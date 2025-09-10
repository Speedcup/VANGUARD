from __future__ import annotations

from typing import List

from tortoise.exceptions import DoesNotExist, IntegrityError

from ..exceptions import IntegrityViolationError, NotFoundError
from ..models import FaqModel
from ..repositories.faq_repository import FaqRepository


class FaqController:
    def __init__(self):
        self.repo = FaqRepository()

    async def create(self, id: str, title: str, description: str) -> FaqModel:
        try:
            return await self.repo.create(id, title, description)
        except IntegrityError as e:
            raise IntegrityViolationError(f'Error creating FAQ: {e}') from e

    async def update(self, id: str, title: str, description: str) -> FaqModel:
        try:
            return await self.repo.update(id, title, description)
        except DoesNotExist as e:
            raise NotFoundError(f'FAQ with ID {id} was not found') from e
        except IntegrityError as e:
            raise IntegrityViolationError(f'Error updating FAQ: {e}') from e

    async def delete(self, id: str) -> None:
        deleted_count = await self.repo.faq.filter(id=id).delete()
        if deleted_count == 0:
            raise NotFoundError(f'FAQ with ID {id} was not found and was not deleted')

    async def get_by_id(self, id: str) -> FaqModel | None:
        try:
            return await self.repo.get_by_id(id)
        except DoesNotExist:
            return None

    async def get_all(self) -> List[FaqModel]:
        return await self.repo.get_all()
