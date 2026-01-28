"""
Main game runner for Power Grid simulation
"""

import random
import json
from itertools import combinations
from datetime import datetime
from card import Card
from Player_class import Player
from board_setup import (
    generate_color_graph, random_choose_play_area, create_game_board,
    generate_game_graph, create_city_nodes, starting_player_order, market_setup
)
from card_setup import market_setup as card_market_setup
import create_use_resources as res
from game_engine import GameEngine
from player_strategies import RandomStrategy, GreedyStrategy, ConservativeStrategy, BalancedStrategy, MyStrategy, TestStrategy, OptimalStrategy, PowerGridMasterStrategy, MyMightyStrategy, SmartTriggerStrategy
from endgame_sniper import EndgameSniper
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

    # Run game (max_rounds=25 so games can reach 17 cities before hitting cap)
    winner = engine.run_game(verbose=verbose, max_rounds=35)

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


def select_strategies(num_strategies=4):
    """Prompt user to select strategies from available options"""
    # Define available strategies with their display names
    available_strategies = {
        '1': ('RandomStrategy', 'Random Strategy', RandomStrategy),
        '2': ('GreedyStrategy', 'Greedy Strategy', GreedyStrategy),
        '3': ('ConservativeStrategy', 'Conservative Strategy', ConservativeStrategy),
        '4': ('BalancedStrategy', 'Balanced Strategy', BalancedStrategy),
        '5': ('MyStrategy', 'My Strategy', MyStrategy),
        '6': ('TestStrategy', 'Test Strategy', TestStrategy),
        '7': ('OptimalStrategy', 'Optimal Strategy', OptimalStrategy),
        '8': ('PowerGridMasterStrategy', 'PowerGridMaster Strategy', PowerGridMasterStrategy),
        '9': ('MyMightyStrategy', 'My Mighty Strategy', MyMightyStrategy),
        '10': ('SmartTriggerStrategy', 'Smart Trigger Strategy', SmartTriggerStrategy),
        '11': ('EndgameSniper', 'Endgame Sniper', EndgameSniper)
    }
    
    print("\n" + "=" * 60)
    print("Available Strategies:")
    print("=" * 60)
    for key, (_, name, _) in sorted(available_strategies.items()):
        print(f"  {key}. {name}")
    print("=" * 60)
    
    selected_strategies = []
    selected_names = []
    
    for i in range(num_strategies):
        while True:
            choice = input(f"\nSelect strategy {i+1}/{num_strategies} (1-11): ").strip()
            if choice in available_strategies:
                _, name, strategy_class = available_strategies[choice]
                selected_strategies.append(strategy_class())
                selected_names.append(name)
                print(f"  Strategy {i+1}: {name}")
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and 11.")
    
    return selected_strategies, selected_names


