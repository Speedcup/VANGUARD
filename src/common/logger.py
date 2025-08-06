from __future__ import annotations

import logging
import os
import sys


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }

    STYLES = {
        'DIM': '\033[2m',
        'RESET': '\033[0m',
    }

    def format(self, record: logging.LogRecord):
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M')

        level_name = record.levelname
        level_color = self.COLORS.get(level_name, '')
        level_reset = self.STYLES['RESET']

        logger_name = record.name
        name_color = '\033[37m'
        name_reset = self.STYLES['RESET']

        pid = os.getpid()
        pid_color = '\033[90m'
        pid_reset = self.STYLES['RESET']

        message = record.getMessage()

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                message += '\n' + record.exc_text

        return (
            f'[VANGUARD] {pid_color}[{pid}]{pid_reset} '
            f'{self.STYLES["DIM"]}{timestamp}{self.STYLES["RESET"]} '
            f'{level_color}{level_name:<8}{level_reset} '
            f'[{name_color}{logger_name}{name_reset}] - '
            f'{message}'
        )


def setup_logger(level: int | str = logging.INFO):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)

    return root_logger
