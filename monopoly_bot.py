import datetime
import logging
from typing import Dict, List

import discord
from discord.ext import commands

from src import MonopolyCore, Player
from src.Board import Board

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
# Global variables to keep track of games and who's WAITING
WAITING: Dict[discord.Guild, List[discord.User]] = {}
PLAYING: Dict[discord.Guild, MonopolyCore.Monopoly] = {}
BOARDS: List[str] = ['json/boards/board_DEBUG.json']
monopoly_bot = commands.AutoShardedBot(command_prefix=prefix)


def look_for_player(caller: discord.User) -> bool:
    for lobby, game in zip(WAITING.values(), PLAYING.values()):
        if caller in game.order or caller in lobby:
            return True
    return False


def prepare_game(
    board_file: str, players: List[discord.User],
    channel: discord.TextChannel
) -> MonopolyCore.Monopoly:
    players_class = []
    for player in players:
        players_class.append(Player.Player(player))
    board = Board.Board(board_file)
    return MonopolyCore.Monopoly(monopoly_bot, channel, players_class, board)


@monopoly_bot.command(help="Lets you create a new lobby for a Monopoly game")
@commands.guild_only()
async def play(ctx):
    # Checks if there's already a game WAITING to start
    # If not, make a new one
    # Else if it is the first issuer of the command, start the game,
    # Else join the game

    # Check if there's a game waiting
    try:
        WAITING[ctx.guild]
    except KeyError:
        # Check if there's a game in course
        try:
            PLAYING[ctx.guild]
        # Join the game
        except KeyError:
            if look_for_player(ctx.author):
                await ctx.send(":x: You are already in a game in this or in another server!")
            else:
                WAITING[ctx.guild] = [ctx.author]
                embed_to_send = discord.Embed(title="Game WAITING",
                                              description="If you want to join the game, use =play."
                                                          "\nOnce you want to start, {} should use =play."
                                                          "\nUp to four players can join.".format(ctx.author),
                                              timestamp=datetime.datetime.now())
                embed_to_send.set_author(name="{.author} wants to start a game!".format(ctx),
                                         icon_url=str(ctx.author.avatar_url))
                embed_to_send.set_footer(
                    text="Monopoly Game at \"{.guild}\"".format(ctx))
                await ctx.send(embed=embed_to_send)
        else:
            await ctx.send("There's a game in course in this server!")
    # Make a game or join it
    else:
        if ctx.author == WAITING[ctx.guild][0]:
            if len(WAITING[ctx.guild]) == 1:
                await ctx.send(":grey_exclamation: There aren't enough players to start. You need at least 2.")
            else:
                game = prepare_game(BOARDS[0], WAITING[ctx.guild], ctx.channel)
                PLAYING[ctx.guild] = game
                WAITING.pop(ctx.guild)
                try:
                    await game.play()
                except Exception as e:
                    await ctx.send(":x: AN ERROR HAS OCCURRED!")
                    raise e
                finally:
                    PLAYING.pop(ctx.guild)
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
    print("We are ready to roll!")


def main():
    with open("Token.txt", "r") as token:
        monopoly_bot.run(token.read())


if __name__ == "__main__":
    main()
