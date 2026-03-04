import os
from dotenv import load_dotenv

from bot.discord_handler.handler import build_bot

load_dotenv()
TOKEN = 'haha did you actually think I would commit with my token still attached? Yes, I know its bad practice, but 1. Im running locally and 2. Im not setting up an env for a test run'

bot = build_bot()
bot.run(TOKEN)