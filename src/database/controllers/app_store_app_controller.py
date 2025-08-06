from __future__ import annotations

from datetime import datetime

from tortoise.exceptions import DoesNotExist, IntegrityError

from ..exceptions import IntegrityViolationError
from ..models import AppStoreAppModel
from ..repositories import AppStoreAppRepository


class AppStoreAppController:
    def __init__(self):
        self.appstore = AppStoreAppRepository()

    async def create(
        self, version: str, release_notes: str, release_date: datetime
    ) -> AppStoreAppModel:
        try:
            return await self.appstore.create(
                version=version, release_notes=release_notes, release_date=release_date
            )
        except IntegrityError as e:
            raise IntegrityViolationError(f'Error creating: {e}') from e

    async def get_by_version(self, version: str) -> AppStoreAppModel | None:
        try:
            return await self.appstore.get_by_version(version=version)
        except DoesNotExist:
            return None
