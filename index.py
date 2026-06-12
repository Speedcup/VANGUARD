"""VANGUARD bot entry point."""

from __future__ import annotations

from bot.client import VanguardBot
from bot.config import Config
from bot.logging_config import configure_logging


def main() -> None:
    config = Config.load()
    log = configure_logging(config.debug)
    log.info("Starting VANGUARD...")

    bot = VanguardBot(config)
    # log_handler=None: we configure logging ourselves in configure_logging().
    bot.run(config.token, log_handler=None)


if __name__ == "__main__":
    main()
