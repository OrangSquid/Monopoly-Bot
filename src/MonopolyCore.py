import asyncio
import datetime
import json
import random
from random import choice
from typing import Dict, List, Tuple, Union, Callable

import discord
from discord.ext import commands

from .Board import Board
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
        self.order: List[Player] = players
        self.bot: commands.AutoShardedBot = bot
        self.channel: discord.Channel = channel
        self.board: Board = board
        self.choice: str = ''
        self.houses: int = 32
        self.hotels: int = 12
        self.doubles: int = 0
        self.dice: Tuple[int] = (0, 0)
        self.prison_broke = False
        # pointer starts at -1 to compensate for the increment
        # __next__ does before it returns the player
        self._pointer: int = -1
        self._end_turn: bool = False
        # While waiting for a reaction to be added, these are the valid ones
        # besides the standard:
        # 'board', 'properties', 'trade', 'bankruptcy'
        self.valid_reactions: List[str] = list()

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
        self.choice = Reactions.EMOJI_REACTIONS[str(reaction.emoji)]
        if str(reaction.emoji) in Reactions.EMOJI_REACTIONS:
            return user == self.playing.user and self.choice in self.valid_reactions
        else:
            return False

    async def pay_debt(self):
        pass

    async def trade(self):
        pass

    async def buy_property(self):
        pass

    async def declare_bankruptcy(self):
        pass

    async def auction_property(self):
        pass

    async def pass_prison_break(self):
        pass

    async def fine_prison_break(self):
        pass

    async def nothing(self):
        pass

    async def check_board(self):
        for embed in self.board.board_embeds():
            embed = discord.Embed.from_dict(embed)
            await self.channel.send(embed=embed)

    async def check_properties(self):
        for embed in self.playing.properties_embed():
            embed = discord.Embed.from_dict(embed)
            await self.channel.send(embed=embed)

    async def roll_dice(self, announce: bool) -> Tuple[int]:
        """
        Rolls dice,

        Announce sends the dice emoji directly to self.channel.

        Returns a tuple with both dice values
        """
        dice1 = random.randrange(1, 7)
        dice2 = random.randrange(1, 7)
        if announce:
            await self.channel.send('{} {}'.format(DICE_EMOJI[f'Dice{dice1}'],
                                                   DICE_EMOJI[f'Dice{dice2}']))
        return dice1, dice2

    async def player_turn(self) -> Dict:
        """
        This is called whenever the player rolls the dice

        Returns a Dict of all the information relevant for
        later use
        """
        dice = self.dice
        playing = self.playing

        # Embed making
        embed_landing = discord.Embed.from_dict(EMBEDS_GLOBAL['landing'])
        embed_landing.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_landing.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))
        embed_landing.timestamp = datetime.datetime.now()

        # Roll dice if not provided and check for doubles
        jailing = False
        if self.dice[0] == dice[1]: 
            if self.doubles == 2:
                embed_landing.description = 'You rolled a double 3 times!\n \
                                             You are going to Brazil'
                jailing = True
                self._end_turn = True
            else:
                self.doubles += 1
                embed_landing.description += '\nYou rolled a double! You can play again!'
        else:
            self._end_turn = True
        # Call move_on_board method and store space
        space, give_salary = self.board.move_on_board(
            playing, dice=sum(dice), jailing=jailing)

        # Embed Editing with space
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
        if give_salary:
            embed_landing.description += f'\n**You passed by GO!\nYou received {self.board.salary}**'
            playing.money += self.board.salary
        
        event = space.event(self.playing, embed_landing)

        return event, embed_landing


    async def prisoner_turn(self):
        """
        Calls if prisoner decides to roll dice
        """

        playing = self.playing
        event: str = str()

        embed_prisoner = discord.Embed.from_dict(EMBEDS_GLOBAL['prisoner'])
        embed_prisoner.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_prisoner.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))

        dice = await self.roll_dice(False)
        if dice[0] == dice[1]:
            embed_prisoner.description += '\nYou rolled a double! You are out of prison!'
            event = 'double_prison_break'
        elif playing.in_prison > 1:
            embed_prisoner.description += '\nYou didn\'t roll a double!'
            playing.in_prison -= 1
            event = 'nothing'
        elif playing.in_prison == 1:
            embed_prisoner.description += '\nYou didn\'t roll a double and you must pay a fine (50$) \
                                            or use a prison free pass to get out'
            event = 'fine_prison_break'

        embed_prisoner.description = embed_prisoner.description.format(
            dice1=DICE_EMOJI[f'Dice{dice[0]}'],
            dice2=DICE_EMOJI[f'Dice{dice[1]}'],
            sum_dice=sum(dice)
        )
        embed_prisoner.color = self.board[10].color_int
        embed_prisoner.timestamp = datetime.datetime.now()
        embed_prisoner.set_thumbnail(
            url=self.board[10].image_url)
        
        return event, embed_prisoner

    # To be purged from existence
    '''async def finish_turn(self, playing: Player, debt: List[int]) -> bool:
        """
        This is called whenever the player does an action
        to end their turn

        Returns a bool to inform that the action has succeed
        """

        message = str()

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
        return True'''

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
        self.valid_reactions = ['board', 'properties', 'trade', 'bankruptcy']
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
            self._end_turn = False
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

            # Check if player is in prison
            if playing.in_prison != 0:
                prisoner = True
                self.valid_reactions.append('dice_prison')
                self.valid_reactions.append('fine_prison_break')
                if playing.prison_free_pass != 0:
                    self.valid_reactions.append('pass_prison_break')
                embed_turn.description += f'\n**You\'re in jail\nTurns left in prison: {playing.in_prison}**'
            else:
                prisoner = False
                self.valid_reactions.append('dice')
            print(self.valid_reactions)
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            Reactions.add_reactions_embed(embed_turn, self.valid_reactions)

            if not self.prison_broke:
                self.dice = await self.roll_dice(False)
                message_turn = await self.channel.send(embed=embed_turn)

                await asyncio.gather(
                    Reactions.add_reactions_message(
                        message_turn, self.valid_reactions),
                    self.bot.wait_for('reaction_add', check=self.check_reaction)
                )
                event, embed_finish = await self.CHOICE_SWICTHER[self.choice](self)
            else:
                event, embed_finish = await self.player_turn()

            self.choice = str()
            del self.valid_reactions[4:]
            
            if event is not None and not prisoner:
                if event == 'jailing':
                    self.board[10].lock_prisoner(playing)
                    self.valid_reactions.append('nothing')
                else:
                    self.valid_reactions.append(event)
                
                if event == 'buy_property':
                    self.valid_reactions.append('auction_property')
            
            elif event is not None and prisoner:
                if event == 'double_prison_break':
                    self.valid_reactions.append('nothing')
                elif event == 'fine_prison_break':
                    self.prison_broke = True
                    self.valid_reactions.append('fine_prison_break')
                    if playing.prison_free_pass != 0:
                        self.valid_reactions.append('pass_prison_break')
                else:
                    self.valid_reactions.append('nothing')
            
            Reactions.add_reactions_embed(embed_finish, self.valid_reactions)

            while self.choice not in self.valid_reactions[4:]:
                message_finish = await self.channel.send(embed=embed_finish)
                await asyncio.gather(
                    Reactions.add_reactions_message(
                        message_finish, self.valid_reactions),
                    self.bot.wait_for('reaction_add', check=self.check_reaction)
                )
                await self.CHOICE_SWICTHER[self.choice](self)
            
            del self.valid_reactions[4:]

        await self.channel.send('The game has ended')
        await self.channel.send(f'{self[0]} is the winner')

    CHOICE_SWICTHER: Dict[str, Callable] = {
        'dice': player_turn,
        'dice_prison': prisoner_turn,
        'board': check_board,
        'properties': check_properties,
        'trade': trade,
        'buy_property': buy_property,
        'bankruptcy': declare_bankruptcy,
        'auction_property': auction_property,
        'nothing': nothing,
        'pay_debt': pay_debt,
        'use_prison_pass': pass_prison_break,
        'fine_prison_break': fine_prison_break
    }
