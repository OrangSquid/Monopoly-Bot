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
    'prison_break': '\n♿ - Pay fine and leave jail'
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
    '♿': 'prison_break'
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


def add_reactions_list(info) -> Tuple[str]:
    reactions = ['board', 'properties', 'trade', 'bankruptcy']

    if info['debt'][0] != 0:
        reactions.append('pay_debt')
    if info['buy_property']:
        reactions.append('buy_property')
    if info['auction_property']:
        reactions.append('auction_property')
    if reactions == ['board', 'properties', 'trade', 'bankruptcy']:
        reactions.append('nothing')

    return reactions
