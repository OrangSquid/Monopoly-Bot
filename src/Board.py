import json
from typing import Dict, List, Union, TypeVar, Tuple

from .Spaces import (ColorProperty, CommunitChestSpace, FreeSpace, Jail,
                     Jailing, RailroadProperty, ChanceSpace,
                     ServiceProperty, Space, Tax)

Player = TypeVar('Player')

space_type_to_class = {
    'free_space': FreeSpace,
    'jail': Jail,
    'jailing': Jailing,
    'chance_card': ChanceSpace,
    'community_chest_card': CommunitChestSpace,
    'service_property': ServiceProperty,
    'railroad_property': RailroadProperty
}


class Board:

    def __init__(self, board_json: str):
        self._board_list: List[Space] = list()
        with open(board_json, 'r') as file:
            temp_board_dict = json.load(file)
        self.salary = temp_board_dict['salary']
        luck_cards = temp_board_dict['luck_cards']
        for count, space in enumerate(temp_board_dict['spaces']):
            # Since jail, jailing, free_space, chance_card and
            # community_chest_card all share the same
            # implementation, this was done to reduce the
            # lines of code
            if space['type'] in ['jail', 'jailing', 'free_space']:
                space_class = space_type_to_class[space['type']](
                    name=space['name'],
                    color_int=space['color_int'],
                    emoji=space['emoji'],
                    image_url=space['image_url'],
                    index=count
                )
            # The same goes to service_property and railroad_property
            elif space['type'] in ['service_property', 'railroad_property']:
                space_class = space_type_to_class[space['type']](
                    name=space['name'],
                    color_int=space['color_int'],
                    emoji=space['emoji'],
                    image_url=space['image_url'],
                    index=count,
                    cost=space['cost'],
                    rent_list=space['rent']
                )
            elif space['type'] in ['chance_card', 'community_chest_card']:
                space_class = space_type_to_class[space['type']](
                    name=space['name'],
                    color_int=space['color_int'],
                    emoji=space['emoji'],
                    image_url=space['image_url'],
                    index=count,
                    deck=luck_cards[space['type']]
                )
            elif space['type'] == 'tax':
                space_class = Tax(
                    name=space['name'],
                    color_int=space['color_int'],
                    emoji=space['emoji'],
                    image_url=space['image_url'],
                    index=count,
                    cost=space['cost']
                )
            # ColorProperty
            else:
                space_class = ColorProperty(
                    name=space['name'],
                    color_int=space['color_int'],
                    emoji=space['emoji'],
                    image_url=space['image_url'],
                    index=count,
                    cost=space['cost'],
                    rent_list=space['rent'],
                    color=space['color'],
                    color_group=space['color_group'],
                    house_cost=space['house_cost']
                )
            self._board_list.append(space_class)


    def __getitem__(self, position) -> Space:
        return self._board_list[position]

    def board_embeds(self) -> Dict[str, Union[str, int]]:
        """
        Returns a iterator of dict embeds of the entire board
        """
        # Integers to slice self._board_list
        begin: int = 0
        end: int = 10
        for x in range(4):
            embed_board = {
                'description': '',
                'color': 13427655,
                'author': {
                    'name': 'Monopoly Board',
                    'icon_url': 'https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024'
                }
            }
            for space in self[begin:end]:
                embed_board['description'] += str(space)

            if x == 3:
                embed_board['image'] = dict(url='https://raw.githubusercontent.com/OrangSquid/Monopoly-Bot/master/emojis/monopoly_board.jpg')

            begin += 10
            end += 10
            yield embed_board

    def move_on_board(
        self, player: Player, dice: int = None,
        teleport: int = None, jailing: bool = False
    ) -> Tuple[Space, bool]:
        """
        Places the player in a new space in the board.

        This can be achieved by a dice roll, a teleport type luck card
        or by a type jailing space

        This also changes the player.space atribute in player.
        This method returns the landing space for a possible event and
        wheter or not the player as passed GO
        """
        index = player.space.index
        player.space.here.remove(player)
        give_salary = False
        # Going to jail
        if jailing:
            self[10].lock_prisoner(player)
        # Rolled dice
        elif dice is not None:
            landing_index = index + dice
            if landing_index > 39:
                player.space = self[landing_index - 40]
                give_salary = True
            else:
                player.space = self[landing_index]
            player.space.here.append(player)
        # Teleport (luck_card)
        elif teleport is not None:
            player.space = self[teleport]
            player.space.here.append(player)

        return player.space, give_salary
