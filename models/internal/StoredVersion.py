import json

import attrs

from typing import TYPE_CHECKING, Any, Dict, List, Type

from interactions.client.const import T
from interactions.client.mixins.serialization import DictSerializationMixin

__all__ = ("StoredVersion",)


@attrs.define(eq=False, order=False, hash=False, kw_only=True)
class StoredVersion(DictSerializationMixin):
    release_version: str = attrs.field(repr=True, default="-1")
    testflight_version: str = attrs.field(repr=True, default="-1")

    @classmethod
    def from_cache(cls: Type[T]) -> T:
        cached_data = {}

        try:
            with open("version.json", "r") as file:
                cached_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        data = cls._process_dict(cached_data)
        return cls(**cls._filter_kwargs(data, cls._get_init_keys()))

    def to_cache(self):
        with open("version.json", "w") as file:
            json.dump(self.to_dict(), file)
