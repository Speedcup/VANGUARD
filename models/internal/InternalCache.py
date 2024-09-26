from typing import TYPE_CHECKING

import attrs
from interactions import BaseMessage, Absent, MISSING

from interactions.client.utils.cache import TTLCache

if TYPE_CHECKING:
    from interactions.client import Client


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class InternalCache:
    _client: "Client" = attrs.field(
        repr=False,
    )

    # Create an independent automod message cache so messages deleted by the bot aren't logged twice.
    automod_message_cache: TTLCache = attrs.field(
        repr=False, factory=TTLCache
    )  # key: message_id

    def place_automod_message_data(self, message: BaseMessage) -> None:
        if not self.automod_message_cache.get(message.id):
            self.automod_message_cache[message.id] = message

    def find_automod_message_and_remove(
        self, message: BaseMessage
    ) -> Absent[BaseMessage]:
        return self.automod_message_cache.pop(key=message.id, default=MISSING)
