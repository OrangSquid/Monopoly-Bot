import asyncio
import copy
import datetime
import json
import random
from random import choice
from typing import Dict, List, Tuple, Union

import discord
from discord.ext import commands

from .Board import Board
# from .LuckCard import LuckCard
from .Player import Player
from .Spaces import (Jailing, Space, Tax, LuckSpace, MonopolyProperty)
from . import Reactions

DICE_EMOJI = {
    'Dice1': '<:Dice1:748278516289896468>',
    'Dice2': '<:Dice2:748278516319256696>',
    'Dice3': '<:Dice3:748278516226719855>',
    'Dice4': '<:Dice4:748278516352549025>',
    'Dice5': '<:Dice5:748278516272857089>',
    'Dice6': '<:Dice6:748278516516388905>'
}

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
        self.in_course: bool = False
        self.order: List[Player] = players
        self.bot: commands.AutoShardedBot = bot
        self.channel: discord.Channel = channel
        self.board: Board = board
        self.choice: str = ''
        self.houses: int = 32
        self.hotels: int = 12
        self.doubles: int = 0
        # pointer starts at -1 to compensate for the increment
        # __next__ does before it returns the player
        self._pointer: int = -1
        self._end_turn: bool = False
        # While waiting for a reaction to be added, these are the valid ones
        # besides the standard:
        # 'board', 'properties', 'trade', 'bankruptcy'
        self.valid_reactions: List[str] = []

    def __getitem__(self, index):
        return self.order[index]

    def __iter__(self):
        return self

    def __next__(self):
        if len(self.order) == 1:
            raise StopIteration
        elif not self._end_turn:
            return self[self._pointer]
        elif self._pointer < len(self.order) - 1:
            self._pointer += 1
            return self[self._pointer]
        else:
            self._pointer = 0
            return self[0]

    def check_reaction(self, reaction: discord.Emoji, user: discord.User) -> bool:
        if str(reaction.emoji) in Reactions.EMOJI_REACTIONS:
            return user == self.playing.user and \
                Reactions.EMOJI_REACTIONS[str(
                    reaction.emoji)] in self.valid_reactions
        else:
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

    async def player_turn(self, playing, dice=[0, 0]) -> Dict:
        """
        This is called whenever the player rolls the dice

        Returns a Dict of all the information relevant for
        later use
        """

        # debt = [amount of money, player object reference]
        debt: List[Union[int, Player]] = [0, None]
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
        jailing = False
        if sum(dice) == 0:
            dice = await self.roll_dice(False)
            is_double = dice[0] == dice[1]
        if is_double:
            if self.doubles == 2:
                embed_landing.description = 'You rolled a double 3 times!\n \
                                             You are going to Brazil'
                jailing = True
            else:
                self.doubles += 1
                embed_landing.description += '\nYou rolled a double! You can play again!'
        # Call move_on_board method and store space
        previous_index = playing.space.index
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

        # Check if player has passed GO
        if previous_index > space.index and playing.in_prison == 0:
            embed_landing.description += f'\n**You passed by GO!\nYou received {self.board.salary}**'
            playing.money += self.board.salary

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
            embed_landing.description += f'\nYou must pay {debt[0]} to the bank'

        elif issubclass(type(space), Jailing):
            self.board.move_on_board(playing, jailing=True)
            embed_landing.description += '\nYou\'re going to Jail'

        

    async def prisoner_turn(self, playing):
        """
        Calls if prisoner decides to roll dice
        """

        choice: str = ''

        embed_prisoner = discord.Embed.from_dict(EMBEDS_GLOBAL['prisoner'])
        embed_prisoner.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_prisoner.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))

        dice = await self.roll_dice(False)
        if dice[0] == dice[1]:
            embed_prisoner.description += '\nYou rolled a double! You are out of prison!'
        elif playing.in_prison > 1:
            embed_prisoner.description += '\nYou didn\'t roll a double!'
            playing.in_prison -= 1
        elif playing.in_prison == 1:
            embed_prisoner.description += '\nYou didn\'t roll a double and you must pay a fine (50$) \
                                            or use a prison free pass to get out'

        embed_prisoner.description = embed_prisoner.description.format(
            dice1=DICE_EMOJI[f'Dice{dice[0]}'],
            dice2=DICE_EMOJI[f'Dice{dice[1]}'],
            sum_dice=sum(dice)
        )
        embed_prisoner.color = self.board[10].color_int
        embed_prisoner.timestamp = datetime.datetime.now()
        embed_prisoner.set_thumbnail(
            url=self.board[10].image_url)

    # THERE'S STILL STUFF TO DO IN HERE
    async def routine_checks(self, playing) -> None:
        """
        Routine_checks can be called at the end or beginning of a turn

        It lets the player check the board, their properties, trade and
        declare bankruptcy
        """
        # Show Board
        if self.choice == 'board':
            for embed in self.board.board_embeds():
                embed = discord.Embed.from_dict(embed)
                await self.channel.send(embed=embed)

        # Show Player Properties
        elif self.choice == 'properties':
            for embed in playing.properties_embed():
                embed = discord.Embed.from_dict(embed)
                await self.channel.send(embed=embed)

        # TODO
        elif self.choice == 'trade':
            pass

        # TODO
        elif self.choice == 'bankruptcy':
            pass

    async def choice_to_end(self):
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

        elif self.choice == 'buy_property':
            to_buy = playing.space
            to_buy.buy_property(playing)
            message = f'{playing.user.mention} bought {to_buy.emoji} **{to_buy.name}** for {to_buy.cost}$'

        # TODO
        elif self.choice == 'auction_property':
            pass

        elif self.choice == 'use_prison_pass':
            playing.prison_free_pass -= 1
            playing.in_prison = 0
            message = f'{playing.user.mention} used a prison free pass. They\'re now free'

        elif self.choice == 'prison_break':
            if playing.money < 50:
                await self.channel.send('You don\'t have enough money to pay the fine!')
                return False
            else:
                playing.money -= 50
                playing.in_prison = 0
                message = f'{playing.user.mention} payed a 50$ fine. They\'re now free'

        await self.channel.send(message)
        return True

    # Main Game Turn
    async def play(self) -> None:
        self.in_course = True
        # Decide game order
        await self.channel.send('We will now decide the playing order!')
        rolled_dice: Dict[Player, int] = dict()
        # Roll dice to decide order
        for player in self.order:
            self.playing = player
            player.space = self.board[0]
            message = await self.channel.send(f'{player.user.mention} roll the dice')
            await message.add_reaction('🎲')
            self.valid_reactions.append('dice')
            await self.bot.wait_for('reaction_add', check=self.check_reaction)
            self.valid_reactions.clear()
            rolled_dice[player] = sum(await self.roll_dice(True))
        self.order.clear()
        # Sort self.order dict
        rolled_dice = sorted(
            rolled_dice.items(),
            key=lambda x: x[1],
            reverse=True
        )
        self.order = [player for player, dice in rolled_dice]

        # Set everyone's postion to the first space
        self.board[0].here = [player for player in self.order]

        # Send the game order embed
        embed_order = discord.Embed(
            title='The game order will be: ', description='', timestamp=datetime.datetime.now())
        embed_order.set_author(
            name='Let\'s Play!', icon_url='https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024')
        embed_order.set_footer(
            text=f'Monopoly Game at \'{self.channel.guild}\'')
        embed_order.set_thumbnail(url=self[0].user.avatar_url)
        for player in self.order:
            embed_order.description += str(player.user) + '\n'
        await self.channel.send(embed=embed_order)

        # Main Game loop
        for playing in self:
            self.playing = playing
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
                self.valid_reactions.append('prison_break')
                if playing.prison_free_pass != 0:
                    self.valid_reactions.append('use_prison_pass')
                embed_turn.description += f'\n**You\'re in jail\nTurns left in prison: {playing.in_prison}**'
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            Reactions.add_reactions_embed(embed_turn, self.valid_reactions)

            message_turn = await self.channel.send(embed=embed_turn)

            await asyncio.gather(
                Reactions.add_reactions_message(message_turn, self.valid_reactions),
                self.bot.wait_for('reaction_add', check=self.check_reaction)
            )
            self.valid_reactions.clear()

            if self.choice == 'dice' and playing.in_prison >= 1:
                await self.prisoner_turn(playing)

            elif self.choice == 'dice' and playing.in_prison == 0:
                await self.player_turn(playing, doubles)

            elif self.choice == 'prison_break':
                space.release_prison(playing, 'prison_break')

            elif self.choice == 'use_prison_pass':
                space.release_prisoner(playing, 'use_prison_pass')

            else:
                await self.routine_checks(playing)
        
        await self.channel.send('The game has ended')
        await self.channel.send(f'{self[0]} is the winner')
