import importlib
import logging
import pkgutil

from interactions import Client


def setup_extensions(bot: Client, base_package: str = 'src.extensions') -> None:
    try:
        package = importlib.import_module(base_package)
    except ImportError as e:
        logging.error(f'Failed to import base package {base_package}: {e}')
        return

    for _, name, ispkg in pkgutil.walk_packages(package.__path__, prefix=f'{base_package}.'):
        if ispkg:
            continue

        try:
            bot.load_extension(name)
            logging.info(f'Successfully loaded extension: {name}')
        except Exception as e:
            logging.error(f'Failed to load extension {name}: {e}')
