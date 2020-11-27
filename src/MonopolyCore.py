import asyncio
import copy
import datetime
import json
import random
from typing import Dict, List, Tuple

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

EMOJI_REACTIONS: Dict[str, str] = {
    '🎲': 'dice',
    '<:monopoly_board:780128903012417536>': 'board',
    '<:properties:780131015581761556>': 'properties',
    '<:thonkang:779326728858370078>': 'trade',
    '💸': 'bankruptcy',
    '🤝': 'buy_property',
    '👨‍⚖️': 'auction_property',
    '🚫': 'nothing',
    '🤑': 'pay_debt',
    '🎫': 'use_prison_pass'
}

STR_EMBED_ACTION: Dict[str, str] = {
    'dice': '\n🎲 - Roll Dice',
    'board': '\n<:monopoly_board:780128903012417536> - Check Board',
    'properties': '\n<:properties:780131015581761556> - Check your Properties',
    'trade': '\n<:thonkang:779326728858370078> - Trade with other players',
    'buy_property': '\n🤝 - Buy Property',
    'bankruptcy': '\n💸 - Declare bankruptcy',
    'auction_property': '\n👨‍⚖️ - Auction this Property',
    'nothing': '\n🚫 - Do nothing and end turn',
    'pay_debt': '\n🤑 - Pay debt',
    'use_prison_pass': '\n🎫 - Use the prison free pass'
}

STR_REACTION: Dict[str, str] = dict()

for key, value in EMOJI_REACTIONS.items():
    STR_REACTION[value] = key

