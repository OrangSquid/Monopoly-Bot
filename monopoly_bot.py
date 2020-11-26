import datetime
import logging
from typing import Dict, List

import discord
from discord.ext import commands

from src import MonopolyCore, Player, Board

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
# WAITING: Dict[discord.Guild, List[discord.User]] = {}
lobbies: Dict[discord.Guild, MonopolyCore.Monopoly] = {}
BOARDS: List[str] = ['boards/board_DEBUG.json']
monopoly_bot = commands.AutoShardedBot(command_prefix=prefix)


def look_for_player(caller: discord.User) -> bool:
    for game in lobbies.values():
        if caller in game.order:
            return True


def prepare_game(
    board_file: str, player: discord.User,
    channel: discord.Channel
) -> MonopolyCore.Monopoly:
    players_class = [Player.Player(player)]
    board = Board.Board(board_file)
    return MonopolyCore.Monopoly(monopoly_bot, channel, players_class, board)


@monopoly_bot.command(help="Lets you create a new lobby for a Monopoly game")
@commands.guild_only()
async def play(ctx):
    """
    Checks if there's already a game WAITING to start
    If not, make a new one
    Else if it is the first issuer of the command, start the game,
    Else join the game
    """

    if look_for_player(ctx.author):
        await ctx.send(":x: You are already in a game in this or in another server!")
    elif lobbies[ctx.guild] is not None:
        if ctx.author == lobbies[ctx.guild].order[0]:
            if len(WAITING[ctx.guild]) == 1:
                await ctx.send(":grey_exclamation: There aren't enough players to start. You need at least 2.")
            else:
                game = lobbies[ctx.guild]
                await game.play()
                lobbies[ctx.guild] = None
        else:
            if len(WAITING[ctx.guild]) != 4:
                WAITING[ctx.guild].append(ctx.author)
                await ctx.send(
                    ":white_check_mark: {} has joined the game ({}/4)".format(ctx.author.mention,
                                                                              len(WAITING[ctx.guild])))
            else:
                await ctx.send(":x: The game is already full")
    else:
        lobbies[ctx.guild] = prepare_game(BOARDS[0], ctx.author, ctx.channel)
        embed_to_send = discord.Embed(
            title="MONOPOLY GAME",
            description=f"If you want to join the game, use =play."
                        "\nOnce you want to start, {ctx.author} should use =play."
                        "\nUp to four players can join.",
            timestamp=datetime.datetime.now()
        )
        embed_to_send.set_author(
            name=f"{ctx.author} wants to start a game!",
            icon_url=str(ctx.author.avatar_url)
        )
        embed_to_send.set_footer(
            text=f"Monopoly Game at \"{ctx.guild}\""
        )
        await ctx.send(embed=embed_to_send)

    try:
        if ctx.author == WAITING[ctx.guild][0]:
            if len(WAITING[ctx.guild]) == 1:
                await ctx.send(":grey_exclamation: There aren't enough players to start. You need at least 2.")
            else:
                game = prepare_game(BOARDS[0], WAITING[ctx.guild], ctx.channel)
                lobbies[ctx.guild] = game
                WAITING.pop(ctx.guild)
                await game.play()
                lobbies.pop(ctx.guild)
        elif ctx.author in WAITING[ctx.guild]:
            await ctx.send(":x: You are already WAITING for the game! The first caller of the play command should be the one to start.")
        elif look_for_player(ctx.author):
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
        # Check if there's a game in course
        try:
            lobbies[ctx.guild]
        # Join the game
        except KeyError:
            if await look_for_player(ctx.author):
                await ctx.send(":x: You are already in a game in this or in another server!")
            else:
                lobbies[ctx.guild] = prepare_game(BOARDS[0], ctx.author, ctx.channel)
                embed_to_send = discord.Embed(
                    title="MONOPOLY GAME",
                    description=f"If you want to join the game, use =play."
                                "\nOnce you want to start, {ctx.author} should use =play."
                                "\nUp to four players can join.",
                    timestamp=datetime.datetime.now()
                )
                embed_to_send.set_author(
                    name=f"{ctx.author} wants to start a game!",
                    icon_url=str(ctx.author.avatar_url)
                )
                embed_to_send.set_footer(
                    text=f"Monopoly Game at \"{ctx.guild}\""
                )
                await ctx.send(embed=embed_to_send)
        else:
            print("There's a game in course in this server!")


@monopoly_bot.command(help="Lets you leave the lobby you're in")
@commands.guild_only()
async def leave(ctx):
    try:
        if WAITING[ctx.guild] == 1:
            await ctx.send(f":x: Use {await prefix(monopoly_bot, ctx)}stop to leave")
        else:
            WAITING[ctx.guild].remove(ctx.author)
            await ctx.send(
                f":white_check_mark: {ctx.author.mention} "
                f"has been removed from the game ({len(WAITING[ctx.guild])})/4)"
            )
    except KeyError:
        await ctx.send(":x: You are not WAITING for any game!")


@monopoly_bot.command(help="Lets you stop the lobby or the game you're lobbies")
@commands.guild_only()
async def stop(ctx):
    try:
        WAITING.pop(ctx.guild)
        await ctx.send(":grey_exclamation: Your game has been cancelled")
    except KeyError:
        await ctx.send(":x: There's no game to stop")


@monopoly_bot.event
async def on_ready():
    '''with open("board.json", "r") as file:
        global BOARD
        BOARD = json.load(file)
    with open("embeds.json", "r", encoding="utf_8") as file:
        global EMBEDS
        EMBEDS = json.load(file)'''
    for guild in monopoly_bot.guilds:
        lobbies[guild] = None
    print(lobbies)
    print("We are ready to roll!")


def main():
    with open("Token.txt", "r") as token:
        monopoly_bot.run(token.read())


if __name__ == "__main__":
    main()
