from __future__ import annotations

import logging

from bot.logging_config import configure_logging


def test_configure_logging_sets_expected_levels() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    original_discord_level = logging.getLogger("discord").level
    original_discord_http_level = logging.getLogger("discord.http").level
    original_st_level = logging.getLogger("sentence_transformers").level
    original_vanguard_level = logging.getLogger("vanguard").level

    try:
        logger = configure_logging(debug=True)

        assert logger.name == "vanguard"
        assert root.level == logging.DEBUG
        assert logging.getLogger("discord").level == logging.WARNING
        assert logging.getLogger("discord.http").level == logging.WARNING
        assert logging.getLogger("sentence_transformers").level == logging.WARNING
        assert logger.level == logging.DEBUG
    finally:
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
        logging.getLogger("discord").setLevel(original_discord_level)
        logging.getLogger("discord.http").setLevel(original_discord_http_level)
        logging.getLogger("sentence_transformers").setLevel(original_st_level)
        logging.getLogger("vanguard").setLevel(original_vanguard_level)
