"""Branded embed helpers.

Centralises the VALPAW brand identity (accent colour + logo thumbnail) so every
embed the bot sends looks consistent.
"""

from __future__ import annotations

import discord

PRIMARY = discord.Color.from_str("#FF4654")
SECONDARY = discord.Color.from_str("#0C1824")
SUCCESS = discord.Color.from_str("#3BA55D")
WARNING = discord.Color.from_str("#FAA61A")
DANGER = discord.Color.from_str("#ED4245")

LOGO_URL = (
    "https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/4c/6f/df/"
    "4c6fdff2-397b-2512-9c96-345ebe20cbd3/AppIcon-0-1x_U007ephone-0-0-85-220-0.png/512x512bb.jpg"
)


def branded_embed(
    *,
    title: str | None = None,
    description: str | None = None,
    color: discord.Color = PRIMARY,
    thumbnail: bool = True,
) -> discord.Embed:
    """Create an embed pre-styled with the brand colour and logo thumbnail."""

    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=LOGO_URL)
    return embed
