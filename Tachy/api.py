import json
import sqlite3
from functools import lru_cache
from typing import Any

import requests

from config.config import Config

RECORD_COUNT = 50

DIFFICULTY_NAMES = {
    0: "PST",
    1: "PRS",
    2: "FTR",
    3: "BYD",
    4: "ETR",
}

DIFFICULTY_COLUMNS = {
    0: "rating_pst",
    1: "rating_prs",
    2: "rating_ftr",
    3: "rating_byn",
    4: "rating_etr",
}


@lru_cache(maxsize=1)
def load_songlist() -> dict[str, Any]:
    with open(Config.SONGLIST_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def build_song_index() -> dict[str, dict[str, Any]]:
    return {
        song["id"]: song for song in load_songlist().get("songs", []) if song.get("id")
    }


@lru_cache(maxsize=1)
def build_chart_level_index() -> dict[tuple[str, int], str]:
    """
    Build an index for the level displayed in-game.

    Example:
        rating=9, ratingPlus=True
        -> "9+"

        rating=10, ratingPlus=False
        -> "10"
    """
    index: dict[tuple[str, int], str] = {}

    for song in load_songlist().get("songs", []):
        song_id = song.get("id")

        if not song_id:
            continue

        for diff in song.get("difficulties", []):
            difficulty = diff.get("ratingClass")

            if difficulty is None:
                continue

            rating = diff.get("rating", "N/A")
            text = f"{rating}+" if diff.get("ratingPlus", False) else str(rating)

            index[(song_id, difficulty)] = text

    return index


@lru_cache(maxsize=1)
def build_chart_constant_index() -> dict[tuple[str, int], float]:
    """
    Load actual chart constants from the Arcaea server's chart table.

    The server DB stores chart constants multiplied by 10.

    Example:
        rating_ftr = 74
        -> actual chart constant = 7.4

    A value of -1 means that the corresponding difficulty does not exist
    and is therefore excluded from the index.
    """
    index: dict[tuple[str, int], float] = {}

    conn = sqlite3.connect(Config.DB_PATH)

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                song_id,
                rating_pst,
                rating_prs,
                rating_ftr,
                rating_byn,
                rating_etr
            FROM chart
            """)

        for row in cursor.fetchall():
            song_id = row[0]

            for difficulty, value in enumerate(row[1:]):
                if value is None:
                    continue

                try:
                    raw_value = float(value)
                except (TypeError, ValueError):
                    continue

                if raw_value < 0:
                    continue

                constant = raw_value / 10.0

                index[(song_id, difficulty)] = constant

    finally:
        conn.close()

    return index


def get_chart_level(song_id: str, difficulty: int) -> str:
    return build_chart_level_index().get(
        (song_id, difficulty),
        "N/A",
    )


def get_chart_constant(
    song_id: str,
    difficulty: int,
) -> float | None:
    return build_chart_constant_index().get((song_id, difficulty))


def get_difficulty_name(difficulty: int) -> str:
    return DIFFICULTY_NAMES.get(
        difficulty,
        f"UNKNOWN({difficulty})",
    )


def get_song_chart(
    song_id: str,
    difficulty: int,
) -> dict[str, Any] | None:
    """
    Return metadata for a specific song/chart.
    """
    song = build_song_index().get(song_id)

    if not song:
        return None

    chart_constant = get_chart_constant(
        song_id,
        difficulty,
    )

    display_level = get_chart_level(
        song_id,
        difficulty,
    )

    for diff in song.get("difficulties", []):
        if diff.get("ratingClass") != difficulty:
            continue

        return {
            "song_id": song_id,
            "song_name": song.get(
                "title_localized",
                {},
            ).get(
                "en",
                song.get("id", "Unknown"),
            ),
            "artist": song.get(
                "artist",
                "Unknown",
            ),
            "difficulty": difficulty,
            "difficulty_name": get_difficulty_name(difficulty),
            "chart_constant": chart_constant,
            "display_level": display_level,
            "rating": diff.get("rating"),
            "rating_plus": bool(diff.get("ratingPlus", False)),
            "chart_designer": diff.get(
                "chartDesigner",
                "",
            ),
        }

    return None


def _get_json(path: str) -> dict[str, Any]:
    """
    Request a JSON response from the Arcaea server API.
    """
    api_url = f"{Config.SERVER_URL.rstrip('/')}" f"/api/v1/{path.lstrip('/')}"

    response = requests.get(
        api_url,
        headers={
            "Token": Config.API_TOKEN,
        },
        timeout=Config.API_TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("code", 0) != 0:
        raise RuntimeError(
            "Arcaea API returned code "
            f"{payload.get('code')}: "
            f"{payload.get('msg', '')}"
        )

    return payload


def fetch_user_brief(
    user_id: int,
) -> dict[str, Any]:
    """
    Fetch the user's basic profile information.

    rating_ptt is the user's current PTT from /brief.
    """
    payload = _get_json(f"users/{user_id}/brief")

    data = payload.get("data") or {}

    return {
        "user_id": data.get(
            "user_id",
            user_id,
        ),
        "name": data.get(
            "name",
            "Unknown",
        ),
        "rating_ptt": float(
            data.get(
                "rating_ptt",
                0.0,
            )
        ),
        "is_hide_rating": bool(
            data.get(
                "is_hide_rating",
                False,
            )
        ),
    }


def _normalize_record(
    item: dict[str, Any],
    include_best_clear: bool = False,
) -> dict[str, Any]:
    """
    Normalize one B50/R30 record.

    The Arcaea API calls the calculated play rating "rating".

    Internally we expose both:
        rating
        play_rating

    `rating` is intentionally preserved for compatibility with
    existing consumers such as b50gen.py.
    `play_rating` is the clearer name for recommendation logic.
    """
    song_id = item.get(
        "song_id",
        "Unknown",
    )

    difficulty = int(
        item.get(
            "difficulty",
            0,
        )
    )

    chart = get_song_chart(
        song_id,
        difficulty,
    )

    play_rating = round(
        float(
            item.get(
                "rating",
                0.0,
            )
        ),
        5,
    )

    result = {
        "song_id": song_id,
        "song_name": (
            item.get("song_name")
            or (chart or {}).get(
                "song_name",
                "Unknown",
            )
        ),
        "difficulty": difficulty,
        "difficulty_name": get_difficulty_name(difficulty),
        "display_level": get_chart_level(
            song_id,
            difficulty,
        ),
        "chart_constant": get_chart_constant(
            song_id,
            difficulty,
        ),
        "score": int(
            item.get(
                "score",
                0,
            )
        ),
        "rating": play_rating,
        "play_rating": play_rating,
        "clear_type": item.get("clear_type"),
        "miss_count": int(
            item.get(
                "miss_count",
                0,
            )
        ),
        "near_count": int(
            item.get(
                "near_count",
                0,
            )
        ),
        "perfect_count": int(
            item.get(
                "perfect_count",
                0,
            )
        ),
        "shiny_perfect_count": int(
            item.get(
                "shiny_perfect_count",
                0,
            )
        ),
        "modifier": item.get(
            "modifier",
            0,
        ),
        "health": item.get("health"),
        "time_played": int(
            item.get(
                "time_played",
                0,
            )
        ),
    }

    if include_best_clear:
        result["best_clear_type"] = item.get("best_clear_type")

    return result


def fetch_user_b50(
    user_id: int,
    limit: int = RECORD_COUNT,
) -> dict[str, Any]:
    """
    Fetch the user's Best 50 records.

    The API response's `rating` field is the calculated
    play rating, not the chart constant.
    """
    payload = _get_json(f"users/{user_id}/b{limit}")

    data = payload.get("data") or {}

    raw_items = (data.get("data") or [])[:limit]

    return {
        "user_id": data.get(
            "user_id",
            user_id,
        ),
        "b50_ptt": float(
            data.get(
                "b50_ptt",
                0.0,
            )
        ),
        "data": [
            _normalize_record(
                item,
                include_best_clear=True,
            )
            for item in raw_items
        ],
    }


def fetch_user_r30(
    user_id: int,
) -> dict[str, Any]:
    """
    Fetch the user's Recent 30 records.
    """
    payload = _get_json(f"users/{user_id}/r30")

    data = payload.get("data") or {}

    raw_items = (data.get("data") or [])[:30]

    return {
        "user_id": data.get(
            "user_id",
            user_id,
        ),
        "r10_ptt": float(
            data.get(
                "r10_ptt",
                0.0,
            )
        ),
        "data": [_normalize_record(item) for item in raw_items],
    }


def fetch_user_best(
    user_id: int,
    limit: int = RECORD_COUNT,
) -> list[dict[str, Any]]:
    """
    Existing /b50 command compatibility wrapper.

    Returns only the normalized record list,
    preserving the original interface expected by b50gen.py.
    """
    return fetch_user_b50(
        user_id,
        limit,
    )["data"]
