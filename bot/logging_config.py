"""Structured logging configuration for the bot."""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(debug: bool = False) -> logging.Logger:
    """Configure root logging and return the project logger.

    discord.py ships its own logging; we tune it down to INFO/WARNING so our own
    DEBUG output stays readable.
    """

    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Keep the discord library's chatter at a sane level even in debug mode.
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    log = logging.getLogger("vanguard")
    log.setLevel(level)
    return log
