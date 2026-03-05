import os
import sys
import logging
from dotenv import load_dotenv

from bot.discord_handler.handler import build_bot


def main() -> None:
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = build_bot()
    bot.run(token)


if __name__ == "__main__":
    main()