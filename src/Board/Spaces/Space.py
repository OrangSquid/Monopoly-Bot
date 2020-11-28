from dataclasses import dataclass, field
from typing import List, Tuple, TypeVar

import discord

Player = TypeVar('Player')


@dataclass
class Space(object):
    """
    Class from which every other space type class inherits.

    Only adds basic functionality to store: name, color_int, image_url
    and emoji (for embeds), here (list of all players in the space) and index
    """

    name: str
    color_int: int
    emoji: str
    image_url: str
    index: int
    here: List[Player] = field(default_factory=list)

    def __str__(self) -> Tuple[str]:
        """
        __str__ function is for easy access to a str to add to embeds.
        """
        embed_str = f'{self.emoji} **{self.name}**'
        players_here_mention = str()
        for player in self.here:
            players_here_mention += f'\n{player.user.mention} ({player.money}$)'
        players_here_mention += '\n\n'

        return embed_str, players_here_mention

    def event(self, playing: Player, embed: discord.Embed):
        return 'nothing'


class FreeSpace(Space):
    """
    Class for free spaces

    Nothing changes when a player lands here
    """

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        return embed_str + players_here_mention
