from __future__ import annotations

from datetime import datetime

from ..models import AppStoreAppModel


class AppStoreAppRepository:
    def __init__(self):
        self.appstore = AppStoreAppModel()

    async def create(
        self, version: str, release_notes: str, release_date: datetime
    ) -> AppStoreAppModel:
        return await self.appstore.create(
            version=version, release_notes=release_notes, release_date=release_date
        )

    async def get_by_version(self, version: str) -> AppStoreAppModel | None:
        return await self.appstore.get(version=version)
