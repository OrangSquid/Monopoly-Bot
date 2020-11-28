from typing import Any, Tuple, TypeVar

import discord

from .Space import Space

Player = TypeVar('Player')


class Tax(Space):
    """
    Class for tax spaces.

    cost has a default value of 0 due to the error raised for having a
    default value before but it should always be set to some value
    """

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, cost: int
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        self.cost = 0

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        embed_str += f' ({self.cost}$)'
        return embed_str + players_here_mention

    def pay_rent(self) -> Tuple[Any]:
        return self.cost, None

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += f'**\nYou must pay {self.cost}$ to the bank**'
        return 'pay_debt'
