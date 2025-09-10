import asyncio
import logging

from src.common import env, setup_logger
from src.core import Bot
from src.utils import setup_extensions


async def main() -> None:
    bot = Bot(
        env.bot.token.get_secret_value(), env.bot.owner_ids_list, setup_logger(env.logger.level)
    )
    setup_extensions(bot)
    await bot.bot_launch()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info('Bot stopped!')
