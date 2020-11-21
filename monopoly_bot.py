import logging
import monopoly_core
import discord
import datetime
import json
from discord.ext import commands
from typing import Dict, List, Any

# Setting up the logger function for the library
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '[%(asctime)s]: %(levelname)s: %(name)s: %(message)s'))
logger.addHandler(handler)


async def prefix(bot, message) -> str:
    return "="


# Global variables to keep track of games and who's WAITING
WAITING: Dict[discord.Guild, List[discord.User]] = {}
PLAYING: Dict[discord.Guild, monopoly_core.Monopoly] = {}
# Keep track of definitions and card info like the emojis and images
# DEFINITIONS: Dict[Any, Any] = {}
BOARD: Dict[str, Any] = {}
EMOJIS: Dict[str, Any] = {}
EMBEDS: Dict[str, Dict[str, str]] = {}
monopoly_bot = commands.Bot(command_prefix=prefix)


async def look_for_player(caller: discord.User) -> bool:
    # Looks if the caller of either join or play_monopoly is already in a game to avoid confusion in DMs with the bot
    for game in PLAYING.values():
        for player in game.order:
            if player.user == caller:
                return True
    for lobby in WAITING.values():
        for player in lobby:
            if player == caller:
                return True
    else:
        return False


@monopoly_bot.command(help="Lets you create a new lobby for a Monopoly game")
@commands.guild_only()
async def play(ctx):
    # Checks if there's already a game WAITING to start
    # If not, make a new one
    try:
        print(WAITING[ctx.guild])
    except KeyError:
        try:
            print(PLAYING[ctx.guild])
        except KeyError:
            if await look_for_player(ctx.author):
                await ctx.send(":x: You are already in a game in this or in another server!")
            else:
                WAITING[ctx.guild] = [ctx.author]
                embed_to_send = discord.Embed(title="Game WAITING",
                                              description="If you want to join the game, use =join."
                                                          "\nOnce you want to start, use =start."
                                                          "\nUp to four players can join.",
                                              timestamp=datetime.datetime.now())
                embed_to_send.set_author(name="{.author} wants to start a game!".format(ctx),
                                         icon_url=str(ctx.author.avatar_url))
                embed_to_send.set_footer(
                    text="Monopoly Game at \"{.guild}\"".format(ctx))
                await ctx.send(embed=embed_to_send)
    else:
        await ctx.send(":x: There's already a game WAITING to start or one is already on course")


@monopoly_bot.command(help="Lets you join the current Monopoly lobby in your server")
@commands.guild_only()
async def join(ctx):
    try:
        if ctx.author in WAITING[ctx.guild]:
            await ctx.send(":x: You are already WAITING for the game")
        elif await look_for_player(ctx.author):
            await ctx.send(":x: You are already in a game in this or in another server!")
        else:
            if len(WAITING[ctx.guild]) != 4:
                WAITING[ctx.guild].append(ctx.author)
                await ctx.send(
                    ":white_check_mark: {} has joined the game ({}/4)".format(ctx.author.mention,
                                                                              len(WAITING[ctx.guild])))
            else:
                await ctx.send(":x: The game is already full")
    except KeyError:
        await ctx.send(":x: There are no current games WAITING to start")


@monopoly_bot.command(help="If there's a lobby with enough people in it, then this command will start the game")
@commands.guild_only()
async def start(ctx):
    try:
        if len(WAITING[ctx.guild]) == 1:
            await ctx.send(":grey_exclamation: There aren't enough players to start. You need at least 2.")
        else:
            players = []
            for player in WAITING[ctx.guild]:
                players.append(monopoly_core.Player(player))
            game = monopoly_core.Monopoly(
                players, monopoly_bot, ctx.channel, BOARD, EMOJIS)
            PLAYING[ctx.guild] = game
            WAITING.pop(ctx.guild)
            await game.play()
            PLAYING.pop(ctx.guild)
    except KeyError:
        await ctx.send(":x: There's no game to start!")


@monopoly_bot.command(help="Lets you leave the lobby you're in")
@commands.guild_only()
async def leave(ctx):
    if WAITING[ctx.guild] == 1:
        await ctx.send(":x: Use {}stop to leave".format("="))
    try:
        WAITING[ctx.guild].remove(ctx.author)
        await ctx.send(":white_check_mark: {.author.mention} "
                       "has been removed from the game ({}/4)".format(ctx, len(WAITING[ctx.guild])))
    except KeyError:
        await ctx.send(":x: You are not WAITING for any game!")


@monopoly_bot.command(help="Lets you stop the lobby or the game you're PLAYING")
@commands.guild_only()
async def stop(ctx):
    try:
        WAITING.pop(ctx.guild)
        await ctx.send(":grey_exclamation: Your game has been cancelled")
    except KeyError:
        try:
            await ctx.send("The game will stop after next player's turn")
            PLAYING[ctx.guild].stop = True
        except KeyError:
            await ctx.send(":x: There are no games to stop")


@monopoly_bot.group()
async def settings(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(":x: Choose a setting! Please use =help to get a full list of settings")


# async def change_settings(setting: str, to_change, guild_id: int):
#    definitions[str(guild_id)][setting] = to_change
#    with open("definitions.json", "w") as file:
#        json.dump(definitions, file, indent="\t")


@monopoly_bot.event
async def on_ready():
    #global definitions
    # Loading the definitions file and filling in any guild missing
    # with open("definitions.json", "r") as file:
    #    definitions = json.load(file)
    #    for guild in monopoly_bot.guilds:
    #        try:
    #            print(definitions[str(guild.id)])
    #        except KeyError:
    #            definitions[guild.id] = definitions["default"]
    # with open("definitions.json", "w") as file:
    #    json.dump(definitions, file, indent="\t")
    with open("board.json", "r") as file:
        global BOARD
        BOARD = json.load(file)
    with open("embeds.json", "r") as file:
        global EMBEDS
        EMBEDS = json.load(file)
    for emoji in monopoly_bot.emojis:
        EMOJIS[emoji.name] = str(emoji)
    print("We are ready to roll!")


@monopoly_bot.event
async def on_guild_join(guild):
    #definitions[guild.id] = definitions["default"]
    #with open("definitions.json.json", "w") as file:
    #   json.dump(definitions, file, indent="\t")
    pass


def main():
    with open("Token.txt", "r") as token:
        monopoly_bot.run(token.read())


if __name__ == "__main__":
    main()
