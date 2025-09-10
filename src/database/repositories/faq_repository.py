from __future__ import annotations

from typing import List

from ..models import FaqModel


class FaqRepository:
    def __init__(self):
        self.faq = FaqModel()

    async def create(self, id: str, title: str, description: str) -> FaqModel:
        return await self.faq.create(
            id=id,
            title=title,
            description=description,
        )

    async def update(self, id: str, title: str, description: str) -> FaqModel:
        await self.faq.filter(id=id).update(title=title, description=description)
        return await self.faq.get(id=id)

    async def delete(self, id: str) -> None:
        await self.faq.filter(id=id).delete()

    async def get_by_id(self, id: str) -> FaqModel | None:
        return await self.faq.get(id=id)

    async def get_all(self) -> List[FaqModel]:
        return await self.faq.all()
