from dataclasses import dataclass, field
from typing import List, Tuple, TypeVar, Union, Dict, Any, Optional
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


@dataclass
class Tax(Space):
    """
    Class for tax spaces.

    cost has a default value of 0 due to the error raised for having a
    default value before but it should always be set to some value
    """
    cost: int = 0

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        embed_str += f' ({self.cost}$)'
        return embed_str + players_here_mention

    def pay_rent(self) -> Tuple[Optional[int]]:
        return self.cost, None
    
    def event(self, playing: Player, embed: discord.Embed):
        embed.description += f'**\nYou must pay {self.cost}$ to the bank**'
        return 'pay_debt'


@dataclass
class Jail(Space):
    """
    Class for Jail space

    Stores jailed as a list
    """
    jailed: List[Player] = field(default_factory=list)

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


@dataclass
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


@dataclass
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


class MonopolyProperty(Space):
    """
    Class from which every other property space class inherits.

    Adds a function to buy property, pay rent and basic variables like
    owner, cost, and rent
    """

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, cost: int, 
        rent_list: List[int]
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        self.owner = None
        self.mortgage = False
        self.cost = cost
        self._rent_list = rent_list
        self._house_level = 0
        self.rent = rent_list[0]

    def __str__(self) -> Tuple[str]:
        embed_str, players_here_mention = super().__str__()
        embed_str += f' ({self.cost}$)'
        if self.owner is not None:
            embed_str += f'\n**Owner:** {str(self.owner.user)}'
            embed_str += f' | **Rent:** {self.rent}'
        return embed_str, players_here_mention

    def event(self, player: Player, embed: discord.Embed()):
        if self.owner is not None:
            if self.owner == player:
                embed.description += '\nYou landed on your own property!'
                return 'nothing'
            elif self.mortgage:
                embed.description += '\nThis property is mortgaged!\nYou don\'t need to pay rent!'
                return 'nothing'
            else:
                embed.description += f'\n**You must pay {self.rent}$ to {self.owner}**'
                return 'pay_rent'
        elif self.cost > player.money:
            embed.description += '\nYou don\'t have enough money!\nYou must auction this property!'
            return 'auction_property'
        else:
            embed.description += '\nYou can buy or auction this property!'
            return 'buy_property'

    def buy_property(self, buyer) -> None:
        self.owner = buyer
        buyer.add_property(self)

    def pay_rent(self, multiplier: int=1) -> Tuple[Union[int, Player]]:
        """
        Returns List of [money to pay, player who receives]
        """
        return self.rent * multiplier, self.owner

class ServiceProperty(MonopolyProperty):

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        if self.owner is not None:
            embed_str += ' * Number on dice'
        return embed_str + players_here_mention

    def buy_property(self, buyer) -> None:
        super().buy_property(buyer)
        self._house_level = len(buyer.properties['service']) - 1
        self.rent = self._rent_list[self._house_level]


class RailroadProperty(MonopolyProperty):

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        return embed_str + '$' + players_here_mention

    def buy_property(self, buyer) -> None:
        super().buy_property(buyer)
        self._house_level = len(buyer.properties['railroad']) - 1
        self.rent = self._rent_list[self._house_level]


class ColorProperty(MonopolyProperty):

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, cost: int, rent_list: List[int], 
        color: str, color_group: List[int], house_cost: int
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index, cost, rent_list)
        self.color = color
        self.color_group = color_group
        self.house_cost = house_cost
        self.monopoly = False

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        embed_str += '$'
        if self._house_level == 5:
            embed_str += '<:hotel:780131003259027477>'
        else:
            embed_str += '<:properties:780131015581761556>' * self._house_level
        return embed_str + players_here_mention

    def buy_property(self, buyer: Player) -> bool:
        """
        ColorProperty buy_property method returns a bool to denote if
        the buyer has a made a monopoly or not.

        This is to make it easy to anounce in discord.
        """
        super().buy_property(buyer)
        if len(buyer.properties[f'{self.color}']) == len(self.color_group):
            self.monopoly = True
        return self.monopoly
