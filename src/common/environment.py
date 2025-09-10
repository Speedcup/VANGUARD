from __future__ import annotations

from typing import Dict, List, Set

from pydantic import BaseModel, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Groq(BaseModel):
    api_key: SecretStr
    base_url: str
    model: str
    max_retries: int
    retry_delay: float


class Logger(BaseModel):
    level: int | str


class Database(BaseModel):
    url: PostgresDsn

    @property
    def tortoise_orm(self) -> Dict[str, Dict[str, str] | Dict[str, Dict[str, List[str] | str]]]:
        return {
            'connections': {'default': self.url.encoded_string()},
            'apps': {
                'models': {
                    'models': [
                        'src.database.models.faq_model',
                        'src.database.models.app_store_app_model',
                        'aerich.models',
                    ],
                    'default_connection': 'default',
                },
            },
        }


class Bot(BaseModel):
    token: SecretStr
    owner_ids: str
    member_log_channel: int
    app_store_updates_channel: int
    app_store_role: int
    whitelist_channel_ids: str
    msg_delete_log_channel: int
    rate_cooldown: int
    interval_cooldown: int

    @property
    def owner_ids_list(self) -> List[str]:
        return [id_.strip() for id_ in self.owner_ids.split(',') if id_.strip()]

    @property
    def whitelist_channels(self) -> Set[int]:
        if not self.whitelist_channel_ids.strip():
            return set()
        return {
            int(id_.strip())
            for id_ in self.whitelist_channel_ids.split(',')
            if id_.strip().isdigit()
        }


class Environment(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_ignore_empty=True,
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )

    bot: Bot
    database: Database
    logger: Logger
    groq: Groq


env = Environment()

TORTOISE_ORM = env.database.tortoise_orm
