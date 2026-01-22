"""
Main game runner for Power Grid simulation
"""

import random
import json
from card import Card
from Player_class import Player
from board_setup import (
    generate_color_graph, random_choose_play_area, create_game_board,
    generate_game_graph, create_city_nodes, starting_player_order, market_setup
)
from card_setup import market_setup as card_market_setup
import create_use_resources as res
from game_engine import GameEngine
from player_strategies import RandomStrategy, GreedyStrategy, ConservativeStrategy, BalancedStrategy, MyStrategy

# Europe color connections
eur_areas = [('brown', 'red'), ('brown', 'purple'), ('brown', 'yellow'), ('brown', 'green'), 
             ('brown', 'orange'), ('purple', 'red'), ('red', 'yellow'), ('yellow', 'blue'), 
             ('yellow', 'green'), ('blue', 'green'), ('orange', 'green')]

# Europe city connections (from board_setup.py)
europe = [
    (('red', 'Lisboa'), ('red', 'Madrid'), 13), (('red', 'Madrid'), ('red', 'Bordeaux'), 16),
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
    (('green', 'Warszawa'), ('green', 'Minsk'), 10), (('orange', 'Kobenhavn'), ('brown', 'Bremen'), 12),
    (('orange', 'Kobenhavn'), ('brown', 'Berlin'), 15), (('orange', 'Riga'), ('green', 'Warszawa'), 12),
    (('orange', 'Riga'), ('green', 'Minsk'), 8), (('orange', 'Riga'), ('green', 'Moskwa'), 18),
    (('orange', 'Kobenhavn'), ('orange', 'Stockholm'), 18), (('orange', 'Kobenhavn'), ('orange', 'Oslo'), 17),
    (('orange', 'Stockholm'), ('orange', 'Oslo'), 13), (('orange', 'Stockholm'), ('orange', 'Helsinki'), 21),
    (('orange', 'Sankt-Peterburg'), ('orange', 'Tallinn'), 9), (('orange', 'Sankt-Peterburg'), ('orange', 'Helsinki'), 11),
    (('yellow', 'Zagreb'), ('blue', 'Beograd'), 9), (('yellow', 'Milano'), ('brown', 'Munchen'), 16),
    (('yellow', 'Zurich'), ('brown', 'Stuttgart'), 5), (('yellow', 'Zurich'), ('brown', 'Munchen'), 8),
    (('yellow', 'Milano'), ('red', 'Marseille'), 13), (('yellow', 'Milano'), ('red', 'Lyon'), 11),
    (('yellow', 'Zurich'), ('red', 'Lyon'), 14), (('yellow', 'Zurich'), ('red', 'Paris'), 14),
    (('yellow', 'Milano'), ('yellow', 'Zurich'), 11), (('yellow', 'Milano'), ('yellow', 'Roma'), 19),
    (('yellow', 'Milano'), ('yellow', 'Zagreb'), 17), (('yellow', 'Napoli'), ('yellow', 'Roma'), 7),
    (('yellow', 'Zagreb'), ('yellow', 'Wien'), 8), (('yellow', 'Zagreb'), ('yellow', 'Budapest'), 7),
    (('yellow', 'Budapest'), ('brown', 'Katowice'), 11), (('yellow', 'Budapest'), ('green', 'Bucuresti'), 16),
    (('yellow', 'Budapest'), ('yellow', 'Wien'), 5), (('brown', 'Berlin'), ('brown', 'Praha'), 7),
    (('brown', 'Bremen'), ('brown', 'Berlin'), 6), (('brown', 'Katowice'), ('brown', 'Praha'), 8),
    (('brown', 'Praha'), ('yellow', 'Wien'), 7), (('green', 'Bucuresti'), ('yellow', 'Budapest'), 16),
    (('green', 'Bucuresti'), ('green', 'Odessa'), 10), (('green', 'Moskwa'), ('orange', 'Sankt-Peterburg'), 14),
    (('green', 'Moskwa'), ('green', 'Minsk'), 14), (('orange', 'Riga'), ('orange', 'Sankt-Peterburg'), 13),
    (('orange', 'Riga'), ('orange', 'Tallinn'), 7), (('yellow', 'Wien'), ('brown', 'Munchen'), 9),
    (('green', 'Minsk'), ('green', 'Kharkiv'), 16), (('brown', 'Praha'), ('brown', 'Munchen'), 8)
]


