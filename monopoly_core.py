import random
import discord
import datetime
import copy
from typing import *

'''COLOR_TO_DECIMAL: Dict[str, int] = {
    "start": 1,
    "railroad_property": 1,
    "Water Works": 16776702,
    "Electric Company": 16708355,
    "luck_card0": 14516021,
    "luck_card1": 42459,
    "jailing": 27043,
    "jail": 15567909,
    "free_space": 14362410,
    "Income Tax": 1,
    "Luxury Tax": 16379444,
    "Brown Property": 8801336,
    "Light Blue Propety": 11328752,
    "Magenta Property": 12925060,
    "Orange Property": 15502124,
    "Red Property": 14361640,
    "Yellow Property": 16707591,
    "Green Property": 1288279,
    "Dark Blue Property": 26276
}'''

class Player:

    def __init__(self, user):
        self.in_prison = False
        self.space = 0
        self.properties = {}
        self.prison_free_pass = 0
        self.money = 1500
        self.user = user

class Monopoly:

    def __init__(self, players, bot, channel, board, emojis):
        self.players: List[Player] = players
        self.order: List[List[Any]] = []
        self.bot = bot
        self.channel = channel
        self.board: Dict[Any] = board
        self.pointer: int = 0
        self.emojis = emojis

    def check_die_reaction(self, reaction, user) -> bool:
        # Function used to check if user wants to roll dice
        return user == self.players[self.pointer].user and str(reaction.emoji) == "🎲"
    
    async def roll_dice(self) -> List[int]:
        dice1 = random.randrange(1, 6)
        dice2 = random.randrange(1, 6)
        await self.channel.send("{} {}".format(self.emojis["Dice{}".format(dice1)], 
                                               self.emojis["Dice{}".format(dice2)]))
        return [dice1, dice2]

    async def decide_order(self) -> None:
        await self.channel.send("We will now decide the playing order!")
        rolled_dice: Dict[Any, int] = {}
        # Roll dice to decide order
        for player in self.players:
            message = await self.channel.send("{} roll the dice".format(player.user.mention))
            await message.add_reaction("🎲")
            await self.bot.wait_for("reaction_add", check=self.check_die_reaction)
            rolled_dice[player] = sum(await self.roll_dice())
            self.increment_pointer()
        self.order = sorted(rolled_dice.items(), key=lambda x: x[1], reverse=True)
        order_copy = copy.copy(self.order)
        self.order = []
        for player in order_copy:
            self.order.append([player[0], 0])
        await self.play()

    def increment_pointer(self):
        if self.pointer == len(self.players) - 1:
            self.pointer = 0
        else:
            self.pointer += 1

    async def play(self):
        # Send the game order embed
        embed_order = discord.Embed(
            title="The game order will be: ", description="", timestamp=datetime.datetime.now())
        embed_order.set_author(name="Let's Play!", icon_url=str(
            self.bot.get_user(703970013366845470).avatar_url))
        embed_order.set_footer(
            text="Monopoly Game at \"{}\"".format(self.channel.guild))
        first = True
        for player in self.order:
            if first:
                embed_order.set_thumbnail(url=str(player[0].user.avatar_url))
            embed_order.description += str(player[0].user) + "\n"
            first = False
        await self.channel.send(embed=embed_order)

        # Game loop
        while self.order != 1:
            playing: Player = self.order[self.pointer][0]
            house: int = self.order[self.pointer][1]
            print(type(self.board["spaces"]))
            print(type(self.board["spaces"][house]))
            print(type(self.board["spaces"][house]["name"]))
            embed_turn = discord.Embed(description="Money: {}$\n \
                                                   House: {}\n \
                                                   🎲 - Roll Dice\n \
                                                   🤳 - Check Board\n \
                                                   🙄 - Check your Properties\n \
                                                   {} - Trade\n \
                                                   💸 - Declare bankruptcy".format(playing.money, \
                                                                                   self.board["spaces"][house]["name"], \
                                                                                   str(self.emojis["thonkang"])), \
                                       color=self.board["spaces"][house]["color_int"])
            embed_turn.set_author(name="{} turn".format(playing.user), icon_url=str(playing.user.avatar_url))
            embed_turn.set_thumbnail(url=self.board["spaces"][house]["image_url"])
            embed_turn.set_footer(text="Monopoly game at \"{}\"".format(self.channel.guild))
            embed_turn.timestamp = datetime.datetime.now()
            message_turn = await self.channel.send(embed=embed_turn)
            await message_turn.add_reaction("🎲")
            await message_turn.add_reaction("🤳")
            await message_turn.add_reaction("🙄")
            await message_turn.add_reaction(str(self.emojis["thonkang"]))
            await message_turn.add_reaction("💸")
            break