def run_multi_game_competition(strategies, strategy_names, num_games_per_combination=500):
    """Run multi-game competition across all combinations of 4 strategies from 8 selected strategies"""
    # Initialize stats dictionary keyed by strategy name
    stats = {name: {
        'wins': 0,
        'games_played': 0,
        'total_cities_powered': 0,
        'total_cities_connected': 0,
        'total_money': 0
    } for name in strategy_names}
    
    # Generate all combinations (8 choose 4 = 70)
    all_combinations = list(combinations(range(8), 4))
    num_combinations = len(all_combinations)
    total_games = num_combinations * num_games_per_combination
    
    print("\n" + "=" * 60)
    print("Multi-Game Strategy Competition")
    print("=" * 60)
    print(f"Strategies: {', '.join(strategy_names)}")
    print(f"Number of combinations: {num_combinations}")
    print(f"Games per combination: {num_games_per_combination}")
    print(f"Total games: {total_games}")
    print("=" * 60)
    
    # Iterate through each combination
    for combo_idx, combo in enumerate(all_combinations, 1):
        # Get strategies and names for this combination
        combo_strategies = [strategies[i] for i in combo]
        combo_names = [strategy_names[i] for i in combo]
        
        # Create mapping from player index to strategy name
        player_to_strategy = {i: combo_names[i] for i in range(4)}
        
        # Display progress
        print(f"\nCombination {combo_idx}/{num_combinations}: {', '.join(combo_names)}")
        print(f"Running {num_games_per_combination} games...")
        
        # Run games for this combination
        for game_num in range(1, num_games_per_combination + 1):
            if game_num % 50 == 0 or game_num == 1:
                print(f"  Game {game_num}/{num_games_per_combination}...", end='\r')
            
            winner, final_stats = run_single_game(
                num_players=4,
                strategies=combo_strategies,
                strategy_names=combo_names,
                verbose=False,
                enable_logging=False
            )
            
            # Update statistics by strategy name (not player index)
            for player_idx, player_stats in enumerate(final_stats):
                strategy_name = player_to_strategy[player_idx]
                stats[strategy_name]['games_played'] += 1
                if player_stats['winner']:
                    stats[strategy_name]['wins'] += 1
                stats[strategy_name]['total_cities_powered'] += player_stats['cities_powered']
                stats[strategy_name]['total_cities_connected'] += player_stats['cities_connected']
                stats[strategy_name]['total_money'] += player_stats['money']
        
        print(f"  Completed {num_games_per_combination} games" + " " * 20)  # Clear progress line
    
    # Calculate final statistics
    final_results = {}
    for strategy_name, strategy_stats in stats.items():
        games_played = strategy_stats['games_played']
        if games_played > 0:
            final_results[strategy_name] = {
                'wins': strategy_stats['wins'],
                'games_played': games_played,
                'win_rate': strategy_stats['wins'] / games_played,
                'avg_cities_powered': strategy_stats['total_cities_powered'] / games_played,
                'avg_cities_connected': strategy_stats['total_cities_connected'] / games_played,
                'avg_money': strategy_stats['total_money'] / games_played
            }
        else:
            final_results[strategy_name] = {
                'wins': 0,
                'games_played': 0,
                'win_rate': 0.0,
                'avg_cities_powered': 0.0,
                'avg_cities_connected': 0.0,
                'avg_money': 0.0
            }
    
    # Save results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"competition_results_{timestamp}.json"
    
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'num_combinations': num_combinations,
        'games_per_combination': num_games_per_combination,
        'total_games': total_games,
        'strategies': final_results
    }
    
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to: {filename}")
    
    # Display results
    print("\n" + "=" * 60)
    print("Multi-Game Competition Results")
    print("=" * 60)
    print(f"{'Strategy Name':<30} {'Wins':<8} {'Win%':<8} {'Avg Cities Powered':<20} {'Avg Cities Connected':<22} {'Avg Money':<10}")
    print("-" * 100)
    
    # Sort by win rate (descending)
    sorted_results = sorted(final_results.items(), key=lambda x: x[1]['win_rate'], reverse=True)
    
    for strategy_name, results in sorted_results:
        print(f"{strategy_name:<30} {results['wins']:<8} {results['win_rate']*100:>6.1f}%  "
              f"{results['avg_cities_powered']:>18.1f}  {results['avg_cities_connected']:>20.1f}  "
              f"{results['avg_money']:>8.0f}E")
    
    print("=" * 60)
    
    return final_results


def main():
    """Run games with 4 test players - single game, tournament, or competition mode"""
    import sys
    
    # Prompt user for game mode
    print("\n" + "=" * 60)
    print("Power Grid Simulation - Game Mode Selection")
    print("=" * 60)
    print("1. Single Game Mode")
    print("2. Tournament Mode (multiple games with same 4 strategies)")
    print("3. Multi-Game Competition Mode (8 strategies, all combinations)")
    print("=" * 60)
    
    while True:
        mode_choice = input("\nSelect game mode (1-3): ").strip()
        if mode_choice in ['1', '2', '3']:
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    num_players = 4
    
    # Get number of games for tournament mode
    num_games = 1
    if mode_choice == '2':
        # Check if provided via command line (backward compatibility)
        if len(sys.argv) > 1:
            try:
                num_games = int(sys.argv[1])
                if num_games < 1 or num_games > 500:
                    print("Error: Number of games must be between 1 and 500")
                    return
            except ValueError:
                print("Error: Number of games must be an integer")
                return
        else:
            # Prompt user for number of games
            while True:
                try:
                    num_games_input = input("\nEnter number of games to run (1-500): ").strip()
                    num_games = int(num_games_input)
                    if 1 <= num_games <= 500:
                        break
                    else:
                        print("Error: Number of games must be between 1 and 500")
                except ValueError:
                    print("Error: Please enter a valid integer")
    
    # Prompt user to select strategies based on mode
    if mode_choice == '3':
        # Competition mode: select 8 strategies
        print("\n" + "=" * 60)
        print("Multi-Game Competition Mode")
        print("=" * 60)
        print("Select 8 strategies to compete in all possible 4-player combinations")
        print("(70 combinations total, 500 games per combination)")
        print("=" * 60)
        strategies, strategy_names = select_strategies(num_strategies=8)
    else:
        # Single game or tournament mode: select 4 strategies
        strategies, strategy_names = select_strategies(num_strategies=4)

    if mode_choice == '3':
        # Multi-game competition mode
        run_multi_game_competition(strategies, strategy_names, num_games_per_combination=500)
    elif num_games == 1:
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
    elif mode_choice == '2':
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

