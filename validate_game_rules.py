"""
Standalone script to validate game rules by checking log files
and running rule compliance tests
"""

import json
import sys
import os
from pathlib import Path


def validate_log_file(log_file='power_grid_game_log.json'):
    """Validate that a log file doesn't contain rule violations"""
    if not os.path.exists(log_file):
        print(f"Log file {log_file} not found. Run a game first to generate it.")
        return False
    
    violations = []
    
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        print(f"Validating {len(log_data)} game states from {log_file}...")
        
        for step_num, state_entry in enumerate(log_data):
            game_state = state_entry.get('gameState', {})
            description = state_entry.get('description', f'step_{step_num}')
            
            # Check player order follows rules
            # NOTE: Player order is only determined at the START of each round (Phase 1).
            # During the round, players can buy plants/build cities, but order doesn't change
            # until the next round's Phase 1. So we only check order:
            # 1. At initial setup (when all players are equal)
            # 2. After Phase 1 determine_order (description contains "after_determine_order")
            players = game_state.get('players', [])
            player_order = game_state.get('player_order', [])
            
            # Only check player order at specific points:
            # - Initial setup
            # - After determine_order phase
            is_initial_setup = description == 'initial_setup'
            is_after_determine_order = 'after_determine_order' in description
            
            if is_initial_setup or is_after_determine_order:
                # Verify player order: should be sorted by cities descending, then largest plant
                player_data = []
                for i, p in enumerate(players):
                    cities = len(p.get('generators', []))
                    cards = p.get('cards', [])
                    largest_plant = max([c.get('cost', 0) for c in cards]) if cards else 0
                    player_data.append((i, cities, largest_plant))
                
                # Check if all players have the same city/plant counts (e.g., initial setup)
                player_keys = [(cities, largest_plant) for _, cities, largest_plant in player_data]
                all_equal = len(set(player_keys)) == 1
                
                if not all_equal:
                    # Players have different city/plant counts, so order must be sorted
                    # Check if order matches expected sort
                    expected_order = sorted(player_data, key=lambda x: (-x[1], -x[2]))
                    expected_order_indices = [x[0] for x in expected_order]
                    
                    if player_order != expected_order_indices:
                        violations.append(
                            f"{description}: Player order violation. "
                            f"Expected {expected_order_indices} (by cities then plants), "
                            f"got {player_order}. "
                            f"Player data: {[(i, c, p) for i, c, p in player_data]}"
                        )
                # If all players are equal, any order is valid (preserve random initial order)
            
            # Check auction state
            if game_state.get('auction_active', False):
                current_winner = game_state.get('auction_current_winner')
                active_bidders = game_state.get('auction_active_bidders', [])
                
                # Current winner should not be in active_bidders
                if current_winner is not None and current_winner in active_bidders:
                    violations.append(
                        f"{description}: Auction violation - Current winner {current_winner} "
                        f"is in active_bidders {active_bidders}"
                    )
            
            # Check step constraints on city occupancy
            step = game_state.get('step', 1)
            city_occupancy = game_state.get('city_occupancy', {})
            
            max_occupants = {1: 1, 2: 2, 3: 3}.get(step, 1)
            
            for city, occupants in city_occupancy.items():
                if len(occupants) > max_occupants:
                    violations.append(
                        f"{description}: Step {step} violation - City {city} has {len(occupants)} "
                        f"players (max allowed: {max_occupants})"
                    )
            
            # Check market structure
            current_market = game_state.get('current_market', [])
            future_market = game_state.get('future_market', [])
            
            if step == 3:
                # Step 3: should have 6 plants total in current, 0 in future
                if len(current_market) > 6:
                    violations.append(
                        f"{description}: Step 3 violation - current_market has {len(current_market)} "
                        f"plants (max 6)"
                    )
                if len(future_market) > 0:
                    violations.append(
                        f"{description}: Step 3 violation - future_market should be empty, "
                        f"has {len(future_market)} plants"
                    )
            else:
                # Steps 1-2: should have 4 in current market
                if len(current_market) > 4:
                    violations.append(
                        f"{description}: Step {step} violation - current_market has {len(current_market)} "
                        f"plants (max 4)"
                    )
            
            # Check that players don't have more than 3 plants
            for i, player in enumerate(players):
                num_plants = len(player.get('cards', []))
                if num_plants > 3:
                    violations.append(
                        f"{description}: Player {i} has {num_plants} plants (max 3)"
                    )
            
            # Check that players don't have negative money
            for i, player in enumerate(players):
                money = player.get('money', 0)
                if money < 0:
                    violations.append(
                        f"{description}: Player {i} has negative money: {money}E"
                    )
            
            # Check resource storage capacity
            for i, player in enumerate(players):
                cards = player.get('cards', [])
                resources = player.get('resources', {})
                
                # Calculate capacity for each resource type
                capacities = {'coal': 0, 'oil': 0, 'gas': 0, 'uranium': 0}
                
                for card in cards:
                    resource_type = card.get('resource', '')
                    resource_cost = card.get('resource_cost', 0)
                    
                    if resource_type == 'green':
                        continue
                    elif resource_type == 'oil&gas':
                        # Hybrid: can store oil or gas (shared capacity)
                        capacities['oil'] += resource_cost * 2
                        capacities['gas'] += resource_cost * 2
                    elif resource_type == 'nuclear':
                        capacities['uranium'] += resource_cost * 2
                    elif resource_type in capacities:
                        capacities[resource_type] += resource_cost * 2
                
                # Check if player has more resources than capacity
                for res_type, capacity in capacities.items():
                    amount = resources.get(res_type, 0)
                    if amount > capacity:
                        violations.append(
                            f"{description}: Player {i} has {amount} {res_type} "
                            f"(capacity: {capacity})"
                        )
            
            # Check that plants are sorted in market
            if current_market:
                costs = [c.get('cost', 0) for c in current_market]
                if costs != sorted(costs):
                    violations.append(
                        f"{description}: Current market not sorted: {costs}"
                    )
            
            if future_market:
                costs = [c.get('cost', 0) for c in future_market]
                if costs != sorted(costs):
                    violations.append(
                        f"{description}: Future market not sorted: {costs}"
                    )
            
            # Check Step 2 threshold (7 cities for 4 players)
            if step == 2:
                # Verify at least one player has >= 7 cities
                max_cities = max([len(p.get('generators', [])) for p in players])
                if max_cities < 7:
                    violations.append(
                        f"{description}: Step 2 triggered but max cities is {max_cities} "
                        f"(should be >= 7)"
                    )
            
            # Check game end condition
            if game_state.get('game_over', False):
                max_cities = max([len(p.get('generators', [])) for p in players])
                if max_cities < 18:
                    violations.append(
                        f"{description}: Game ended but max cities is {max_cities} "
                        f"(should be >= 18)"
                    )
        
        if violations:
            print(f"\n❌ Found {len(violations)} rule violations:\n")
            for i, violation in enumerate(violations, 1):
                print(f"  {i}. {violation}")
            return False
        else:
            print(f"\n✅ No rule violations found in {len(log_data)} game states!")
            return True
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    except Exception as e:
        print(f"Error validating log file: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to validate game rules"""
    print("=" * 60)
    print("Power Grid Rule Compliance Validator")
    print("=" * 60)
    
    # Check for log file
    log_file = 'power_grid_game_log.json'
    if os.path.exists(log_file):
        print(f"\nValidating log file: {log_file}")
        log_valid = validate_log_file(log_file)
    else:
        print(f"\n⚠ Log file {log_file} not found.")
        print("  Run a game first to generate a log file for validation.")
        log_valid = None
    
    print("\n" + "=" * 60)
    print("To run rule compliance tests, use:")
    print("  pytest test_rule_compliance.py -v")
    print("=" * 60)
    
    if log_valid is False:
        sys.exit(1)
    elif log_valid is True:
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
