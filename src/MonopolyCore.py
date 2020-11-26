import asyncio
import copy
import datetime
import json
import random
from typing import Dict, List

import discord
from discord.ext import commands

from .Board import Board
# from .LuckCard import LuckCard
from .Player import Player
from .Spaces import (Jailing, Space, Tax, LuckSpace, MonopolyProperty)

DICE_EMOJI = {
    'Dice1': '<:Dice1:748278516289896468>',
    'Dice2': '<:Dice2:748278516319256696>',
    'Dice3': '<:Dice3:748278516226719855>',
    'Dice4': '<:Dice4:748278516352549025>',
    'Dice5': '<:Dice5:748278516272857089>',
    'Dice6': '<:Dice6:748278516516388905>'
}

with open('../json/embeds.json', 'r') as file:
    global EMBEDS_GLOBAL
    EMBEDS_GLOBAL = json.load(file)


class Monopoly:
    """
    Main Class that handles the game loop

    Monopoly class sends messages and embeds and
    does most of the game logic
    """

    def __init__(self, bot, channel, players, board):
        self.in_course = False
        self.order: List[Player] = players
        self.bot: commands.AutoShardedBot = bot
        self.channel: discord.Channel = channel
        self.board: Board = board
        self.pointer: int = 0
        self.choice: str = ''
        self.houses: int = 32
        self.hotels: int = 12
        self.emoji_reactions: Dict[str, str] = {
            '🎲': 'dice',
            '<:monopoly_board:780128903012417536>': 'board',
            '<:properties:780131015581761556>': 'properties',
            '<:thonkang:779326728858370078>': 'trade',
            '💸': 'bankruptcy',
            '🤝': 'buy_property',
            '👨‍⚖️': 'auction_property',
            '🚫': 'nothing',
            '🤑': 'pay_debt'
        }
        self.str_reactions: Dict[str, str] = {}
        for key, value in self.emoji_reactions.items():
            self.str_reactions[value] = key
        # While waiting for a reaction to be added, these are the valid ones 
        # besides the standard:
        # 'board', 'properties', 'trade', 'bankruptcy'
        self.valid_reactions: List[str] = []

    def check_reaction(self, reaction: discord.Emoji, user: discord.User) -> bool:
        self.choice = self.emoji_reactions[str(reaction.emoji)]
        try:
            return user == self.order[self.pointer].user and \
                self.emoji_reactions[str(reaction.emoji)
                                     ] in self.valid_reactions
        except KeyError:
            return False

    async def roll_dice(self, announce: bool) -> List[int]:
        dice1 = random.randrange(1, 7)
        dice2 = random.randrange(1, 7)
        if announce:
            await self.channel.send('{} {}'.format(DICE_EMOJI[f'Dice{dice1}'],
                                                   DICE_EMOJI[f'Dice{dice2}']))
        return [dice1, dice2]

    def increment_pointer(self) -> None:
        if self.pointer >= len(self.players) - 1:
            self.pointer = 0
        else:
            self.pointer += 1

    # TODO
    async def add_reactions_embed(self, embed):
        pass

    async def add_reactions_message(self, message, reactions):
        for reaction in reactions:
            await message.add_reaction(self.str_reactions[reaction])

    def str_embed_properties(self, property):
        # Color_Property
        if self.board['spaces'][property]['type'] == 'color_property':
            rent = self.board['spaces'][property]['rent'][self.board['spaces']
                                                          [property]['house_level']]
            if self.board['spaces'][property]['monopoly'] and self.board['spaces'][property]['house_level'] == 0:
                rent *= 2
            str_to_return = '\n{emoji} **{name}** ({cost}$)\nRent: {rent}$'.format(
                emoji=self.emojis[self.board['spaces'][property]['color']], name=self.board['spaces'][property]['name'], cost=self.board['spaces'][property]['cost'], rent=rent)
            if self.board['spaces'][property]['house_level'] != 5:
                for house in range(self.board['spaces'][property]['house_level']):
                    str_to_return += str(
                        self.emojis['properties'])
            else:
                str_to_return += str(
                    self.emojis['hotel'])
            return str_to_return
        # Railroad_Property
        elif self.board['spaces'][property]['type'] == 'railroad_property':
            return '\n{emoji} **{name}** ({cost}$)\nRent: {rent}$'.format(
                emoji=self.emojis['railroad_property'], name=self.board['spaces'][property]['name'], cost=self.board['spaces'][property]['cost'], rent=self.board['spaces'][property]['rent'][self.board['spaces'][property]['house_level']])
        # Service_Property
        elif self.board['spaces'][property]['type'] == 'service_property':
            if self.board['spaces'][property]['name'] == 'Eletric Company':
                return '\n{emoji} **{name}** ({cost}$)\nRent: {rent} * Number on Dice'.format(
                    emoji=self.emojis['electric_company'], name=self.board['spaces'][property]['name'], cost=self.board['spaces'][property]['cost'], rent=6 * self.board['spaces'][property]['house_level'] - 2)
            else:
                return '\n{emoji} **{name}** ({cost}$)\nRent: {rent} * Number on Dice'.format(
                    emoji=self.emojis['water_works'], name=self.board['spaces'][property]['name'], cost=self.board['spaces'][property]['cost'], rent=6 * self.board['spaces'][property]['house_level'] - 2)

    async def player_turn(self, playing, doubles) -> Dict:
        """
        This is called whenever the player rolls the dice

        Returns a Dict of all the information relevant for
        later use
        """

        # debt = [amount of money, int refering to self.order player]
        debt: List[int] = [0, None]
        buy_property: bool = False
        auction_property: bool = False

        # Embed making
        embed_landing = discord.Embed.from_dict(EMBEDS_GLOBAL['landing'])
        embed_landing.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_landing.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))

        # Roll dice and check for doubles
        dice = await self.roll_dice(False)
        if dice[0] == dice[1]:
            if doubles == 2:
                embed_landing.description = 'You rolled a double 3 times!\n \
                                             You are going to Brazil'
            else:
                doubles += 1
                embed_landing.description += '\nYou rolled a double!, you can play again!'
        # Call move_on_board method and store space
        space = self.board.move_on_board(playing, dice=sum(dice))

        # Embed Editing
        embed_landing.description = embed_landing.description.format(
            dice1=DICE_EMOJI[f'Dice{dice[0]}'],
            dice2=DICE_EMOJI[f'Dice{dice[1]}'],
            sum_dice=sum(dice),
            space=space.name
        )
        embed_landing.color = space.color_int
        embed_landing.timestamp = datetime.datetime.now()
        embed_landing.set_thumbnail(
            url=space.image_url)

        # Lands on property
        if issubclass(space, MonopolyProperty):
            # Somebody is the owner
            if space.owner is not None:
                if space.owner == playing:
                    embed_landing.description += '\nYou landed on your own property!'
                elif space.mortgage:
                    embed_landing.description += '\nThis property is mortgaged!\nYou don\'t need to pay rent!'
                else:
                    debt = space.pay_rent()
                    embed_landing.description += f'\n**You must pay {debt[0]}$ to {str(debt[1].user)}**'
            # Has enough money to buy property
            elif space.cost < playing.money:
                embed_landing.description += '\nYou can buy or auction this property!'
                buy_property = True
                auction_property = True
            # Doesn't have enough money to buy property
            else:
                embed_landing.description += '\nYou don\'t have enough money!\nYou must auction this property!'
                auction_property = True

        elif issubclass(space, LuckSpace):
            pass

        elif issubclass(space, Tax):
            debt = space.pay_rent()
            embed_landing.description += '\nYou must pay {} to the bank'.format(
                debt[0])

        elif issubclass(space, Jailing):
            self.board.move_on_board(playing, jailing=True)
            embed_landing += '\nYou\'re going to Jail'

        return {'doubles': doubles, 'debt': debt, 'buy_property': buy_property, 'auction_property': auction_property, 'embed': embed_landing, 'dice': dice}

    # THERE'S STILL STUFF TO DO IN HERE
    async def routine_checks(self, playing) -> None:
        # Show Board
        if self.choice == 'board':
            for embed in self.board.board_embeds():
                embed = discord.Embed.from_dict(embed)
                await self.channel.send(embed=embed)

        # TODO
        elif self.choice == 'properties':
            embed_properties_dict = {}
            monopolies = []
            color_int_dict = {}
            for property in self.order[self.pointer][0].properties['properties_spaces']:
                house_dict = self.board['spaces'][property]
                if house_dict['type'] == 'color_property':
                    try:
                        embed_properties_dict[house_dict['color']
                                              ] += self.str_embed_properties(property)
                    # monopolies.append() is in the except block because it only happens once
                    except KeyError:
                        embed_properties_dict[house_dict['color']
                                              ] = self.str_embed_properties(property)
                        monopolies.append(house_dict['color'])
                        color_int_dict[house_dict['color']
                                       ] = house_dict['color_int']
                elif house_dict['type'] == 'service_property':
                    try:
                        embed_properties_dict[house_dict['service_property']
                                              ] += self.str_embed_properties(property)
                    except KeyError:
                        embed_properties_dict['service_property'] = self.str_embed_properties(
                            property)
                        color_int_dict['service_property'] = house_dict['color_int']
                elif house_dict['type'] == 'railroad_property':
                    try:
                        embed_properties_dict['railroad_property'] += self.str_embed_properties(
                            property)
                    except KeyError:
                        embed_properties_dict['railroad_property'] = self.str_embed_properties(
                            property)
                        color_int_dict['railroad_property'] = house_dict['color_int']

            for property in zip(embed_properties_dict.keys(), embed_properties_dict.values()):
                embed_property = discord.Embed(
                    color=color_int_dict[property[0]], timestamp=datetime.datetime.now(), description=property[1])
                embed_property.set_author(name='{} properties'.format(
                    self.order[self.pointer][0].user), icon_url=str(playing.avatar_url))
                await self.channel.send(embed=embed_property)

        # TODO
        elif self.choice == 'trade':
            pass

        # TODO
        elif self.choice == 'bankruptcy':
            pass

    async def finish_turn(self, playing: Player, debt: List[int]) -> bool:
        """
        This is called whenever the player does an action
        to end their turn

        Returns a bool to inform that the action has succeed
        """

        if self.choice == 'pay_debt':
            if playing.money < debt[0]:
                await self.channel.send('You don\'t have enough money to pay this debt!')
                return False
            else:
                playing.money -= debt[0]
                # debt[1] references the player the debt who should receive
                # the money
                # If it is None, it goes to the 'bank'
                if debt[1] is not None:
                    debt[1].money += debt[0]
                    message = f'{playing.user.mention} payed {debt[0]}$ to {debt[1].user.mention}'
                else:
                    message = f'{playing.user.mention} payed {debt[0]}$ to the bank!'
                await self.channel.send(message)
                return True

        elif self.choice == 'buy_property':
            to_buy = playing.space
            playing.space.buy_property(playing)
            message = f'{playing.user.mention} bought {to_buy.emoji} **{to_buy.name}** for {to_buy.cost}$'
            await self.channel.send(message)
            return True

        # TODO
        elif self.choice == 'auction_property':
            pass

        # TODO
        elif self.choice == 'nothing':
            return True

    # Main Game Turn
    async def play(self) -> None:
        self.in_course = True
        # Decide game order
        await self.channel.send('We will now decide the playing order!')
        rolled_dice: Dict[Player, int] = dict()
        # Roll dice to decide order
        for player in self.order:
            player.space = self.board[0]
            message = await self.channel.send(f'{player.user.mention} roll the dice')
            await message.add_reaction('🎲')
            self.valid_reactions.append('dice')
            await self.bot.wait_for('reaction_add', check=self.check_reaction)
            self.valid_reactions.clear()
            rolled_dice[player] = sum(await self.roll_dice(True))
            self.increment_pointer()
        # Sort self.order dict
        self.order = sorted(
            rolled_dice.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Set everyone's postion to the first space
        self.board[0].here = [player for player in self.order]

        # Send the game order embed
        embed_order = discord.Embed(
            title='The game order will be: ', description='', timestamp=datetime.datetime.now())
        embed_order.set_author(
            name='Let\'s Play!', icon_url='https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024')
        embed_order.set_footer(
            text=f'Monopoly Game at \'{self.channel.guild}\'')
        embed_order.set_thumbnail(url=self.order[0].avatar_url)
        for player in self.order:
            embed_order.description += str(player.user) + '\n'
        await self.channel.send(embed=embed_order)

        # Main Game loop
        doubles: int = 0
        while len(self.order) >= 1:
            playing: Player = self.order[self.pointer]
            space: Space = playing.space

            # Make embed for turn
            embed_turn = discord.Embed.from_dict(EMBEDS_GLOBAL['turn'])
            embed_turn.color = space.color_int
            embed_turn.set_author(
                name=f'{playing.user} turn',
                icon_url=str(playing.avatar_url)
            )
            embed_turn.set_thumbnail(url=space.color_int)
            embed_turn.set_footer(
                text=f'Monopoly game at \'{self.channel.guild}\'')
            embed_turn.timestamp = datetime.datetime.now()
            message_turn = await self.channel.send(embed=embed_turn)

            self.valid_reactions = ['dice', 'board',
                                    'properties', 'trade', 'bankruptcy']
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            await asyncio.gather(
                self.add_reactions_message(
                    message_turn, ['dice', 'board', 'properties', 'trade', 'bankruptcy']),
                self.bot.wait_for('reaction_add', check=self.check_reaction)
            )
            self.valid_reactions.clear()

            if self.choice == 'dice':
                info_end_turn = await self.moving_on_board(playing, doubles)
                doubles = info_end_turn['doubles']

                while not(self.choice in ['pay_debt', 'buy_property', 'auction_property', 'nothing']):
                    message_end_turn = await self.channel.send(embed=info_end_turn['embed'])
                    reactions = ['board', 'properties', 'trade', 'bankruptcy']

                    if info_end_turn['debt'][0] != 0:
                        reactions.append('pay_debt')
                    if info_end_turn['buy_property']:
                        reactions.append('buy_property')
                    if info_end_turn['auction_property']:
                        reactions.append('auction_property')
                    if reactions == ['board', 'properties', 'trade', 'bankruptcy']:
                        reactions.append('nothing')

                    self.valid_reactions = copy.copy(reactions)
                    await asyncio.gather(
                        self.add_reactions_message(
                            message_end_turn, reactions),
                        self.bot.wait_for(
                            'reaction_add', check=self.check_reaction)
                    )
                    self.valid_reactions.clear()

                    if self.choice in ['board', 'properties', 'trade', 'bankruptcy']:
                        await self.routine_checks(playing)

                    elif self.choice in reactions:
                        if not await self.finish_turn(playing, info_end_turn['debt']):
                            continue
                else:
                    if doubles != 0 and info_end_turn['dice'][0] == info_end_turn['dice'][1]:
                        continue

            else:
                await self.routine_checks(playing)
                continue

            doubles = 0
            self.increment_pointer()
