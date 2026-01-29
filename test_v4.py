"""Quick test V4 vs Original"""
import random, json
from card import Card
from Player_class import Player
from board_setup import generate_color_graph, random_choose_play_area, create_game_board, generate_game_graph
import create_use_resources as res
from game_engine import GameEngine
from player_strategies import SmartTriggerStrategy
from smart_trigger_v4 import SmartTriggerV4

eur_areas = [('brown', 'red'), ('brown', 'purple'), ('brown', 'yellow'), ('brown', 'green'), 
             ('brown', 'orange'), ('purple', 'red'), ('red', 'yellow'), ('yellow', 'blue'), 
             ('yellow', 'green'), ('blue', 'green'), ('orange', 'green')]

europe = [(('red', 'Lisboa'), ('red', 'Madrid'), 13), (('red', 'Madrid'), ('red', 'Bordeaux'), 16),
    (('red', 'Barcelona'), ('red', 'Marseille'), 11), (('red', 'Barcelona'), ('red', 'Madrid'), 14),
    (('red', 'Barcelona'), ('red', 'Bordeaux'), 15), (('red', 'Marseille'), ('red', 'Bordeaux'), 12),
    (('red', 'Bordeaux'), ('red', 'Paris'), 12), (('red', 'Marseille'), ('red', 'Lyon'), 8),
    (('red', 'Bordeaux'), ('red', 'Lyon'), 12), (('purple', 'London'), ('red', 'Paris'), 16),
    (('red', 'Paris'), ('red', 'Lyon'), 11), (('red', 'Paris'), ('purple', 'Rhein-Ruhr'), 10),
    (('red', 'Paris'), ('purple', 'Vlaanderen'), 7), (('purple', 'Randstad'), ('purple', 'London'), 18),
    (('purple', 'Rhein-Ruhr'), ('purple', 'Vlaanderen'), 4), (('purple', 'Vlaanderen'), ('purple', 'London'), 15),
    (('purple', 'London'), ('purple', 'Birmingham'), 4), (('purple', 'Birmingham'), ('purple', 'Glasgow'), 13),
    (('purple', 'Birmingham'), ('purple', 'Dublin'), 15), (('purple', 'Dublin'), ('purple', 'Glasgow'), 17),
    (('purple', 'Randstad'), ('purple', 'Vlaanderen'), 4), (('red', 'Paris'), ('brown', 'Stuttgart'), 14),
    (('purple', 'Randstad'), ('brown', 'Bremen'), 8), (('purple', 'Vlaanderen'), ('brown', 'Bremen'), 10),
    (('purple', 'Vlaanderen'), ('brown', 'Rhein-Main'), 6), (('purple', 'Rhein-Ruhr'), ('brown', 'Rhein-Main'), 3),
    (('purple', 'Rhein-Ruhr'), ('brown', 'Stuttgart'), 5), (('brown', 'Rhein-Main'), ('brown', 'Stuttgart'), 3),
    (('brown', 'Rhein-Main'), ('brown', 'Berlin'), 10), (('brown', 'Rhein-Main'), ('brown', 'Praha'), 10),
    (('brown', 'Rhein-Main'), ('brown', 'Munchen'), 6), (('brown', 'Stuttgart'), ('brown', 'Munchen'), 4),
    (('brown', 'Berlin'), ('brown', 'Bremen'), 6), (('brown', 'Praha'), ('brown', 'Munchen'), 8),
    (('brown', 'Praha'), ('brown', 'Katowice'), 8), (('brown', 'Praha'), ('brown', 'Berlin'), 7),
    (('blue', 'Beograd'), ('blue', 'Tirane'), 15), (('blue', 'Beograd'), ('blue', 'Sofia'), 11),
    (('blue', 'Sofia'), ('blue', 'Tirane'), 13), (('blue', 'Sofia'), ('blue', 'Istanbul'), 13),
    (('blue', 'Sofia'), ('blue', 'Athina'), 17), (('blue', 'Tirane'), ('blue', 'Athina'), 16),
    (('blue', 'Istanbul'), ('blue', 'Izmir'), 8), (('blue', 'Istanbul'), ('blue', 'Ankara'), 9),
    (('blue', 'Izmir'), ('blue', 'Ankara'), 10), (('blue', 'Beograd'), ('green', 'Bucuresti'), 12),
    (('blue', 'Sofia'), ('green', 'Bucuresti'), 9), (('blue', 'Istanbul'), ('green', 'Bucuresti'), 13),
    (('blue', 'Beograd'), ('yellow', 'Budapest'), 10), (('green', 'Warszawa'), ('brown', 'Katowice'), 5),
    (('green', 'Warszawa'), ('brown', 'Praha'), 11), (('green', 'Warszawa'), ('brown', 'Berlin'), 11),
    (('green', 'Kyjiv'), ('green', 'Warszawa'), 14), (('green', 'Kyjiv'), ('green', 'Minsk'), 10),
    (('green', 'Kyjiv'), ('green', 'Kharkiv'), 9), (('green', 'Kyjiv'), ('green', 'Odessa'), 9),
    (('green', 'Kharkiv'), ('green', 'Odessa'), 13), (('green', 'Kharkiv'), ('green', 'Moskwa'), 15),
    (('green', 'Warszawa'), ('green', 'Minsk'), 10), (('yellow', 'Zagreb'), ('blue', 'Beograd'), 9),
    (('yellow', 'Milano'), ('brown', 'Munchen'), 16), (('yellow', 'Zurich'), ('brown', 'Stuttgart'), 5),
    (('yellow', 'Zurich'), ('brown', 'Munchen'), 8), (('yellow', 'Milano'), ('red', 'Marseille'), 13),
    (('yellow', 'Milano'), ('red', 'Lyon'), 11), (('yellow', 'Zurich'), ('red', 'Lyon'), 14),
    (('yellow', 'Zurich'), ('red', 'Paris'), 14), (('yellow', 'Milano'), ('yellow', 'Zurich'), 11),
    (('yellow', 'Milano'), ('yellow', 'Roma'), 19), (('yellow', 'Milano'), ('yellow', 'Zagreb'), 17),
    (('yellow', 'Napoli'), ('yellow', 'Roma'), 7), (('yellow', 'Zagreb'), ('yellow', 'Wien'), 8),
    (('yellow', 'Zagreb'), ('yellow', 'Budapest'), 7), (('yellow', 'Budapest'), ('brown', 'Katowice'), 11),
    (('yellow', 'Budapest'), ('green', 'Bucuresti'), 16), (('yellow', 'Budapest'), ('yellow', 'Wien'), 5),
    (('brown', 'Berlin'), ('brown', 'Praha'), 7), (('brown', 'Bremen'), ('brown', 'Berlin'), 6),
    (('brown', 'Praha'), ('yellow', 'Wien'), 7), (('green', 'Bucuresti'), ('yellow', 'Budapest'), 16),
    (('green', 'Bucuresti'), ('green', 'Odessa'), 10), (('green', 'Moskwa'), ('orange', 'Sankt-Peterburg'), 14),
    (('green', 'Moskwa'), ('green', 'Minsk'), 14), (('orange', 'Riga'), ('orange', 'Sankt-Peterburg'), 13),
    (('orange', 'Riga'), ('orange', 'Tallinn'), 7), (('orange', 'Riga'), ('green', 'Moskwa'), 18),
    (('orange', 'Kobenhavn'), ('brown', 'Bremen'), 12), (('orange', 'Kobenhavn'), ('brown', 'Berlin'), 15),
    (('orange', 'Riga'), ('green', 'Warszawa'), 12), (('orange', 'Riga'), ('green', 'Minsk'), 8),
    (('orange', 'Kobenhavn'), ('orange', 'Stockholm'), 18), (('orange', 'Kobenhavn'), ('orange', 'Oslo'), 17),
    (('orange', 'Stockholm'), ('orange', 'Oslo'), 13), (('orange', 'Stockholm'), ('orange', 'Helsinki'), 21),
    (('orange', 'Sankt-Peterburg'), ('orange', 'Tallinn'), 9), (('orange', 'Sankt-Peterburg'), ('orange', 'Helsinki'), 11),
    (('yellow', 'Wien'), ('brown', 'Munchen'), 9), (('green', 'Minsk'), ('green', 'Kharkiv'), 16),
    (('brown', 'Praha'), ('brown', 'Munchen'), 8)]

