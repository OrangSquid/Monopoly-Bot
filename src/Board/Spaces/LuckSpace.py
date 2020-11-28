import discord
from .Space import Space
from typing import List, Dict, Any, TypeVar

Player = TypeVar('Player')


class LuckSpace(Space):

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        return embed_str + players_here_mention


class ChanceSpace(LuckSpace):

    deck: List[Dict[Any, Any]]

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, deck
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        ChanceSpace.deck = deck

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += '\nTaking a card from Chance deck.\nIt reads as follows: '
        return 'nothing'


class CommunitChestSpace(LuckSpace):

    deck: List[Dict[Any, Any]]

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, deck
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        CommunitChestSpace.deck = deck

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += '\nTaking a card from Community Chest deck.\nIt reads as follows: '
        return 'nothing'
