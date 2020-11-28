import discord
import random
from .Space import Space
from typing import List, Dict, Any, TypeVar

Player = TypeVar('Player')


class LuckSpace(Space):

    def __str__(self) -> str:
        embed_str, players_here_mention = super().__str__()
        return embed_str + players_here_mention
    
    def event(self, playing, embed, card):
        if card['type'] == 'receive_money':
            embed.description += f'\n**You received {card["money"]} from the bank**'
            playing.money += card['money']
            return 'nothing'
        elif card['type'] == 'receive_money_players':
            embed.description += f'\n**You must receive {card["money"]}$ from each player**'
            embed.description += '\n**Once you finish this turn each player will be prompted to pay the debt**'
            return 'nothing'
        elif card['type'].startswith('teleport'):
            embed.description += '**You will be teleported in the once you finish this turn**'
            return 'teleport'
        elif card['type'] == 'jailing':
            embed.description += '**You will be put in jail once you finish this turn**'
            return 'jailing'
        elif card['type'] == 'space_backwards':
            embed.description += '**You will be put in the new space once you finish this turn**'
            return 'teleport'
        elif card['type'] == 'house_repair':
            debt = playing.houses * card['cost']['house'] + playing.hotels * card['cost']['hotel']
            embed.description += f'**You have to pay {debt}$ to the bank**'
            return 'pay_debt'
        elif card['type'] == 'pay_money':
            embed.description += f'**You have to play {card["money"]}$ to the bank**'
            return 'pay_debt'
        elif card['type'] == 'pay_money_players':
            embed.description += f'**You must pay each player {card["money"]}$**'
            return 'pay_debt'


class ChanceSpace(LuckSpace):

    deck: List[Dict[Any, Any]] = list()

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, deck
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        ChanceSpace.deck = random.sample(deck, len(deck))

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += '\nTaking a card from Chance deck.\nIt reads as follows: '
        embed.description += f'\n```{ChanceSpace.deck[0]["text"]}```'
        card = ChanceSpace.deck[0]
        del ChanceSpace.deck[0]
        ChanceSpace.deck.append(card)
        return super().event(playing, embed, card)


class CommunityChestSpace(LuckSpace):

    deck: List[Dict[Any, Any]] = list()

    def __init__(
        self, name: str, color_int: int, emoji: str,
        image_url: str, index: int, deck
    ) -> None:
        super().__init__(name, color_int, emoji, image_url, index)
        CommunityChestSpace.deck = random.sample(deck, len(deck))

    def event(self, playing: Player, embed: discord.Embed):
        embed.description += '\nTaking a card from Community Chest deck.\nIt reads as follows: '
        embed.description += f'\n```{CommunityChestSpace.deck[0]["text"]}```'
        card = CommunityChestSpace.deck[0]
        del CommunityChestSpace.deck[0]
        CommunityChestSpace.deck.append(card)
        return super().event(playing, embed, card)
        