def setup_game(num_players=4, random_seed=None):
    if random_seed:
        random.seed(random_seed)
    color_graph = generate_color_graph(eur_areas)
    play_areas = random_choose_play_area(num_players, color_graph)
    game_board = create_game_board(europe, play_areas)
    board_graph = generate_game_graph(game_board)
    players = [Player(f'Player_{i}') for i in range(num_players)]
    player_order = list(range(num_players))
    random.shuffle(player_order)
    with open('config.json', 'r') as f:
        config = json.load(f)
    cards = [Card(c) for c in config.get('cards')]
    dark_cards = [c for c in cards if c.type == 'dark']
    light_cards = [c for c in cards if c.type == 'light']
    random.shuffle(dark_cards)
    random.shuffle(light_cards)
    if num_players == 4:
        dark_cards = dark_cards[:-1]
        light_cards = light_cards[:-3]
    first_nine = dark_cards[:9]
    rest_dark = dark_cards[9:]
    remaining_deck = rest_dark + light_cards
    random.shuffle(remaining_deck)
    step3_card = Card(config.get('stage_three_card'))
    remaining_deck.append(step3_card)
    first_nine.sort(key=lambda c: c.cost)
    current_market = first_nine[:4]
    future_market = first_nine[4:9]
    coal_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
               [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    gas_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
              [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    oil_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
              [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    uranium_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
                  [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    coal = res.Resource(27, (2, 9), coal_cl, 'coal')
    coal.initialize_supply()
    gas = res.Resource(24, (3, 8), gas_cl, 'gas')
    gas.initialize_supply()
    oil = res.Resource(20, (3, 9), oil_cl, 'oil')
    oil.initialize_supply()
    uranium = res.Resource(12, (8, 9), uranium_cl, 'uranium')
    uranium.initialize_supply()
    resources = {'coal': coal, 'gas': gas, 'oil': oil, 'uranium': uranium}
    return players, current_market, future_market, remaining_deck, board_graph, resources, player_order

def run_single_game(num_players, strategies, strategy_names):
    random_seed = random.randint(1, 10000)
    players, current_market, future_market, deck, board_graph, resources, player_order = setup_game(num_players=num_players, random_seed=random_seed)
    for i, (player, strategy) in enumerate(zip(players, strategies)):
        player.strategy = strategy
        player.name = f'P{i}_{strategy_names[i]}'
    engine = GameEngine(players=players, current_market=current_market, future_market=future_market, deck=deck,
        board_graph=board_graph, resources=resources, player_order=player_order, num_players=num_players,
        enable_logging=False, game_id=None, log_file="test_log.json")
    winner = engine.run_game(verbose=False, max_rounds=35)
    return winner

def test():
    num_games = 500
    print(f"Testing SmartTriggerV4 vs Original ({num_games} games)")
    stats = {'V4': 0, 'Original': 0}
    for game_num in range(1, num_games + 1):
        if game_num % 100 == 0:
            print(f"Game {game_num}...")
        strategies = [SmartTriggerV4(), SmartTriggerV4(), SmartTriggerStrategy(), SmartTriggerStrategy()]
        strategy_names = ['V4', 'V4', 'Original', 'Original']
        indices = list(range(4))
        random.shuffle(indices)
        strategies = [strategies[i] for i in indices]
        strategy_names = [strategy_names[i] for i in indices]
        winner = run_single_game(4, strategies, strategy_names)
        winner_type = 'V4' if 'V4' in strategy_names[winner] else 'Original'
        stats[winner_type] += 1
    print(f"\nResults:")
    print(f"V4: {stats['V4']} wins ({stats['V4']/5:.1f}%)")
    print(f"Original: {stats['Original']} wins ({stats['Original']/5:.1f}%)")
    v4_rate = stats['V4'] / 5
    orig_rate = stats['Original'] / 5
    if v4_rate > orig_rate:
        print(f"✓ V4 wins by {v4_rate - orig_rate:.1f} points!")
    elif orig_rate > v4_rate:
        print(f"✗ Original wins by {orig_rate - v4_rate:.1f} points")
    else:
        print("= Tie")

if __name__ == '__main__':
    test()
