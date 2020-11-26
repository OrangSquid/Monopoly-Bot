import discord
from typing import Dict, List
from .Spaces import MonopolyProperty, ServiceProperty, RailroadProperty, ColorProperty


class Player:

    def __init__(self, user: discord.User):
        self.in_prison: bool = False
        self.space: int = 0
        # {'color\service\railroad': LIST OF OBJECT REFERENCES}
        self.properties: Dict[str, List[MonopolyProperty]] = dict()
        self.prison_free_pass: int = 0
        self.money: int = 1500
        self._monopolies: List['str'] = []
        self.user: discord.User = user
        self.avatar_url: str = str(user.avatar_url)

    def add_property(self, monopoly_property: MonopolyProperty):
        if type(monopoly_property) == ServiceProperty:
            self.properties['service'] += 1
        elif type(monopoly_property) == RailroadProperty:
            self.properties['railroad'] += 1
        self.properties['properties'].append(monopoly_property)

    def properties_embed(self) -> Dict:
        properties_dict = {
            'embeds': [],
            'monopolies': self._monopolies
        }
        # TODO: FIX THIS
        '''for property_str in self.properties['properties'].keys():
            if type(monopoly_property) == ColorProperty:
                properties_dict['embeds']
            elif type(monopoly_property) == ServiceProperty:
                pass
            elif type(monopoly_property) == RailroadProperty:
                pass'''

        """for property in zip(embed_properties_dict.keys(), embed_properties_dict.values()):
            embed_property = discord.Embed(
                color=color_int_dict[property[0]], timestamp=datetime.datetime.now(), description=property[1])
            embed_property.set_author(name='{} properties'.format(
                self.order[self.pointer][0].user), icon_url=str(playing.avatar_url))
            await self.channel.send(embed=embed_property)"""
