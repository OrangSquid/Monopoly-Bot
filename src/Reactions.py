import discord
from typing import Dict, Tuple, List

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
    'use_prison_pass': '\n🎫 - Use the prison free pass',
    'fine_prison_break': '\n♿ - Pay fine and leave jail',
    'double_prison_break': '\n🛂 - Leave Jail',
    'teleport': '\n↘ - Go to specified place',
    'space_backwards': '\n⏪ - Go back 3 spaces',
    'jailing': '\n<:brazil:780207221900050445> - Go to Brazil'
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
    '🎫': 'use_prison_pass',
    '♿': 'fine_prison_break',
    '🛂': 'double_prison_break',
    '↘': 'teleport',
    '⏪': 'space_backwards',
    '<:brazil:780207221900050445>': 'jailing'
}

STR_REACTION: Dict[str, str] = dict()

for key, value in EMOJI_REACTIONS.items():
    STR_REACTION[value] = key


def add_reactions_embed(embed: discord.Embed, reactions) -> discord.Embed:
    for reaction in reactions:
        embed.description += STR_EMBED_ACTION[reaction]
    return embed


async def add_reactions_message(message, reactions):
    for reaction in reactions:
        await message.add_reaction(STR_REACTION[reaction])