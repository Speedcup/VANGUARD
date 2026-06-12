"""Persistent view for the honeypot warning embed.

The single button is permanently disabled and acts purely as a live counter of
caught compromised accounts. It carries a static ``custom_id`` so the view can be
registered as persistent and survive restarts; being disabled, it never receives
interactions.
"""

from __future__ import annotations

import discord

_COUNTER_CUSTOM_ID = "honeypot:counter"


class HoneypotWarningView(discord.ui.View):
    def __init__(self, caught: int = 0) -> None:
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label=f"\U0001f528 Caught: {caught}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                custom_id=_COUNTER_CUSTOM_ID,
            )
        )
