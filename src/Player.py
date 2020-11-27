from typing import Dict, List

import discord

from .Spaces import (MonopolyProperty, RailroadProperty,
                     ServiceProperty, Space)


class Player:

    def __init__(self, user: discord.User):
        self.in_prison: int = 0
        self.space: Space = None
        # {'color\service\railroad': LIST OF OBJECT REFERENCES}
        self.properties: Dict[str, List[MonopolyProperty]] = dict()
        self.prison_free_pass: int = 0
        self.money: int = 1500
        self.monopolies: List['str'] = list()
        self.user: discord.User = user
        self.avatar_url: str = str(user.avatar_url)

    def add_property(self, monopoly_property: MonopolyProperty):
        self.money -= monopoly_property.cost
        if type(monopoly_property) == ServiceProperty:
            property_type: str = 'service'
        elif type(monopoly_property) == RailroadProperty:
            property_type: str = 'railroad'
        else:
            property_type: str = monopoly_property.color
            if property_type in self.properties.keys():
                ammount_color_properties = len(monopoly_property.color_group)
                player_color_properties = len(self.properties[property_type]) - 1
                if ammount_color_properties == player_color_properties:
                    self.monopolies.append(property_type)

        if property_type in self.properties.keys():
            self.properties[property_type].append(monopoly_property)
        else:
            self.properties[property_type] = [monopoly_property]

    def properties_embed(self) -> Dict:
        for properties_list in self.properties.values():
            embed = {
                'description': '',
                'color': properties_list[0].color_int,
                'author': {
                    'name': f'{str(self.user)} properties',
                    'icon_url': f'{self.avatar_url}'
                }
            }
            for monopoly_property in properties_list:
                embed['description'] += str(monopoly_property)
            
            yield embed