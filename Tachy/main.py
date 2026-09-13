import logging

from config.config import Config
from database import init_link_table
from discord_handler import create_bot

logging.basicConfig(level=logging.INFO)

init_link_table()
bot = create_bot()
bot.run(Config.DISCORD_BOT_TOKEN)
