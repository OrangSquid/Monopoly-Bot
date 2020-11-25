import asyncio
import copy
import datetime
import json
import random
from typing import Any, Dict, List

import discord

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
        '''for space in self.board["spaces"]:
            pass
        with open("board.json", "w") as file:
            pass
            #json.dump(self.board, file, indent="\t")'''

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
        dice1 = random.randrange(1, 7)
        dice2 = random.randrange(1, 7)
        if announce:
            await self.channel.send("{} {}".format(self.emojis["Dice{}".format(dice1)],
                                                   self.emojis["Dice{}".format(dice2)]))
        return [dice1, dice2]

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

    def str_embed_properties(self, property):
        # Color_Property
        if self.board["spaces"][property]["type"] == "color_property":
            rent = self.board["spaces"][property]["rent"][self.board["spaces"]
                                                          [property]["house_level"]]
            if self.board["spaces"][property]["monopoly"] and self.board["spaces"][property]["house_level"] == 0:
                rent *= 2
            str_to_return = "\n{emoji} **{name}** ({cost}$)\nRent: {rent}$".format(
                emoji=self.emojis[self.board["spaces"][property]["color"]], name=self.board["spaces"][property]["name"], cost=self.board["spaces"][property]["cost"], rent=rent)
            if self.board["spaces"][property]["house_level"] != 5:
                for house in range(self.board["spaces"][property]["house_level"]):
                    str_to_return += str(
                        self.emojis["properties"])
            else:
                str_to_return += str(
                    self.emojis["hotel"])
            return str_to_return
        # Railroad_Property
        elif self.board["spaces"][property]["type"] == "railroad_property":
            return "\n{emoji} **{name}** ({cost}$)\nRent: {rent}$".format(
                emoji=self.emojis["railroad_property"], name=self.board["spaces"][property]["name"], cost=self.board["spaces"][property]["cost"], rent=self.board["spaces"][property]["rent"][self.board["spaces"][property]["house_level"]])
        # Service_Property
        elif self.board["spaces"][property]["type"] == "service_property":
            if self.board["spaces"][property]["name"] == "Eletric Company":
                return "\n{emoji} **{name}** ({cost}$)\nRent: {rent} * Number on Dice".format(
                    emoji=self.emojis["electric_company"], name=self.board["spaces"][property]["name"], cost=self.board["spaces"][property]["cost"], rent=6 * self.board["spaces"][property]["house_level"] - 2)
            else:
                return "\n{emoji} **{name}** ({cost}$)\nRent: {rent} * Number on Dice".format(
                    emoji=self.emojis["water_works"], name=self.board["spaces"][property]["name"], cost=self.board["spaces"][property]["cost"], rent=6 * self.board["spaces"][property]["house_level"] - 2)

    async def moving_on_board(self, playing, house_int, doubles, roll_dice) -> Dict:
        # debt = [amount of money, int refering to self.order player]
        debt: List[int] = [0, None]
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
        self.board["spaces"][house_int]["here"].remove(self.pointer)
        if house_int + sum(dice) > 39:
            house_int += sum(dice) - 40
            playing.space = house_int
        else:
            house_int += sum(dice)
            playing.space = house_int
        self.order[self.pointer][1] = house_int
        self.board["spaces"][house_int]["here"].append(self.pointer)
        house_dict = self.board["spaces"][house_int]

        # Embed
        embed_landing.description = embed_landing.description.format(self.emojis["Dice{}".format(
            dice[0])], self.emojis["Dice{}".format(dice[1])], sum(dice), house_dict["name"])
        embed_landing.color = house_dict["color_int"]
        embed_landing.timestamp = datetime.datetime.now()
        embed_landing.set_thumbnail(
            url=house_dict["image_url"])

        # Lands on property
        if house_dict["type"].endswith("property"):
            # Buy or auction
            if house_dict["owner"] == None:
                if house_dict["cost"] < playing.money:
                    embed_landing.description += "\nYou can buy or auction this property!"
                    buy_property = True
                    auction_property = True
                else:
                    embed_landing.description += "\nYou don't have enough money!\nYou must auction this property!"
                    auction_property = True
            # Mortgaged
            elif house_dict["mortgage"]:
                embed_landing.description += "\nThis property is mortgaged!\nYou don't need to pay rent!"
            # Own property
            elif house_dict["owner"] == playing:
                embed_landing.description += "\nYou landed on your own property!"
            # Pay Rent
            else:
                if house_dict["type"] == "color_property":
                    if house_dict["house_level"] == 0 and house_dict["monopoly"]:
                        debt = [house_dict["rent"]
                                [house_dict["house_level"]] * 2, house_dict["owner"]]
                    else:
                        debt = [house_dict["rent"]
                                [house_dict["house_level"]], house_dict["owner"]]
                elif house_dict["type"] == "service_property":
                    debt = [
                        sum(dice) * 6 * house_dict["house_level"] - 2, house_dict["owner"]]
                elif house_dict["type"] == "railroad_property":
                    debt = [house_dict["rent"]
                            [house_dict["house_level"]], house_dict["owner"]]
                embed_landing.description += "\n**You must pay {}$ to {}**".format(
                    debt[0], str(self.order[debt[1]][0].user))

        # TODO
        elif house_dict["type"] == "lucky_card0":
            pass

        # TODO
        elif house_dict["type"] == "lucky_card1":
            pass

        # TODO
        elif house_dict["type"] == "tax":
            debt = [house_dict["cost"], None]
            embed_landing.description += "\nYou must pay {} to the bank".format(
                debt[0])

        return {"doubles": doubles, "debt": debt, "buy_property": buy_property, "auction_property": auction_property, "embed": embed_landing, "dice": dice}

    # THERE'S STILL STUFF TO DO IN HERE
    async def routine_checks(self, playing, house) -> None:
        # Show Board
        if self.choice == "board":
            embed_board = discord.Embed(
                color=self.board["spaces"][house]["color_int"], timestamp=datetime.datetime.now())
            embed_board.set_author(
                name="Monopoly Board", icon_url="https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024")

            start = 0
            end = 10
            for x in range(4):
                # Iterate over every space
                for space in self.board["spaces"][start:end]:
                    # Start
                    if space["type"] == "start":
                        embed_board.description = "{emoji} **{name}**".format(
                            emoji=self.emojis["go"], name=space["name"])
                    # Color_Property
                    elif space["type"] == "color_property":
                        try:
                            rent = space["rent"][space["house_level"]]
                            if space["monopoly"] and space["house_level"] == 0:
                                rent *= 2
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)\nOwner: {owner} | Rent: {rent}$".format(
                                emoji=self.emojis[space["color"]], name=space["name"], cost=space["cost"], owner=str(self.order[space["owner"]][0].user), rent=rent)
                            if space["house_level"] != 5:
                                for house in range(space["house_level"]):
                                    embed_board.description += str(
                                        self.emojis["properties"])
                            else:
                                embed_board.description += str(
                                    self.emojis["hotel"])
                        except TypeError:
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                emoji=self.emojis[space["color"]], name=space["name"], cost=space["cost"])
                    # Railroad_Property
                    elif space["type"] == "railroad_property":
                        try:
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)\nOwner:{owner} | Rent: {rent}$".format(
                                emoji=self.emojis["railroad_property"], name=space["name"], cost=space["cost"], owner=str(self.order[space["owner"]].user), rent=space["rent"][space["house_level"]])
                        except TypeError:
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                emoji=self.emojis["railroad_property"], name=space["name"], cost=space["cost"])
                    # Service_Property
                    elif space["type"] == "service_property":
                        if space["name"] == "Eletric Company":
                            try:
                                embed_board.description += "\n{emoji} **{name}** ({cost}$)\nOwner:{owner} | Rent: {rent} * Number on Dice".format(
                                    emoji=self.emojis["electric_company"], name=space["name"], cost=space["cost"], owner=str(self.order[space["owner"]].user), rent=6 * space["house_level"] - 2)
                            except TypeError:
                                embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                    emoji=self.emojis["electric_company"], name=space["name"], cost=space["cost"])
                        else:
                            try:
                                embed_board.description += "\n{emoji} **{name}** ({cost}$)\nOwner:{owner} | Rent: {rent} * Number on Dice".format(
                                    emoji=self.emojis["water_works"], name=space["name"], cost=space["cost"], owner=str(self.order[space["owner"]].user), rent=6 * space["house_level"] - 2)
                            except TypeError:
                                embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                    emoji=self.emojis["water_works"], name=space["name"], cost=space["cost"])
                    # Tax
                    elif space["type"] == "tax":
                        if space["name"] == "Luxury Tax":
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                emoji=self.emojis["luxury_tax"], name=space["name"], cost=space["cost"])
                        else:
                            embed_board.description += "\n{emoji} **{name}** ({cost}$)".format(
                                emoji=self.emojis["pintelho"], name=space["name"], cost=space["cost"])
                    # Chance (luck_card0)
                    elif space["type"] == "luck_card0":
                        embed_board.description += "\n{emoji} **{name}**".format(
                            emoji=self.emojis["luck_card0"], name=space["name"])
                    # Comunity Chets (luck_card1)
                    elif space["type"] == "luck_card1":
                        embed_board.description += "\n{emoji} **{name}**".format(
                            emoji=self.emojis["luck_card1"], name=space["name"])
                    # Jail
                    elif space["type"] == "jail":
                        embed_board.description += "\n{emoji} **{name}**\nJailed: ".format(
                            emoji=self.emojis["brazil"], name=space["name"])
                        for priosner in space["jailed"]:
                            embed_board.description += str(
                                self.order[priosner])
                    # Go to jail
                    elif space["type"] == "jailing":
                        embed_board.description += "\n{emoji} **{name}**".format(
                            emoji=self.emojis["go_to_brazil"], name=space["name"])
                    # Free Parking
                    elif space["type"] == "free_space":
                        embed_board.description += "\n{emoji} **{name}**".format(
                            emoji=self.emojis["parking"], name=space["name"])

                    if space["here"] != None:
                        for player in space["here"]:
                            embed_board.description += "\n{} ({}$)".format(
                                self.order[player][0].user.mention, self.order[player][0].money)

                    embed_board.description += "\n"

                if x == 3:
                    embed_board.set_image(
                        url="https://raw.githubusercontent.com/OrangSquid/Monopoly-Bot/master/emojis/monopoly_board.jpg")
                await self.channel.send(embed=embed_board)
                embed_board = discord.Embed(
                    color=self.board["spaces"][house]["color_int"], timestamp=datetime.datetime.now())
                embed_board.set_author(
                    name="Monopoly Board", icon_url="https://cdn.discordapp.com/avatars/703970013366845470/e87b7deba6b38e852e6295beed200d37.webp?size=1024")
                embed_board.description = ""
                if x == 3:
                    embed_board.set_image(
                        url="https://raw.githubusercontent.com/OrangSquid/Monopoly-Bot/master/emojis/monopoly_board.jpg")
                start += 10
                end += 10

        # TODO
        elif self.choice == "properties":
            embed_properties_dict = {}
            monopolies = []
            color_int_dict = {}
            for property in self.order[self.pointer][0].properties["properties_spaces"]:
                house_dict = self.board["spaces"][property]
                if house_dict["type"] == "color_property":
                    try:
                        embed_properties_dict[house_dict["color"]
                                              ] += self.str_embed_properties(property)
                    # monopolies.append() is in the except block because it only happens once
                    except KeyError:
                        embed_properties_dict[house_dict["color"]
                                              ] = self.str_embed_properties(property)
                        monopolies.append(house_dict["color"])
                        color_int_dict[house_dict["color"]
                                       ] = house_dict["color_int"]
                elif house_dict["type"] == "service_property":
                    try:
                        embed_properties_dict[house_dict["service_property"]
                                              ] += self.str_embed_properties(property)
                    except KeyError:
                        embed_properties_dict["service_property"] = self.str_embed_properties(
                            property)
                        color_int_dict["service_property"] = house_dict["color_int"]
                elif house_dict["type"] == "railroad_property":
                    try:
                        embed_properties_dict["railroad_property"] += self.str_embed_properties(
                            property)
                    except KeyError:
                        embed_properties_dict["railroad_property"] = self.str_embed_properties(
                            property)
                        color_int_dict["railroad_property"] = house_dict["color_int"]

            for property in zip(embed_properties_dict.keys(), embed_properties_dict.values()):
                embed_property = discord.Embed(
                    color=color_int_dict[property[0]], timestamp=datetime.datetime.now(), description=property[1])
                embed_property.set_author(name="{} properties".format(
                    self.order[self.pointer][0].user), icon_url=str(playing.avatar_url))
                await self.channel.send(embed=embed_property)

        # TODO
        elif self.choice == "trade":
            pass

        # TODO
        elif self.choice == "bankruptcy":
            pass

    async def finish_turn(self, house: int, debt: List[int]) -> bool:
        # Pay Debt
        if self.choice == "pay_debt":
            if self.order[self.pointer][0].money < debt[0]:
                await self.channel.send("You don't have enough money to pay this debt!")
                return False
            else:
                self.order[self.pointer][0].money -= debt[0]
                if debt[1] == None:
                    await self.channel.send("{player} payed {debt}$ to the bank!".format(player=self.order[self.pointer][0].user.mention, debt=debt[0]))
                else:
                    self.order[debt[1]][0].money += debt[0]
                    await self.channel.send("{player} payed {debt}$ to {receiver}".format(player=self.order[self.pointer][0].user.mention, debt=debt[0], receiver=self.order[debt[1]][0].user.mention))
                return True

        # Buy Property
        elif self.choice == "buy_property":
            house_dict = self.board["spaces"][house]
            # Color Property
            property_emoji: str = ""
            if house_dict["type"] == "color_property":
                property_emoji = self.emojis[self.board["spaces"]
                                             [house]["color"]]
                color_property_count = 0
                for property in self.order[self.pointer][0].properties["properties_spaces"]:
                    if property in house_dict["color_group"]:
                        color_property_count += 1
                if color_property_count == len(house_dict["color_group"]):
                    await self.channel.send("{player} has made a Monopoly on {emoji} properties".format(player=self.order[self.pointer][0].user.mention, emoji=self.emojis[self.board[house]["color"]]))
                    for space in house_dict["color_group"]:
                        self.board["spaces"][space]["monopoly"] = True
            # Service Property
            elif house_dict["type"] == "service_property":
                if house_dict["name"] == "Electric Company":
                    property_emoji = self.emojis["electric_company"]
                else:
                    property_emoji = self.emojis["water_works"]
                self.board["spaces"][house]["house_level"] = 1
                self.order[self.pointer][0].properties["service_properties"] = 1
                for property in self.order[self.pointer][0].properties["properties_spaces"]:
                    if property in [12, 28]:
                        self.board["spaces"][house]["house_level"] = 2
                        self.order[self.pointer][0].properties["railroad_properties"] = 2
            # Railroad Property
            elif house_dict["type"] == "railroad_property":
                property_emoji = self.emojis["railroad_property"]
                self.board["spaces"][house]["house_level"] = 0
                self.order[self.pointer][0].properties["railroad_properties"] = 1
                for property in self.order[self.pointer][0].properties["properties_spaces"]:
                    if property in [5, 15, 25, 35]:
                        self.board["spaces"][house]["house_level"] += 1
                        self.order[self.pointer][0].properties["railroad_properties"] += 1

            message = "{player} bought {emoji} **{name}** for {cost}$".format(
                player=self.order[self.pointer][0].user.mention, emoji=property_emoji, name=house_dict["name"], cost=house_dict["cost"])
            await self.channel.send(message)
            self.order[self.pointer][0].properties["properties_spaces"].append(
                house)
            self.board["spaces"][house]["owner"] = self.pointer
            self.order[self.pointer][0].money -= house_dict["cost"]
            return True

        # TODO
        elif self.choice == "auction_property":
            pass

        # TODO
        elif self.choice == "nothing":
            return True

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
        for count, player in enumerate(order_copy):
            self.order.append([player[0], 0])
            self.board["spaces"][0]["here"].append(count)

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

        # Main Game loop
        doubles: int = 0
        while len(self.order) >= 1:
            playing: Player = self.order[self.pointer][0]
            house: int = self.order[self.pointer][1]

            embed_turn = discord.Embed.from_dict(self.embeds["turn"])
            # TODO: put this in the add_reactions_embed
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
            self.valid_reactions = ["dice", "board",
                                    "properties", "trade", "bankruptcy"]
            await asyncio.gather(
                self.add_reactions_message(
                    message_turn, ["dice", "board", "properties", "trade", "bankruptcy"]),
                self.bot.wait_for("reaction_add", check=self.check_reaction)
            )
            self.valid_reactions.clear()

            if self.choice == "dice":
                info_end_turn = await self.moving_on_board(
                    playing, house, doubles, True)
                doubles = info_end_turn["doubles"]
                house = self.order[self.pointer][1]

                while not(self.choice in ["pay_debt", "buy_property", "auction_property", "nothing"]):
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

                    self.valid_reactions = copy.copy(reactions)
                    await asyncio.gather(
                        self.add_reactions_message(
                            message_end_turn, reactions),
                        self.bot.wait_for(
                            "reaction_add", check=self.check_reaction)
                    )
                    self.valid_reactions.clear()

                    if self.choice in ["board", "properties", "trade", "bankruptcy"]:
                        await self.routine_checks(playing, house)

                    elif self.choice in reactions:
                        if not await self.finish_turn(house, info_end_turn["debt"]):
                            continue
                else:
                    if doubles != 0 and info_end_turn["dice"][0] == info_end_turn["dice"][1]:
                        continue

            else:
                await self.routine_checks(playing, house)
                continue

            doubles = 0
            self.increment_pointer()
