import os
import sqlite3

from config.config import Config

LINK_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tachy.db",
)


def get_user_id(name):
    conn = sqlite3.connect(Config.DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM user WHERE name = ?",
            (name,),
        )
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def init_link_table():
    conn = sqlite3.connect(LINK_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_link (
                discord_user_id TEXT PRIMARY KEY,
                arcaea_username TEXT NOT NULL,
                arcaea_user_id INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def link_user(discord_user_id, arcaea_username, arcaea_user_id):
    conn = sqlite3.connect(LINK_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO discord_link
            (discord_user_id, arcaea_username, arcaea_user_id)
            VALUES (?, ?, ?)
            """,
            (
                str(discord_user_id),
                arcaea_username,
                arcaea_user_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_linked_user_id(discord_user_id):
    conn = sqlite3.connect(LINK_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT arcaea_user_id
            FROM discord_link
            WHERE discord_user_id = ?
            """,
            (str(discord_user_id),),
        )
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def get_linked_username(discord_user_id):
    conn = sqlite3.connect(LINK_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT arcaea_username
            FROM discord_link
            WHERE discord_user_id = ?
            """,
            (str(discord_user_id),),
        )
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()
