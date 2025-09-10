import asyncio
import logging
from typing import Dict, List

from tortoise import Tortoise

from src.common import env, setup_logger

from .controllers import FaqController
from .mocks.faq_mocks import FAQ_MOCKS


async def seed_faqs(mocks: List[Dict[str, str]], controller: FaqController) -> None:
    for mock in mocks:
        exists_faq = await controller.get_by_id(mock['id'])

        if exists_faq:
            continue

        create_faq = await controller.create(**mock)
        logging.info(f'Created Faq: {create_faq.id}')


async def seed() -> None:
    setup_logger(env.logger.level)
    await Tortoise.init(env.database.tortoise_orm)

    logging.info('Start seeding')

    await seed_faqs(FAQ_MOCKS, FaqController())

    logging.info('Finished seeding')


asyncio.run(seed())
