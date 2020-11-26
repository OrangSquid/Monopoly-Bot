from dataclasses import dataclass
from typing import List, TypeVar

Player = TypeVar('Player')


@dataclass
class Space(object):
    """
    Class from which every other space type class inherits.

    Only adds basic functionality to store: name, color_int
    (for embeds), here (list of all players in the space) and emoji
    """

    name: str
    color_int: int
    emoji: str
    here: List[Player] = []


@dataclass
class Tax(Space):
    """
    Class for tax spaces.

    cost has a default value of 0 due to the error raised for here having a
    default value but it is always set to some value
    """
    cost: int = 0


@dataclass
class Jail(Space):
    """
    Class for Jail space

    Store jailed as a list
    """
    jailed: List[Player] = []


@dataclass
class Jailing(Space):
    """
    Class for Go to prison space

    Doesn't add any new funcitonality
    """
    pass


class MonopolyProperty(Space):
    """
    Class from which every other property space class inherits.

    Adds a function to buy property, pay rent and basic variables like owner
    cost and rent
    """

    def __init__(self, name, color_int, emoji, cost, rent_list) -> None:
        super().__init__(name, color_int, emoji)
        self.owner = None
        self.cost = cost
        self._rent_list = rent_list
        self._house_level = 0
        self.rent = rent_list[0]

    def buy_property(self, buyer) -> None:
        self.owner = buyer
        buyer.add_property(self)
    
    def pay_rent(self, payer) -> bool:
        if payer.money < self.rent:
            return False
        else:
            payer.money -= self.rent
            self.owner.money += self.rent
            return True


class ServiceProperty(MonopolyProperty):
    
    def buy_property(self, buyer) -> None:
        super().buy_property(buyer)
        self._house_level = buyer.properties['service'] - 1
        self.rent = self._rent_list[self._house_level]

    def pay_rent(self, payer, dice) -> bool:
        actual_rent = self.rent * dice
        if payer.money < actual_rent:
            return False
        else:
            payer.money -= actual_rent
            self.owner.money += actual_rent
            return True


class RailroadProperty(MonopolyProperty):
    
    def buy_property(self, buyer) -> None:
        super().buy_property(buyer)
        self._house_level = buyer.properties['railroad'] - 1
        self.rent = self._rent_list[self._house_level]


class ColorProperty(MonopolyProperty):

    def __init__(
        self, name, color_int, emoji,
        cost, rent_list, color, house_cost
    ) -> None:
        super().__init__(name, color_int, emoji, cost, rent_list)
        self.color = color
        self.house_cost = house_cost
        self.monopoly = False
