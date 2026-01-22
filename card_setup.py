import random
import json
from card import Card


number_of_players = 4
with open('config.json', 'r') as f:
    config = json.load(f)

def market_setup(number_of_players):

    """returns 2 lists, the first 9 dark cards for the starting marketplace and the rest of the deck ready for play"""
    
    # turn each card into a card object
    cards = [Card(c) for c in config.get('cards')]
    
    dark_cards = []
    light_cards = []

    for c in cards:
        if c.type == 'dark':
            dark_cards.append(c)
        else:
            light_cards.append(c)

    random.shuffle(dark_cards)
    random.shuffle(light_cards)

    if number_of_players == 3:
        dark_cards = dark_cards[:-2]
        light_cards = light_cards[:-6]

    elif number_of_players == 4:
        dark_cards = dark_cards[:-1]
        light_cards = light_cards[:-3]


    first_nine_cards = dark_cards[:9]
    rest_of_dark_cards = dark_cards[9:]

    remaining_deck = rest_of_dark_cards + light_cards
    random.shuffle(remaining_deck)
    
    # Insert the stage 3 card
    remaining_deck.append(Card(config.get('stage_three_card')))

    return first_nine_cards, remaining_deck

#*****************************************************************



first_nine, rest = market_setup(number_of_players)

# check that there are actually 9 cards in the first nine cards
assert len(first_nine) == 9

# check that all of the cards in the first 9 are actually dark cards
for c in first_nine:
    assert c.type == 'dark'

# check that the last card in the remaining is the phase 3 card
assert rest[-1].resource == 'stage three'

print('All tests passed')