def setup_game(num_players=4, random_seed=None):
    """Set up a new game"""
    if random_seed:
        random.seed(random_seed)
    
    # Generate board
    color_graph = generate_color_graph(eur_areas)
    play_areas = random_choose_play_area(num_players, color_graph)
    game_board = create_game_board(europe, play_areas)
    board_graph = generate_game_graph(game_board)
    
    # Create players
    players = []
    for i in range(num_players):
        players.append(Player(f'Player_{i}'))
    
    # Initial player order
    player_order = list(range(num_players))
    random.shuffle(player_order)
    
    # Setup card market (using card_setup logic)
    with open('config.json', 'r') as f:
        config = json.load(f)
    cards = [Card(c) for c in config.get('cards')]
    
    dark_cards = [c for c in cards if c.type == 'dark']
    light_cards = [c for c in cards if c.type == 'light']
    
    random.shuffle(dark_cards)
    random.shuffle(light_cards)
    
    # Remove cards based on player count
    if num_players == 3:
        dark_cards = dark_cards[:-2]
        light_cards = light_cards[:-6]
    elif num_players == 4:
        dark_cards = dark_cards[:-1]
        light_cards = light_cards[:-3]
    
    # First 9 dark cards for market
    first_nine = dark_cards[:9]
    rest_dark = dark_cards[9:]
    
    # Remaining deck
    remaining_deck = rest_dark + light_cards
    random.shuffle(remaining_deck)
    
    # Insert Step 3 card (at end Europe rule)
    step3_card = Card(config.get('stage_three_card'))
    remaining_deck.append(step3_card)
    
    # Separate market: 4 current (cheapest) + 5 future
    first_nine.sort(key=lambda c: c.cost)
    current_market = first_nine[:4]
    future_market = first_nine[4:9]
    
    # Setup resources
    total_supply_coal = 27
    start_supply_coal = (2, 9)
    total_supply_gas = 24
    start_supply_gas = (3, 8)
    total_supply_oil = 20
    start_supply_oil = (3, 9)
    total_supply_uranium = 12
    start_supply_uranium = (8, 9)
    
    coal_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
               [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    gas_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
              [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    oil_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
              [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    uranium_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], 
                  [5, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
    
    coal = res.Resource(total_supply_coal, start_supply_coal, coal_cl, 'coal')
    coal.initialize_supply()
    gas = res.Resource(total_supply_gas, start_supply_gas, gas_cl, 'gas')
    gas.initialize_supply()
    oil = res.Resource(total_supply_oil, start_supply_oil, oil_cl, 'oil')
    oil.initialize_supply()
    uranium = res.Resource(total_supply_uranium, start_supply_uranium, uranium_cl, 'uranium')
    uranium.initialize_supply()
    
    resources = {
        'coal': coal,
        'gas': gas,
        'oil': oil,
        'uranium': uranium
    }
    
    return players, current_market, future_market, remaining_deck, board_graph, resources, player_order


def run_single_game(num_players, strategies, strategy_names, verbose=True, enable_logging=False):
    """Run a single game and return winner and final stats"""
    random_seed = random.randint(1, 10000)
    
    # Setup game
    players, current_market, future_market, deck, board_graph, resources, player_order = setup_game(
        num_players=num_players, random_seed=random_seed
    )

    # Assign strategies to players
    for i, (player, strategy) in enumerate(zip(players, strategies)):
        player.strategy = strategy
        player.name = f'Player_{i} ({strategy_names[i]})'

    # Create game engine
    engine = GameEngine(
        players=players,
        current_market=current_market,
        future_market=future_market,
        deck=deck,
        board_graph=board_graph,
        resources=resources,
        player_order=player_order,
        num_players=num_players,
        enable_logging=enable_logging,
        game_id=None,
        log_file="power_grid_game_log.json"
    )

    # Run game
    winner = engine.run_game(verbose=verbose)

    # Get final stats for all players
    final_stats = []
    for player_idx, player in enumerate(engine.players):
        cities_powered = engine.calculate_cities_powered(player)
        cities_connected = len(player.generators)
        money = player.money
        final_stats.append({
            'winner': (player_idx == winner),
            'cities_powered': cities_powered,
            'cities_connected': cities_connected,
            'money': money
        })

    return winner, final_stats


def main():
    """Run games with 4 test players - single game or tournament mode"""
    import sys
    
    # Check if tournament mode requested
    num_games = 1
    if len(sys.argv) > 1:
        try:
            num_games = int(sys.argv[1])
            if num_games < 1 or num_games > 500:
                print("Error: Number of games must be between 1 and 500")
                return
        except ValueError:
            print("Error: Number of games must be an integer")
            return
    
    num_players = 4
    
    # Define strategies (same for all games)
    strategies = [
        MyStrategy(),
        BalancedStrategy(),
        MyStrategy(),
        BalancedStrategy()
    ]

    strategy_names = ['my strategy 1', 'Balanced Strategy', 'My Strategy 2', 'Balanced Strategy']

    if num_games == 1:
        # Single game mode - verbose output
        print("=" * 60)
        print("Power Grid Simulation")
        print("=" * 60)
        print(f"\nPlayers: {', '.join([f'P{i}: {strategy_names[i]}' for i in range(num_players)])}\n")
        
        winner, final_stats = run_single_game(
            num_players, strategies, strategy_names, 
            verbose=True, enable_logging=True
        )
        
        print(f"\n{'='*60}")
        print(f"Game finished! Winner: Player {winner} ({strategy_names[winner]})")
        print(f"{'='*60}")
    else:
        # Tournament mode - suppress output
        print("=" * 60)
        print(f"Power Grid Tournament - Running {num_games} games")
        print("=" * 60)
        print(f"Players: {', '.join([f'P{i}: {strategy_names[i]}' for i in range(num_players)])}\n")
        
        # Initialize statistics
        stats = {
            i: {
                'wins': 0,
                'total_cities_powered': 0,
                'total_cities_connected': 0,
                'total_money': 0
            }
            for i in range(num_players)
        }
        
        # Run games
        for game_num in range(1, num_games + 1):
            if game_num % 50 == 0 or game_num == 1:
                print(f"Running game {game_num}/{num_games}...", end='\r')
            
            winner, final_stats = run_single_game(
                num_players, strategies, strategy_names,
                verbose=False, enable_logging=False
            )
            
            # Update statistics
            for player_idx, player_stats in enumerate(final_stats):
                stats[player_idx]['wins'] += 1 if player_stats['winner'] else 0
                stats[player_idx]['total_cities_powered'] += player_stats['cities_powered']
                stats[player_idx]['total_cities_connected'] += player_stats['cities_connected']
                stats[player_idx]['total_money'] += player_stats['money']
        
        print(f"Completed {num_games} games" + " " * 20)  # Clear the progress line
        
        # Calculate and display averages
        print("\n" + "=" * 60)
        print("Final Average Scores:")
        print("=" * 60)
        
        for player_idx in range(num_players):
            wins = stats[player_idx]['wins']
            avg_cities_powered = stats[player_idx]['total_cities_powered'] / num_games
            avg_cities_connected = stats[player_idx]['total_cities_connected'] / num_games
            avg_money = stats[player_idx]['total_money'] / num_games
            
            print(f"Player {player_idx}: {wins:3d} wins {avg_cities_powered:.0f} cities powered, "
                  f"{avg_cities_connected:.0f} cities connected, {avg_money:.0f}E")
        
        print("=" * 60)


if __name__ == '__main__':
    main()

