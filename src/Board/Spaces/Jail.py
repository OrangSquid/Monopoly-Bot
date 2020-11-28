from typing import List, TypeVar

import discord

from .Space import Space

Player = TypeVar('Player')


class Jail(Space):
    """
    Class for Jail space

    Stores jailed as a list
    """

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int
    ) -> None:
        self.jailed: List[Player] = list()

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        prisoners = str()
        for prisoner in self.jailed:
            prisoners += f'{prisoner.user.mention}\n'

        return embed_str + players_here_mention + "__Jailed:\n\n__" + prisoners

    def release_prisoner(self, prisoner: Player, means: str):
        if means == 'fine':
            prisoner.money -= 50
        elif means == 'prison_free_pass':
            prisoner.prison_free_pass -= 1
        self.jailed.remove(prisoner)
        self.here.append(prisoner)
        prisoner.in_prison = 0

    def lock_prisoner(self, prisoner: Player):
        prisoner.space = self
        prisoner.in_prison = 3
        self.jailed.append(prisoner)


class Jailing(Space):
    """
    Class for Go to prison space

    Doesn't add any new funcitonality
    """

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        return embed_str + players_here_mention

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += '\nYou\'re going to Jail'
        return 'jailing'
