from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AppStoreRelease(BaseModel):
    version: str
    release_notes: str = Field(alias='releaseNotes')
    release_date: datetime = Field(alias='currentVersionReleaseDate')


class AppStoreResponse(BaseModel):
    result_count: int = Field(alias='resultCount')
    results: List[AppStoreRelease]
