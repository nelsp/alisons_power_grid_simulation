#!/usr/bin/env python3
"""
Tournament runner for Power Grid strategies.
Discovers all strategies and runs a round-robin tournament.
"""

import argparse
import importlib.util
import inspect
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from itertools import combinations

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from card import Card
from Player_class import Player
from board_setup import (
    generate_color_graph, random_choose_play_area, create_game_board,
    generate_game_graph
)
import create_use_resources as res
from game_engine import GameEngine
from player_strategies import Strategy

# Europe map data
eur_areas = [
    ('brown', 'red'), ('brown', 'purple'), ('brown', 'yellow'), ('brown', 'green'),
    ('brown', 'orange'), ('purple', 'red'), ('red', 'yellow'), ('yellow', 'blue'),
    ('yellow', 'green'), ('blue', 'green'), ('orange', 'green')
]

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
    (('brown', 'Praha'), ('brown', 'Munchen'), 8)
]


def discover_strategies():
    """Discover all strategy classes in the repository."""
    strategies = {}
    base_dir = Path(__file__).parent

    # Import from player_strategies.py (built-in strategies)
    from player_strategies import (
        RandomStrategy, GreedyStrategy, ConservativeStrategy, BalancedStrategy,
        MyStrategy, OptimalStrategy, PowerGridMasterStrategy, MyMightyStrategy,
        SmartTriggerStrategy
    )

    built_in = [
        ('RandomStrategy', RandomStrategy),
        ('GreedyStrategy', GreedyStrategy),
        ('ConservativeStrategy', ConservativeStrategy),
        ('BalancedStrategy', BalancedStrategy),
        ('MyStrategy', MyStrategy),
        ('OptimalStrategy', OptimalStrategy),
        ('PowerGridMasterStrategy', PowerGridMasterStrategy),
        ('MyMightyStrategy', MyMightyStrategy),
        ('SmartTriggerStrategy', SmartTriggerStrategy),
    ]

    for name, cls in built_in:
        strategies[name] = cls

    # Discover standalone strategy files
    strategy_files = [
        'endgame_sniper.py',
        'adaptive_strategist.py',
        'sui_strategy.py',
        'sui_strategy_v2.py',
        'smart_trigger_v2.py',
        'smart_trigger_v3.py',
        'smart_trigger_v4.py',
    ]

    for filename in strategy_files:
        filepath = base_dir / filename
        if filepath.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    filename[:-3], filepath
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Strategy subclasses in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, Strategy) and
                        obj is not Strategy and
                        name not in strategies):
                        strategies[name] = obj
            except Exception as e:
                print(f"Warning: Could not load {filename}: {e}")

    return strategies


def setup_game(num_players=4, random_seed=None):
    """Set up a new game."""
    if random_seed:
        random.seed(random_seed)

    color_graph = generate_color_graph(eur_areas)
    play_areas = random_choose_play_area(num_players, color_graph)
    game_board = create_game_board(europe, play_areas)
    board_graph = generate_game_graph(game_board)

    players = []
    for i in range(num_players):
        players.append(Player(f'Player_{i}'))

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

    # Resources
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
    """Run a single game and return the winner index and stats."""
    random_seed = random.randint(1, 10000)

    players, current_market, future_market, deck, board_graph, resources, player_order = setup_game(
        num_players=num_players, random_seed=random_seed
    )

    for i, (player, strategy) in enumerate(zip(players, strategies)):
        player.strategy = strategy
        player.name = f'{strategy_names[i]}'

    engine = GameEngine(
        players=players,
        current_market=current_market,
        future_market=future_market,
        deck=deck,
        board_graph=board_graph,
        resources=resources,
        player_order=player_order,
        num_players=num_players,
        enable_logging=False
    )

    winner = engine.run_game(verbose=False, max_rounds=35)

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


