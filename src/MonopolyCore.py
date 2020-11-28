import asyncio
import datetime
import json
import random
from typing import Callable, Dict, List, Tuple, TypeVar

import discord
from discord.ext import commands

from . import Reactions
from .Board import Board
from .Board.Spaces.LuckSpace import LuckSpace
from .Board.Spaces.MonopolyProperty import MonopolyProperty
from .Board.Spaces.Tax import Tax
from .Player import Player

Space = TypeVar('Space')

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
        self._teleport: int = -1
        self._space_backwards: int = 0
        self._jailing: bool = False
        self.rent_multiplier = 1
        # pointer starts at -1 to compensate for the increment
        # __next__ does before it returns the player
        self._pointer: int = 0
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
        space = self.playing.space
        if issubclass(type(space), MonopolyProperty) or issubclass(type(space), Tax):
            rent, receiver = space.pay_rent(self.rent_multiplier)
            if rent > self.playing.money:
                await self.channel.send('You don\'t have enough money to pay this debt!')
                return False
            elif issubclass(type(space), Tax):
                self.playing.money -= rent
                await self.channel.send(f'{self.playing.user.mention} ({self.playing.money}$) payed {space.rent} to the bank')
            else:
                self.playing.money -= rent
                receiver.money += rent
                await self.channel.send(f'{self.playing.user.mention} ({self.playing.money}$) payed {space.rent} to {receiver.user.mention} ({receiver.money}$)')
                self.rent_multiplier = 1
            return True
        elif issubclass(type(space), LuckSpace):
            card = space.deck[-1]
            if card['type'] == 'pay_money':
                if card['money'] > self.playing.money:
                    await self.channel.send('You don\'t have enough money to pay this debt!')
                    return False
                else:
                    self.playing.money -= card['money']
                    await self.channel.send(f'{self.playing.user.mention} ({self.playing.money}$) payed {space.rent} to the bank')
                    return True
            elif card['type'] == 'pay_money_players':
                if card['money'] * len(self.order) > self.playing.money:
                    await self.channel.send('You don\'t have enough money to pay this debt!')
                    return False
                else:
                    self.playing.money -= card['money'] * len(self.order)
                    for player in self.order:
                        player.money += card['money'] 
                    await self.channel.send(f'{self.playing.user.mention} ({self.playing.money}$) payed each player {card["money"]}$')
                    return True
            elif card['type'] == 'house_repairs':
                if card['cost']['hotel'] * self.playing.hotels + card['cost']['house'] * self.playing.house > self.playing.money:
                    await self.channel.send('You don\'t have enough money to pay this debt!')
                    return False
                else:
                    self.playing.money -= card['cost']['hotel'] * self.playing.hotels + card['cost']['house'] * self.playing.house
                    await self.channel.send(f'{self.playing.user.mention} ({self.playing.money}$) payed {space.rent} to the bank')
                    return True

    async def trade(self):
        return None, discord.Embed(description='')

    async def buy_property(self):
        to_buy = self.playing.space
        to_buy.buy_property(self.playing)
        await self.channel.send(f'{self.playing.user.mention} bought {to_buy.emoji} **{to_buy.name}** for {to_buy.cost}$')
        return True

    async def declare_bankruptcy(self):
        return None, discord.Embed(description='')

    async def auction_property(self):
        return None, discord.Embed(description='')

    async def pass_prison_break(self):
        self[10].release_prisoner(self.playing, 'pass')
        await self.channel.send(f'{self.playing.user.mention} used a prison free pass. They\'re now free')
        return True

    async def fine_prison_break(self):
        if self.playing.money < 50:
            await self.channel.send('You don\'t have enough money to pay the fine!')
            return False
        else:
            self[10].release_prisoner(self.playing, 'fine')
            await(f'{self.playing.user.mention}({self.playing.money}$) payed a 50$ fine. They\'re now free')
            return True
    
    async def double_prison_break(self):
        await self.channel.send(f'{self.playing.user.mention} has broke out of jail with a double')
        self[10].release_prisoner(self.playing, 'double')

    async def teleport(self):
        print('we are in!')
        card = self.playing.space.deck[-1]
        if card['type'] == 'teleport':
            self._teleport = card['space']
        elif card['type'] == 'teleport_rent_multiplier':
            self.rent_multiplier = 2
            if card['space'] == 'railroad_property':
                if self.playing.space.index == 7:
                    self._teleport = 15
                elif self.playing.space.index == 22:
                    self._teleport = 25
                elif self.playing.space.index == 36:
                    self._teleport = 5
            elif card['space'] == 'service_property':
                if self.playing.space.index == 7:
                    self._teleport = 12
                elif self.playing.space.index == 22:
                    self._teleport = 28
                elif self.playing.space.index == 36:
                    self._teleport = 12
        self._end_turn = False
        
    async def space_backwards(self):
        card = self.playing.space.deck[-1]
        self._space_backwards = card['spaces']

    async def jailing(self):
        self._jailing = True

    async def nothing(self):
        pass

    async def check_board(self):
        for embed in self.board.board_embeds():
            embed = discord.Embed.from_dict(embed)
            await self.channel.send(embed=embed)
        return None, discord.Embed(description='')

    async def check_properties(self):
        for embed in self.playing.properties_embed():
            embed = discord.Embed.from_dict(embed)
            await self.channel.send(embed=embed)
        return None, discord.Embed(description='')

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

        if dice[0] == dice[1]: 
            if self.doubles == 2:
                embed_landing.description = 'You rolled a double 3 times!\n \
                                            You are going to Brazil'
                self._jailing = True
                self._end_turn = True
            else:
                self.doubles += 1
                embed_landing.description += '\nYou rolled a double! You can play again!'
        else:
            self._end_turn = True
        # Call move_on_board method and store space
        space, give_salary = self.board.move_on_board(
            playing, dice=sum(dice), jailing=self._jailing)

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
    
    async def teleport_turn(self):
        playing = self.playing
        # Embed making
        embed_landing = discord.Embed.from_dict(EMBEDS_GLOBAL['teleport'])
        embed_landing.set_author(
            name=f'{str(playing.user)} end turn', icon_url=playing.avatar_url)
        embed_landing.set_footer(
            text='Monopoly game at \'{}\''.format(self.channel.guild))
        embed_landing.timestamp = datetime.datetime.now()

        if self.dice[0] != self.dice[1]:
            self._end_turn = True

        space, give_salary = self.board.move_on_board(
            playing, teleport=self._teleport, jailing=self._jailing)
        self._teleport = -1

        embed_landing.description.format(space=space.name)
        embed_landing.color = space.color_int
        embed_landing.timestamp = datetime.datetime.now()
        embed_landing.set_thumbnail(
            url=space.image_url)
        
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

    async def play(self) -> None:
        """
        Main game loop
        """

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
        self.order = [player[0] for player in rolled_dice]

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
                embed_turn.description += f'\n**You\'re in jail\nTurns left in prison: __{playing.in_prison}__**'
            else:
                prisoner = False
                self.valid_reactions.append('dice')
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            event = str()
            embed_finish = discord.Embed()
            Reactions.add_reactions_embed(embed_turn, self.valid_reactions)

            if not self.prison_broke and self._teleport == -1 and self._space_backwards == 0:
                self.dice = await self.roll_dice(False)
                message_turn = await self.channel.send(embed=embed_turn)

                await asyncio.gather(
                    Reactions.add_reactions_message(
                        message_turn, self.valid_reactions),
                    self.bot.wait_for('reaction_add', check=self.check_reaction)
                )
                event, embed_finish = await self.CHOICE_SWICTHER[self.choice](self)
            elif self.prison_broke:
                event, embed_finish = await self.player_turn()
            elif self._teleport != -1:
                event, embed_finish = await self.teleport_turn()

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
                    self.valid_reactions.append('double_prison_break')
                elif event == 'fine_prison_break':
                    self.prison_broke = True
                    self.valid_reactions.append('fine_prison_break')
                    if playing.prison_free_pass != 0:
                        self.valid_reactions.append('pass_prison_break')
                else:
                    self.valid_reactions.append('nothing')
            
            Reactions.add_reactions_embed(embed_finish, self.valid_reactions)

            while self.choice not in self.valid_reactions[4:] and event is not None:
                message_finish = await self.channel.send(embed=embed_finish)
                await asyncio.gather(
                    Reactions.add_reactions_message(
                        message_finish, self.valid_reactions),
                    self.bot.wait_for('reaction_add', check=self.check_reaction)
                )
                if not await self.CHOICE_SWICTHER[self.choice](self):
                    continue
            
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
        'fine_prison_break': fine_prison_break,
        'double_prison_break': double_prison_break,
        'teleport': teleport,
        'space_backwards': space_backwards,
        'jailing': jailing
    }
