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

__all__ = ("TestFlightRelease",)


@attrs.define(eq=False, order=False, hash=False, kw_only=True)
class TestFlightRelease(DictSerializationMixin):
    version: str = attrs.field(repr=True, default="-1")
    uploadedDate: Optional[Timestamp] = attrs.field(
        default=None,
        converter=c_optional(timestamp_converter),
        validator=v_optional(instance_of((datetime, float, int))),
        repr=True,
    )
    processingState: str = attrs.field(repr=True, default=None)
    buildAudienceType: str = attrs.field(repr=True, default=None)
