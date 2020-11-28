from typing import Any, List, Tuple, TypeVar

import discord

from .Space import Space

Player = TypeVar('Player')


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

    def event(self, player: Player, embed: discord.Embed):
        if self.owner is not None:
            if self.owner == player:
                embed.description += '\nYou landed on your own property!'
                return 'nothing'
            elif self.mortgage:
                embed.description += '\nThis property is mortgaged!\nYou don\'t need to pay rent!'
                return 'nothing'
            else:
                embed.description += f'\n**You must pay {self.rent}$ to {self.owner.user}**'
                return 'pay_debt'
        elif self.cost > player.money:
            embed.description += '\nYou don\'t have enough money!\nYou must auction this property!'
            return 'auction_property'
        else:
            embed.description += '\nYou can buy or auction this property!'
            return 'buy_property'

    def buy_property(self, buyer) -> None:
        self.owner = buyer
        buyer.add_property(self)

    def pay_rent(self, multiplier: int = 1) -> Tuple[Any]:
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
