import random
import discord
import datetime
import copy
import asyncio
import json
from typing import *

# TODO: ADD HOUSE LEVEL REFERENCE TO RAILROAD PROPERTIES AND SERVICE PROPERTIES

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

    def __init__(self, user: discord.User):
        self.in_prison = False
        self.space = 0
        self.properties: Dict[str, Any] = {
            "service_properties": 0, "railroad_properties": 0, "properties_spaces": []}
        self.prison_free_pass = 0
        self.money = 1500
        self.user = user
        self.avatar_url = str(user.avatar_url)


class Monopoly:

    def __init__(self, players, bot, channel, board, emojis, embeds):
        self.players: List[Player] = players
        self.order: List[List[Any]] = []
        self.bot = bot
        self.channel = channel
        self.board: Dict[Any] = board
        self.pointer: int = 0
        self.emojis: Dict[str, str] = emojis
        self.choice: str = ""
        self.embeds: Dict[str, Dict[str, str]] = embeds
        self.houses = 32
        self.hotels = 12
        self.emoji_to_str_reactions: Dict[str, str] = {"🎲": "dice",
                                                       str(self.emojis["monopoly_board"]): "board",
                                                       str(self.emojis["properties"]): "properties",
                                                       str(self.emojis["thonkang"]): "trade",
                                                       "💸": "bankruptcy",
                                                       "🤝": "buy_property",
                                                       "👨‍⚖️": "auction_property",
                                                       "🚫": "nothing",
                                                       "🤑": "pay_debt"}
        self.str_to_emoji_reactions: Dict[str, str] = {}
        for key, value in zip(self.emoji_to_str_reactions.keys(), self.emoji_to_str_reactions.values()):
            self.str_to_emoji_reactions[value] = key
        # While waiting for a reaction to be added, these are the valid ones besides the standard:
        # "board", "properties", "trade", "bankruptcy"
        self.valid_reactions: List[str] = []
        for space in self.board["spaces"]:
            if space["type"].endswith("property"):
                space["space"] = None
        with open("board.json", "w") as file:
            json.dump(self.board, file, indent="\t")

    ''' def check_die_reaction(self, reaction: discord.Emoji, user: discord.User) -> bool:
            # Function used to check if user wants to roll dice
            return user == self.players[self.pointer].user and str(reaction.emoji) == "🎲"'''

    def check_reaction(self, reaction: discord.Emoji, user: discord.User) -> bool:
        self.choice = self.emoji_to_str_reactions[str(reaction.emoji)]
        try:
            try:
                return user == self.order[self.pointer][0].user and str(reaction.emoji) in self.emoji_to_str_reactions.keys() and self.emoji_to_str_reactions[str(reaction.emoji)] in self.valid_reactions
            except IndexError:
                return user == self.players[self.pointer].user and str(reaction.emoji) in self.emoji_to_str_reactions.keys() and self.emoji_to_str_reactions[str(reaction.emoji)] in self.valid_reactions
        except KeyError:
            return False

    async def roll_dice(self, announce: bool) -> List[int]:
        dice1 = random.randrange(1, 6)
        dice2 = random.randrange(1, 6)
        if announce:
            await self.channel.send("{} {}".format(self.emojis["Dice{}".format(dice1)],
                                                   self.emojis["Dice{}".format(dice2)]))
        return [dice1, dice2]

    # TODO
    async def buy_property(self):
        pass

    # TODO
    async def pay_debt(self):
        pass

    # TODO
    async def build_sell_house(self):
        pass

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
            await message.add_reaction(self.str_to_emoji_reactions[reaction])

    async def moving_on_board(self, playing, house, doubles, roll_dice):
        debt: List[Any] = [0, None]
        buy_property: bool = False
        auction_property: bool = False

        # Embed making
        embed_landing = discord.Embed.from_dict(self.embeds["landing"])
        embed_landing.set_author(name="{} end turn".format(
            playing.user), icon_url=playing.avatar_url)
        embed_landing.set_footer(
            text="Monopoly game at \"{}\"".format(self.channel.guild))
        dice = await self.roll_dice(False)
        # Check for doubles
        if dice[0] == dice[1]:
            if doubles == 2:
                embed_landing.description = "You rolled a double 3 times!\n \
                                                You are going to Brazil"
            else:
                doubles += 1
                embed_landing.description += "\nYou rolled a double!, you can play again!"
        # Add total of dice and put it back into self.order
        self.board["spaces"][house]["here"] = None
        if house + sum(dice) > 39:
            house += sum(dice) - 39
        else:
            house += sum(dice)
        self.order[self.pointer][1] = house
        self.board["spaces"][house]["here"] = playing
        embed_landing.description = embed_landing.description.format(self.emojis["Dice{}".format(
            dice[0])], self.emojis["Dice{}".format(dice[1])], sum(dice), self.board["spaces"][house]["name"])
        embed_landing.color = self.board["spaces"][house]["color_int"]
        embed_landing.timestamp = datetime.datetime.now()
        embed_landing.set_thumbnail(
            url=self.board["spaces"][house]["image_url"])

        if self.board["spaces"][house]["type"].endswith("property"):
            # Buy or auction
            if self.board["spaces"][house]["owner"] == None:
                if self.board["spaces"][house]["cost"] < playing.money:
                    embed_landing.description += "\nYou can buy or auction this property!"
                    buy_property = True
                    auction_property = True
                else:
                    embed_landing.description += "\nYou don't have enough money!\nYou must auction this property!"
                    auction_property = True
            # Mortgaged
            elif self.board[house]["mortgage"]:
                embed_landing.description += "\nThis property is mortgaged!\nYou don't need to pay rent!"
            # Own property
            elif self.board["spaces"][house]["owner"] == playing:
                embed_landing.description += "\nYou landed on your own property!"
            # Pay Rent
            else:
                if self.board[house]["type"] == "color_property":
                    debt = [self.board["spaces"]["rent"][self.board["spaces"]
                                                         [house]["house_level"]], self.board["spaces"][house]["owner"]]
                elif self.board[house]["type"] == "service_property":
                    debt = [sum(dice) * 6 * self.board["spaces"][house]
                            ["owner"].properties["serivce_properties"] - 2, self.board["spaces"][house]["owner"]]
                elif self.board[house]["type"] == "railroad_property":
                    railroad_dict = {1: 25, 2: 50, 3: 100, 4: 200}
                    debt = [railroad_dict[self.board["spaces"][house]
                                          ["owner"].properties["railroad_properties"]], self.board["spaces"][house]["owner"]]
                embed_landing.description += "\nYou must pay {} to {}".format(debt[0], debt[1])

        # TODO
        elif self.board["spaces"][house]["type"] == "lucky_card0":
            pass

        # TODO
        elif self.board["spaces"][house]["type"] == "lucky_card1":
            pass

        # TODO
        elif self.board["spaces"][house]["type"] == "tax":
            pass

        return {"doubles": doubles, "debt": debt, "buy_property": buy_property, "auction_property": auction_property, "embed": embed_landing, "dice": dice}

    async def routine_checks(self, playing, house) -> None:
        if self.choice == "board":
            embed_board = discord.Embed(color=self.board["spaces"][house]["color_int"], timestamp=datetime.datetime.now())
            embed_board.set_author(name="Monopoly Board", icon_url="https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024")
            embed_board.set_image(url="https://raw.githubusercontent.com/OrangSquid/Monopoly-Bot/master/monopoly_board.jpg")
            for space in self.board["spaces"]:
                if space["type"] == "start":
                    embed_board.description = "{} **{}**".format(space["name"])
                elif space["type"] == "color_property":
                    if space["owner"] == None:
                        embed_board.description = "{} **{}** ({})\nOwner:{}".format(self.emojis[space["color"]], space["name"], space["cost"], space["owner"])
                    else:
                        embed_board.description = "{} **{}** ({})\nOwner:{} | Rent: {} ".format(self.emojis[space["color"]], space["name"], space["cost"], space["owner"], space["rent"][space["house_level"]])
                        for house in range(space["house_level"]):
                            embed_board.description += str(self.emojis["properties"])
                elif space["type"] == "railroad_property":
                    if space["owner"] == None:
                        embed_board.description = "{} **{}** ({})\nOwner:{}".format(self.emojis["railroad_property"], space["name"], space["cost"], space["owner"])
                    else:
                        railroad_dict = {1: 25, 2: 50, 3: 100, 4: 200}
                        # TODO: FIX THIS
                        embed_board.description = "{} **{}** ({})\nOwner:{} | Rent: {} ".format(self.emojis[space["color"]], space["name"], space["cost"], space["owner"])
                elif space["type"] == "service_property":
                    pass
                elif space["type"] == "tax":
                    pass
                elif space["type"] == "luck_card0":
                    pass
                elif space["type"] == "luck_card1":
                    pass
                elif space["type"] == "jail":
                    pass
                elif space["type"] == "jailing":
                    pass
                elif space["type"] == "free_space":
                    pass
            await self.channel.send(embed=embed_board)

        # TODO
        elif self.choice == "properties":
            pass

        # TODO
        elif self.choice == "trade":
            pass

        # TODO
        elif self.choice == "bankruptcy":
            pass

    async def finish_turn(self) -> None:
        # TODO
        if self.choice == "pay_debt":
            pass

        # TODO
        elif self.choice == "buy_property":
            pass

        # TODO
        elif self.choice == "auction_property":
            pass
        
        # TODO
        else:
            return

    # Main Game Turn
    async def play(self) -> None:
        # Decide game order
        await self.channel.send("We will now decide the playing order!")
        rolled_dice: Dict[Any, int] = {}
        # Roll dice to decide order
        for player in self.players:
            message = await self.channel.send("{} roll the dice".format(player.user.mention))
            await message.add_reaction("🎲")
            self.valid_reactions.append("dice")
            await self.bot.wait_for("reaction_add", check=self.check_reaction)
            self.valid_reactions.clear()
            rolled_dice[player] = sum(await self.roll_dice(True))
            self.increment_pointer()
        self.order = sorted(rolled_dice.items(),
                            key=lambda x: x[1], reverse=True)
        order_copy = copy.copy(self.order)
        self.order = []
        for player in order_copy:
            self.order.append([player[0], 0])

        # Send the game order embed
        embed_order = discord.Embed(
            title="The game order will be: ", description="", timestamp=datetime.datetime.now())
        embed_order.set_author(
            name="Let's Play!", icon_url="https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024")
        embed_order.set_footer(
            text="Monopoly Game at \"{}\"".format(self.channel.guild))
        first: bool = True
        for player in self.order:
            if first:
                embed_order.set_thumbnail(url=player[0].avatar_url)
                first = False
            embed_order.description += str(player[0].user) + "\n"
        await self.channel.send(embed=embed_order)

        # Game loop
        doubles: int = 0
        while len(self.order) != 1:
            playing: Player = self.order[self.pointer][0]
            house: int = self.order[self.pointer][1]

            embed_turn = discord.Embed.from_dict(self.embeds["turn"])
            embed_turn.description = embed_turn.description.format(playing.money,
                                                                   self.board["spaces"][house]["name"],
                                                                   playing.prison_free_pass,
                                                                   str(self.emojis["thonkang"]))
            embed_turn.color = self.board["spaces"][house]["color_int"]
            embed_turn.set_author(name="{} turn".format(
                playing.user), icon_url=str(playing.avatar_url))
            embed_turn.set_thumbnail(
                url=self.board["spaces"][house]["image_url"])
            embed_turn.set_footer(
                text="Monopoly game at \"{}\"".format(self.channel.guild))
            embed_turn.timestamp = datetime.datetime.now()
            message_turn = await self.channel.send(embed=embed_turn)
            # This block is in a gather function to detect possible reaction adds
            # while the bot adds all the possibilites
            self.valid_reactions = ["dice", "board", "properties", "trade", "bankruptcy"]
            await asyncio.gather(
                self.add_reactions_message(message_turn, ["dice", "board", "properties", "trade", "bankruptcy"]),
                self.bot.wait_for("reaction_add", check=self.check_reaction)
            )
            self.valid_reactions.clear()

            if self.choice == "dice":
                info_end_turn = await self.moving_on_board(
                    playing, house, doubles, True)
                doubles = info_end_turn["doubles"]

                while not(self.choice in ["debt", "buy_property", "auction_property", "nothing"]):
                    message_end_turn = await self.channel.send(embed=info_end_turn["embed"])
                    reactions = ["board", "properties", "trade", "bankruptcy"]

                    if info_end_turn["debt"][0] != 0:
                        reactions.append("pay_debt")
                    if info_end_turn["buy_property"]:
                        reactions.append("buy_property")
                    if info_end_turn["auction_property"]:
                        reactions.append("auction_property")
                    if reactions == ["board", "properties", "trade", "bankruptcy"]:
                        reactions.append("nothing")

                    self.valid_reactions = reactions
                    await asyncio.gather(
                        self.add_reactions_message(message_end_turn, reactions),
                        self.bot.wait_for("reaction_add", check=self.check_reaction)
                    )
                    self.valid_reactions.clear()

                    if self.choice in ["board", "properties", "trade", "bankruptcy"]:
                        await self.routine_checks(playing, house)

                    elif self.choice in reactions:
                        self.finish_turn()
                else:
                    if doubles != 0 and info_end_turn["dice"][0] == info_end_turn["dice"][1]:
                        continue

            else:
                await self.routine_checks(playing, house)
                continue

            doubles = 0
            self.increment_pointer()