with open('json/embeds.json', 'r') as file:
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
        # While waiting for a reaction to be added, these are the valid ones
        # besides the standard:
        # 'board', 'properties', 'trade', 'bankruptcy'
        self.valid_reactions: List[str] = []

    def check_reaction(self, reaction: discord.Emoji, user: discord.User) -> bool:
        self.choice = EMOJI_REACTIONS[str(reaction.emoji)]
        try:
            return user == self.order[self.pointer].user and \
                EMOJI_REACTIONS[str(reaction.emoji)
                                ] in self.valid_reactions
        except KeyError:
            return False

    async def roll_dice(self, announce: bool) -> Tuple[int]:
        """
        Function to roll the dice,

        Announce sends the dice emoji directly to self.channel.

        Returns a tuple with both dice values
        """
        dice1 = random.randrange(1, 7)
        dice2 = random.randrange(1, 7)
        if announce:
            await self.channel.send('{} {}'.format(DICE_EMOJI[f'Dice{dice1}'],
                                                   DICE_EMOJI[f'Dice{dice2}']))
        return dice1, dice2

    def increment_pointer(self) -> None:
        if self.pointer >= len(self.order) - 1:
            self.pointer = 0
        else:
            self.pointer += 1

    def add_reactions_embed(self, embed: discord.Embed) -> discord.Embed:
        for reaction in self.valid_reactions:
            embed.description += STR_EMBED_ACTION[reaction]
        return embed

    async def add_reactions_message(self, message):
        for reaction in self.valid_reactions:
            await message.add_reaction(STR_REACTION[reaction])

    def add_reactions_list(self, info_end_turn, playing) -> Tuple[str]:
        self.valid_reactions = ['board', 'properties', 'trade', 'bankruptcy']

        if info_end_turn['prison_break']:
            if info_end_turn['debt'][0] != 0:
                self.valid_reactions.append('pay_debt')
                if playing.prison_free_pass != 0:
                    self.valid_reactions.append('use_prison_pass')
            else:
                self.valid_reactions.append('nothing')
        elif info_end_turn['debt'][0] != 0:
            self.valid_reactions.append('pay_debt')
        if info_end_turn['buy_property']:
            self.valid_reactions.append('buy_property')
        if info_end_turn['auction_property']:
            self.valid_reactions.append('auction_property')
        if self.valid_reactions == ['board', 'properties', 'trade', 'bankruptcy']:
            self.valid_reactions.append('nothing')

    async def player_turn(self, playing, doubles, dice=[0, 0]) -> Dict:
        """
        This is called whenever the player rolls the dice

        Returns a Dict of all the information relevant for
        later use
        """

        # debt = [amount of money, player object reference]
        debt: List[int] = [0, None]
        buy_property: bool = False
        auction_property: bool = False

        # Embed making
        embed_landing = discord.Embed.from_dict(EMBEDS_GLOBAL['landing'])
        embed_landing.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_landing.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))

        # Roll dice if not provided and check for doubles
        is_double = False
        if sum(dice) == 0:
            dice = await self.roll_dice(False)
            is_double = dice[0] == dice[1]
        jailing = False
        if is_double:
            if doubles == 2:
                embed_landing.description = 'You rolled a double 3 times!\n \
                                             You are going to Brazil'
                jailing = True
            else:
                doubles += 1
                embed_landing.description += '\nYou rolled a double! You can play again!'
        # Call move_on_board method and store space
        space = self.board.move_on_board(
            playing, dice=sum(dice), jailing=jailing)

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
        if issubclass(type(space), MonopolyProperty):
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

        elif issubclass(type(space), LuckSpace):
            pass

        elif issubclass(type(space), Tax):
            debt = space.pay_rent()
            embed_landing.description += '\nYou must pay {} to the bank'.format(
                debt[0])

        elif issubclass(type(space), Jailing):
            self.board.move_on_board(playing, jailing=True)
            embed_landing.description += '\nYou\'re going to Jail'

        return {
            'doubles': doubles,
            'debt': debt,
            'buy_property': buy_property,
            'auction_property': auction_property,
            'embed': embed_landing,
            'dice': dice,
            'prison_break': False
        }

    async def prisoner_turn(self, playing):
        """
        Calls if prisoner decides to roll dice
        """

        debt: List[int] = [0, None]
        embed_prisoner = discord.Embed.from_dict(EMBEDS_GLOBAL['prisoner'])
        embed_prisoner.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_prisoner.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))

        dice = await self.roll_dice(False)
        prison_break = False
        if dice[0] == dice[1]:
            embed_prisoner.description += '\nYou rolled a double! You are out of prison!'
            prison_break = True
        elif playing.in_prison > 1:
            embed_prisoner.description += '\nYou didn\'t roll a double!'
            playing.in_prison -= 1
        elif playing.in_prison == 1:
            embed_prisoner.description += '\nYou didn\'t roll a double and you must pay a fine (50$) \
                                            or use a prison free pass to get out'
            prison_break = True
            debt[0] = 50

        embed_prisoner.description = embed_prisoner.description.format(
            dice1=DICE_EMOJI[f'Dice{dice[0]}'],
            dice2=DICE_EMOJI[f'Dice{dice[1]}'],
            sum_dice=sum(dice)
        )
        embed_prisoner.color = self.board[10].color_int
        embed_prisoner.timestamp = datetime.datetime.now()
        embed_prisoner.set_thumbnail(
            url=self.board[10].image_url)

        return {
            'doubles': 0,
            'debt': debt,
            'buy_property': False,
            'auction_property': False,
            'embed': embed_prisoner,
            'dice': dice,
            'prison_break': prison_break
        }

    # THERE'S STILL STUFF TO DO IN HERE
    async def routine_checks(self, playing) -> None:
        # Show Board
        if self.choice == 'board':
            for embed in self.board.board_embeds():
                embed = discord.Embed.from_dict(embed)
                await self.channel.send(embed=embed)

        # Show Player Properties
        elif self.choice == 'properties':
            for embed_dict in playing.properties_embed()['embeds']:
                embed = discord.Embed.from_dict(embed_dict)
                await self.channel.send(embed=embed)

        # TODO
        elif self.choice == 'trade':
            pass

        # TODO
        elif self.choice == 'bankruptcy':
            pass

    async def finish_turn(self, playing: Player, debt: List[int], prison_break: bool) -> bool:
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
                

        elif self.choice == 'buy_property':
            to_buy = playing.space
            playing.space.buy_property(playing)
            message = f'{playing.user.mention} bought {to_buy.emoji} **{to_buy.name}** for {to_buy.cost}$'
            await self.channel.send(message)
            

        # TODO
        elif self.choice == 'auction_property':
            pass

        elif self.choice == 'use_prison_pass':
            playing.prison_free_pass -= 1
        
        if prison_break:
            playing.in_prison = 0

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
        self.order.clear()
        # Sort self.order dict
        self.rolled_dice = sorted(
            rolled_dice.items(),
            key=lambda x: x[1],
            reverse=True
        )
        self.order = [player for player, shit in rolled_dice.items()]

        # Set everyone's postion to the first space
        self.board[0].here = [player for player in self.order]

        # Send the game order embed
        embed_order = discord.Embed(
            title='The game order will be: ', description='', timestamp=datetime.datetime.now())
        embed_order.set_author(
            name='Let\'s Play!', icon_url='https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024')
        embed_order.set_footer(
            text=f'Monopoly Game at \'{self.channel.guild}\'')
        embed_order.set_thumbnail(url=self.order[0].user.avatar_url)
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
            embed_turn.set_thumbnail(url=space.image_url)
            embed_turn.set_footer(
                text=f'Monopoly game at \'{self.channel.guild}\'')
            embed_turn.timestamp = datetime.datetime.now()
            embed_turn.description = embed_turn.description.format(
                money=playing.money,
                space=playing.space.name,
                prison_free_pass=playing.prison_free_pass
            )

            self.valid_reactions = ['dice', 'board',
                                    'properties', 'trade', 'bankruptcy']

            # Check if player is in prison
            if playing.in_prison != 0:
                self.valid_reactions.append('pay_debt')
                if playing.prison_free_pass != 0:
                    self.valid_reactions.append('use_prison_pass')
                embed_turn.description += f'\n**You\'re in jail\nTurns left in prison: {playing.in_prison}**'
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            self.add_reactions_embed(embed_turn)

            message_turn = await self.channel.send(embed=embed_turn)

            await asyncio.gather(
                self.add_reactions_message(message_turn),
                self.bot.wait_for('reaction_add', check=self.check_reaction)
            )
            self.valid_reactions.clear()

            if self.choice == 'dice':
                if playing.in_prison >= 1:
                    info_end_turn = await self.prisoner_turn(playing)
                else:
                    info_end_turn = await self.player_turn(playing, doubles)
                doubles = info_end_turn['doubles']
                self.add_reactions_list(info_end_turn, playing)

                while not self.choice in ['pay_debt', 'buy_property', 'auction_property', 'nothing', 'use_prison_pass']:
                    embed_end_turn = copy.copy(info_end_turn['embed'])
                    embed_end_turn = self.add_reactions_embed(embed_end_turn)
                    message_end_turn = await self.channel.send(embed=embed_end_turn)

                    await asyncio.gather(
                        self.add_reactions_message(
                            message_end_turn),
                        self.bot.wait_for(
                            'reaction_add', check=self.check_reaction)
                    )

                    if self.choice in ['board', 'properties', 'trade', 'bankruptcy']:
                        await self.routine_checks(playing)

                    elif self.choice in self.valid_reactions:
                        if not await self.finish_turn(playing, info_end_turn['debt'], info_end_turn['prison_break']):
                            self.valid_reactions.clear()
                            continue
                else:
                    if info_end_turn['prison_break']:
                        info_end_turn = await self.player_turn(playing, 0, info_end_turn['dice'])
                        continue
                    elif doubles != 0 and info_end_turn['dice'][0] == info_end_turn['dice'][1]:
                        continue

            elif self.choice == 'pay_debt':
                self.finish_turn(playing, [50, None], True)
                continue

            elif self.choice == 'use_prison_pass':
                self.finish_turn(playing, [0, None], True)
                continue

            else:
                await self.routine_checks(playing)
                continue

            doubles = 0
            self.increment_pointer()
