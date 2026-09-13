import os


class Config:
    DISCORD_BOT_TOKEN = os.getenv(
        "TACHY_DISCORD_BOT_TOKEN",
        "",
    )
    SERVER_URL = os.getenv("TACHY_SERVER_URL", "")
    API_TOKEN = os.getenv("TACHY_API_TOKEN", "")
    DB_PATH = os.getenv("TACHY_DB_PATH", "")
    SONGLIST_PATH = os.getenv("TACHY_SONGLIST_PATH", "")
    JACKET_PATH = os.getenv("TACHY_JACKET_PATH", "")
    BACKGROUND_PATH = os.getenv("TACHY_BACKGROUND_PATH", "../Tachy/files/bg.png")
    FONT_PATH = os.getenv("TACHY_FONT_PATH", "../Tachy/files/WantedSans-SemiBold.otf")

    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "90"))

    API_TIMEOUT = int(os.getenv("TACHY_API_TIMEOUT", "10"))

    RECOMMENDATION_CANDIDATES_PER_BUCKET = int(
        os.getenv("TACHY_RECOMMENDATION_CANDIDATES_PER_BUCKET", "12")
    )

    RATING_CLASS_0_COLOR = 10, 130, 190
    RATING_CLASS_1_COLOR = 100, 140, 60
    RATING_CLASS_2_COLOR = 80, 25, 75
    RATING_CLASS_3_COLOR = 130, 35, 40
    RATING_CLASS_4_COLOR = 161, 132, 181