def run_tournament(strategy_classes, games_per_matchup=20, num_players=4):
    """Run a round-robin tournament with all strategy combinations."""
    num_strategies = len(strategy_classes)
    all_combinations = list(combinations(range(num_strategies), num_players))
    total_games = len(all_combinations) * games_per_matchup

    print(f"Tournament: {num_strategies} strategies")
    print(f"Combinations: {len(all_combinations)}")
    print(f"Games per combo: {games_per_matchup}")
    print(f"Total games: {total_games}")
    print("=" * 60)

    # Initialize stats
    stats = {name: {
        'wins': 0,
        'games_played': 0,
        'total_cities_powered': 0,
        'total_cities_connected': 0,
        'total_money': 0
    } for name, _ in strategy_classes}

    game_count = 0
    for combo_idx, combo in enumerate(all_combinations, 1):
        combo_strategies = [strategy_classes[i][1]() for i in combo]
        combo_names = [strategy_classes[i][0] for i in combo]
        player_to_strategy = {i: combo_names[i] for i in range(num_players)}

        print(f"\nCombo {combo_idx}/{len(all_combinations)}: {', '.join(combo_names)}")

        for game_num in range(1, games_per_matchup + 1):
            game_count += 1
            if game_num % 10 == 0:
                print(f"  Game {game_num}/{games_per_matchup}... ({game_count}/{total_games} total)", end='\r')

            try:
                winner, final_stats = run_single_game(
                    num_players=num_players,
                    strategies=combo_strategies,
                    strategy_names=combo_names
                )

                for player_idx, player_stats in enumerate(final_stats):
                    strategy_name = player_to_strategy[player_idx]
                    stats[strategy_name]['games_played'] += 1
                    if player_stats['winner']:
                        stats[strategy_name]['wins'] += 1
                    stats[strategy_name]['total_cities_powered'] += player_stats['cities_powered']
                    stats[strategy_name]['total_cities_connected'] += player_stats['cities_connected']
                    stats[strategy_name]['total_money'] += player_stats['money']
            except Exception as e:
                print(f"\n  Error in game {game_num}: {e}")

        print(f"  Completed {games_per_matchup} games          ")

    return stats


def generate_report(stats, total_games):
    """Generate markdown and JSON reports."""
    results = []
    for name, s in stats.items():
        games = s['games_played']
        if games > 0:
            win_rate = s['wins'] / games
            avg_cities = s['total_cities_powered'] / games
            avg_money = s['total_money'] / games
            results.append((name, s['wins'], games, win_rate, avg_cities, avg_money))

    # Sort by win rate
    results.sort(key=lambda x: x[3], reverse=True)

    # Generate markdown
    lines = [
        "🏆 **Power Grid Tournament Results**",
        "",
        f"Total games: {total_games}",
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "```",
        f"{'Rank':<6} {'Strategy':<25} {'Wins':<8} {'Games':<8} {'Win%':<8} {'Avg Cities':<12} {'Avg Money':<10}",
        "-" * 80,
    ]

    for rank, (name, wins, games, win_rate, avg_cities, avg_money) in enumerate(results, 1):
        lines.append(
            f"{rank:<6} {name:<25} {wins:<8} {games:<8} {win_rate*100:>6.1f}%  {avg_cities:>10.1f}  {avg_money:>8.0f}E"
        )

    lines.append("```")

    # Add top 3 medal emojis
    if len(results) >= 1:
        lines.append(f"\n🥇 **1st: {results[0][0]}** ({results[0][3]*100:.1f}% win rate)")
    if len(results) >= 2:
        lines.append(f"🥈 **2nd: {results[1][0]}** ({results[1][3]*100:.1f}% win rate)")
    if len(results) >= 3:
        lines.append(f"🥉 **3rd: {results[2][0]}** ({results[2][3]*100:.1f}% win rate)")

    markdown = "\n".join(lines)

    # Generate JSON
    json_output = {
        'timestamp': datetime.now().isoformat(),
        'total_games': total_games,
        'results': {name: {
            'wins': s['wins'],
            'games_played': s['games_played'],
            'win_rate': s['wins'] / s['games_played'] if s['games_played'] > 0 else 0,
            'avg_cities_powered': s['total_cities_powered'] / s['games_played'] if s['games_played'] > 0 else 0,
            'avg_money': s['total_money'] / s['games_played'] if s['games_played'] > 0 else 0
        } for name, s in stats.items()}
    }

    return markdown, json_output


def main():
    parser = argparse.ArgumentParser(description='Run Power Grid strategy tournament')
    parser.add_argument('--games', type=int, default=20, help='Games per matchup')
    parser.add_argument('--output', type=str, default='results.json', help='Output JSON file')
    parser.add_argument('--markdown', type=str, default='results.md', help='Output markdown file')
    args = parser.parse_args()

    print("Discovering strategies...")
    strategies = discover_strategies()
    print(f"Found {len(strategies)} strategies:")
    for name in sorted(strategies.keys()):
        print(f"  - {name}")
    print()

    strategy_classes = list(strategies.items())
    num_players = 4

    all_combinations = list(combinations(range(len(strategy_classes)), num_players))
    total_games = len(all_combinations) * args.games

    # Run tournament
    stats = run_tournament(strategy_classes, games_per_matchup=args.games, num_players=num_players)

    # Generate reports
    markdown, json_output = generate_report(stats, total_games)

    # Save files
    with open(args.markdown, 'w') as f:
        f.write(markdown)

    with open(args.output, 'w') as f:
        json.dump(json_output, f, indent=2)

    # Print to stdout
    print("\n" + markdown)
    print(f"\nResults saved to {args.output} and {args.markdown}")


if __name__ == '__main__':
    main()
