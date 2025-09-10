from pydantic import BaseModel

from .enums import LanguageLevel


class LanguageCheckResult(BaseModel):
    language: LanguageLevel
    reason: str
