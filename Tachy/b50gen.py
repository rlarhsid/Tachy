import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from config.config import Config
from api import build_chart_level_index

LAYOUT_CONFIG = {
    "COLUMNS": 10,
    "IMAGE_WIDTH": 3200,
    "PADDING_RATIO": 0.025,
    "SPACING_RATIO": 0.008,
    "TEXT_AREA_RATIO": 0.38,
}


def compute_layout(num_cards: int, config: dict = LAYOUT_CONFIG) -> dict:
    columns = max(1, config["COLUMNS"])
    image_width = config["IMAGE_WIDTH"]
    padding = int(image_width * config["PADDING_RATIO"])
    spacing = int(image_width * config["SPACING_RATIO"])

    album_size = int(
        (image_width - (padding * 2) - (spacing * (columns - 1))) / columns
    )
    text_area_h = int(album_size * config["TEXT_AREA_RATIO"])

    box_width = album_size - 1
    box_height = album_size + text_area_h
    rows = max(1, (num_cards + columns - 1) // columns)

    image_height = (padding * 2) + (rows * box_height) + (spacing * (rows - 1))

    return {
        "columns": columns,
        "padding": padding,
        "spacing": spacing,
        "album_size": album_size,
        "text_area_h": text_area_h,
        "box_width": box_width,
        "box_height": box_height,
        "rows": rows,
        "image_width": image_width,
        "image_height": image_height,
        "font_large": max(14, int(album_size * 0.08)),
        "font_small": max(12, int(album_size * 0.06)),
        "font_overlay": max(16, int(album_size * 0.09)),
    }


@lru_cache(maxsize=1)
def build_jacket_index():
    index = {}
    if not Config.JACKET_PATH or not os.path.isdir(Config.JACKET_PATH):
        return index

    for folder in os.listdir(Config.JACKET_PATH):
        normalized = folder[3:] if folder.lower().startswith("dl_") else folder
        for fname in ("1080_base.jpg", "base.jpg"):
            full_path = os.path.join(Config.JACKET_PATH, folder, fname)
            if os.path.exists(full_path):
                index.setdefault(normalized.lower(), full_path)
                break
    return index


def get_album_cover(song_id):
    return build_jacket_index().get(song_id.lower())


@lru_cache(maxsize=None)
def get_font(size):
    try:
        return ImageFont.truetype(Config.FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


@lru_cache(maxsize=None)
def get_difficulty_color(difficulty_class):
    difficulty_colors = {
        0: Config.RATING_CLASS_0_COLOR,
        1: Config.RATING_CLASS_1_COLOR,
        2: Config.RATING_CLASS_2_COLOR,
        3: Config.RATING_CLASS_3_COLOR,
        4: Config.RATING_CLASS_4_COLOR,
    }
    return difficulty_colors.get(difficulty_class, (255, 255, 255))


def create_image(data, filename_base):
    layout = compute_layout(len(data))
    padding = layout["padding"]
    spacing = layout["spacing"]
    album_size = layout["album_size"]
    text_area_h = layout["text_area_h"]
    box_width = layout["box_width"]
    box_height = layout["box_height"]
    columns = layout["columns"]

    font_large = get_font(layout["font_large"])
    font_small = get_font(layout["font_small"])
    font_overlay = get_font(layout["font_overlay"])
    font_color = "black"

    try:
        background = (
            Image.open(Config.BACKGROUND_PATH)
            .convert("RGB")
            .resize((layout["image_width"], layout["image_height"]), Image.LANCZOS)
        )
    except Exception:
        background = Image.new(
            "RGB", (layout["image_width"], layout["image_height"]), (240, 240, 240)
        )

    image = background.copy()
    draw = ImageDraw.Draw(image)

    for idx, entry in enumerate(data):
        col = idx % columns
        row = idx // columns
        x = padding + col * (box_width + spacing)
        y = padding + row * (box_height + spacing)

        draw.rectangle([x, y, x + box_width, y + box_height], fill=(255, 255, 255))

        cover_path = get_album_cover(entry["song_id"])
        cover_drawn = False
        if cover_path:
            try:
                cover = (
                    Image.open(cover_path)
                    .convert("RGB")
                    .resize((album_size, album_size), Image.LANCZOS)
                )
                image.paste(cover, (x, y))
                cover_drawn = True
            except Exception:
                pass
        if not cover_drawn:
            draw.rectangle([x, y, x + album_size, y + album_size], fill=(200, 200, 200))

        level_text = str(entry["chart_constant"])
        l_bbox = font_overlay.getbbox(level_text)
        tw, th = l_bbox[2] - l_bbox[0], l_bbox[3] - l_bbox[1]
        l_pad = max(6, int(album_size * 0.035))
        l_box_w, l_box_h = tw + l_pad * 2, th + l_pad * 2
        l_x, l_y = x + album_size - l_box_w, y

        draw.rectangle(
            [l_x, l_y, l_x + l_box_w, l_y + l_box_h],
            fill=get_difficulty_color(entry.get("difficulty", 0)),
        )
        draw.text(
            (l_x + l_pad, l_y + l_pad - l_bbox[1]),
            level_text,
            fill="white",
            font=font_overlay,
        )

        song_name = entry["song_name"]
        if len(song_name) > 12:
            song_name = song_name[:11] + "..."

        tx = x + int(album_size * 0.045)
        ty = y + album_size + int(text_area_h * 0.12)
        line_gap = int(text_area_h * 0.30)

        draw.text((tx, ty), f"#{idx + 1} {song_name}", fill=font_color, font=font_large)
        draw.text(
            (tx, ty + line_gap),
            f"Score: {entry['score']:,}",
            fill=font_color,
            font=font_small,
        )
        draw.text(
            (tx, ty + line_gap * 2),
            f"Rating: {entry['play_rating']:.2f}",
            fill=font_color,
            font=font_small,
        )

    image_path = os.path.join(
        os.path.expanduser("~/ArcSrv/tmp"), f"{filename_base}.png"
    )
    image.save(image_path)
    return image_path
