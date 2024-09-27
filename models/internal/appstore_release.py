from datetime import datetime
from typing import Optional

import attrs
from attrs.validators import instance_of
from attrs.validators import optional as v_optional

from interactions import Timestamp
from interactions.client.mixins.serialization import DictSerializationMixin
from interactions.client.utils.attr_converters import (
    optional as c_optional,
    timestamp_converter,
)

__all__ = ("AppStoreRelease",)


@attrs.define(eq=False, order=False, hash=False, kw_only=True)
class AppStoreRelease(DictSerializationMixin):
    version: str = attrs.field(repr=True, default="-1")
    release_notes: str = attrs.field(repr=True, default="")
    release_date: Optional[Timestamp] = attrs.field(
        default=None,
        converter=c_optional(timestamp_converter),
        validator=v_optional(instance_of((datetime, float, int))),
        repr=True,
    )
