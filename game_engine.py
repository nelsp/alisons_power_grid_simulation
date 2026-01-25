"""
Power Grid Game Engine
Implements the complete game logic according to Power Grid Deluxe rules
"""

import random
import copy
from card import Card
import create_use_resources as res
from game_state_logger import GameStateLogger
from player_action import PlayerAction, ActionType


# Payment table: cities powered -> Elektro earned
PAYMENT_TABLE = {
    0: 10, 1: 22, 2: 33, 3: 44, 4: 54, 5: 64, 6: 73, 7: 82, 8: 90, 9: 98, 10: 105,
    11: 112, 12: 118, 13: 124, 14: 129, 15: 134, 16: 138, 17: 142, 18: 145, 19: 148, 20: 150
}

# Resource resupply tables [Step1, Step2, Step3] for each number of players
RESUPPLY_TABLES = {
    'coal': {2: [2, 6, 2], 3: [2, 6, 2], 4: [3, 7, 4], 5: [3, 8, 4], 6: [5, 10, 5]},
    'gas': {2: [2, 3, 5], 3: [2, 3, 5], 4: [3, 4, 5], 5: [3, 5, 7], 6: [4, 6, 8]},
    'oil': {2: [2, 2, 3], 3: [2, 2, 3], 4: [3, 3, 4], 5: [4, 3, 5], 6: [4, 5, 6]},
    'uranium': {2: [1, 1, 2], 3: [1, 1, 2], 4: [1, 2, 2], 5: [2, 3, 3], 6: [2, 3, 4]}
}

# Step transition thresholds (number of cities to trigger Step 2)
STEP_2_THRESHOLDS = {2: 7, 3: 7, 4: 7, 5: 6, 6: 5}


class GameState:
    """Represents the current state of the game"""

    def __init__(self, players, current_market, future_market, deck, board_graph,
                 resources, player_order, step=1, round_num=1, phase='determine_order'):
        self.players = players  # List of Player objects
        self.current_market = current_market  # List of Card objects (4 plants)
        self.future_market = future_market  # List of Card objects (4-5 plants)
        self.deck = deck  # List of Card objects
        self.board_graph = board_graph  # Dictionary graph of cities
        self.resources = resources  # Dict of Resource objects {'coal': Resource, ...}
        self.player_order = player_order  # List of player indices in order
        self.step = step  # 1, 2, or 3
        self.round_num = round_num
        self.phase = phase  # determine_order, auction, buy_resources, build, bureaucracy
        self.step_3_triggered = False
        self.game_over = False
        self.winner = None

        # Track city occupancy: {city_name: [player_indices]}
        self.city_occupancy = {}
        for city_node in board_graph:
            city_name = city_node[1] if isinstance(city_node, tuple) else city_node
            self.city_occupancy[city_name] = []

        # Auction state tracking
        self.auction_active = False
        self.auction_plant = None  # Card being auctioned
        self.auction_current_bid = None  # Current highest bid
        self.auction_current_winner = None  # Player index of current winner
        self.auction_active_bidders = []  # List of player indices still in the auction
        self.auction_starter = None  # Player index who opened the auction

    def to_dict(self):
        """Convert GameState to dictionary for JSON serialization"""
        # Convert board_graph to serializable format
        board_graph_serializable = {}
        for city_node, connections in self.board_graph.items():
            city_key = str(city_node)
            board_graph_serializable[city_key] = {}
            for connected_city, cost in connections.items():
                board_graph_serializable[city_key][str(connected_city)] = cost

        return {
            'players': [player.to_dict() for player in self.players],
            'current_market': [card.to_dict() for card in self.current_market],
            'future_market': [card.to_dict() for card in self.future_market],
            'deck': [card.to_dict() for card in self.deck],
            'board_graph': board_graph_serializable,
            'resources': {name: resource.to_dict() for name, resource in self.resources.items()},
            'player_order': list(self.player_order),  # Create a copy of the list
            'step': self.step,
            'round_num': self.round_num,
            'phase': self.phase,
            'step_3_triggered': self.step_3_triggered,
            'game_over': self.game_over,
            'winner': self.winner,
            'city_occupancy': {city: list(occupants) for city, occupants in self.city_occupancy.items()},  # Deep copy
            'auction_active': self.auction_active,
            'auction_plant': self.auction_plant.to_dict() if self.auction_plant else None,
            'auction_current_bid': self.auction_current_bid,
            'auction_current_winner': self.auction_current_winner,
            'auction_active_bidders': list(self.auction_active_bidders),
            'auction_starter': self.auction_starter
        }


class GameEngine:
    """Main game engine for Power Grid"""

    def __init__(self, players, current_market, future_market, deck, board_graph, resources, player_order, num_players, enable_logging=False, game_id=None, log_file=None):
        self.num_players = num_players
        self.players = players
        self.game_state = GameState(
            players=players,
            current_market=sorted(current_market, key=lambda c: c.cost),
            future_market=sorted(future_market, key=lambda c: c.cost),
            deck=deck,
            board_graph=board_graph,
            resources=resources,
            player_order=player_order,
            step=1,
            round_num=1,
            phase='determine_order'
        )

        # Initialize game state logger
        self.enable_logging = enable_logging
        if enable_logging:
            self.logger = GameStateLogger(game_id=game_id, output_file=log_file)
            # Log initial state
            self.logger.log_state(self.game_state, description="initial_setup")
    
    def run_game(self, player_strategies=None, verbose=True, max_rounds=20):
        """Run the complete game

        Args:
            player_strategies: (DEPRECATED) List of strategy objects for each player.
                             Strategies should now be assigned to player.strategy
            verbose: Whether to print game progress
            max_rounds: Maximum number of rounds to play (default: 20)
        """
        # Support legacy API where strategies are passed separately
        if player_strategies is not None:
            for i, strategy in enumerate(player_strategies):
                if self.players[i].strategy is None:
                    self.players[i].strategy = strategy

        if verbose:
            print("=" * 60)
            print("POWER GRID - Game Starting")
            print("=" * 60)

        while not self.game_state.game_over:
            # Check if we've reached max rounds
            if self.game_state.round_num > max_rounds:
                self.game_state.game_over = True
                if verbose:
                    print(f"\nMaximum rounds ({max_rounds}) reached.")
                break

            if verbose:
                print("\n" + "=" * 60)
                print(f"Round {self.game_state.round_num} - Step {self.game_state.step}")
                print("=" * 60)

            # Phase 1: Determine Player Order
            self.phase_1_determine_order()
            if verbose:
                print(f"Player Order: {[f'P{p}' for p in self.game_state.player_order]}")
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_determine_order")

            # Phase 2: Auction Power Plants
            self.phase_2_auction(verbose)
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_auction")

            # Phase 3: Buy Resources
            self.phase_3_buy_resources(verbose)
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_buy_resources")

            # Phase 4: Build Generators
            self.phase_4_build(verbose)
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_build")

            # Check for end game after building (game may have ended during build phase)
            if self.game_state.game_over or self.check_end_game():
                if self.enable_logging and not self.game_state.game_over:
                    self.logger.log_state(self.game_state, description="game_end_condition_triggered")
                break

            # Phase 5: Bureaucracy
            self.phase_5_bureaucracy(verbose)
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_bureaucracy")

            # Check step transitions
            self.check_step_transitions(verbose)
            if self.enable_logging:
                self.logger.log_state(self.game_state, description=f"round_{self.game_state.round_num}_after_step_check")
            
            # Print account balances at end of round
            if verbose:
                print(f"\nAccount Balances (End of Round {self.game_state.round_num}):")
                for player_idx in self.game_state.player_order:
                    player = self.players[player_idx]
                    print(f"  Player {player_idx}: {player.money}E")
            
            # Prepare for next round
            self.game_state.round_num += 1
            self.game_state.phase = 'determine_order'
        
        # Game over - determine winner
        winner_idx = self.determine_winner()
        if verbose:
            print("\n" + "=" * 60)
            print("GAME OVER")
            if self.game_state.round_num > max_rounds:
                print(f"Maximum rounds ({max_rounds}) reached.")
            print("=" * 60)
            print(f"Winner: Player {winner_idx}")
            self.print_final_scores(verbose)

        # Log final state and write to file
        if self.enable_logging:
            self.logger.log_state(self.game_state, description=f"game_over_winner_{winner_idx}")
            self.logger.write_to_file()
            if verbose:
                print(f"\nGame state log written to: {self.logger.output_file}")
                print(f"Total states logged: {self.logger.get_state_count()}")

        return winner_idx
    
    def phase_1_determine_order(self):
        """Phase 1: Determine player order based on cities connected
        
        If all players have the same number of cities and plants (e.g., first round),
        the order remains as set (preserving initial random order).
        Once players have different cities/plants, order is determined by:
        - Most cities (descending)
        - Largest plant as tie-breaker (descending)
        """
        # Sort by cities connected (descending), then by largest plant (descending)
        def sort_key(player_idx):
            player = self.players[player_idx]
            cities_count = len(player.generators)
            largest_plant = max([card.cost for card in player.cards] if player.cards else [0])
            return (-cities_count, -largest_plant)  # Negative for descending
        
        # Only sort if players have different city/plant counts
        # This preserves initial random order when everyone starts equal
        player_keys = [sort_key(p) for p in self.game_state.player_order]
        if len(set(player_keys)) > 1:
            # Players have different cities/plants, so sort them
            self.game_state.player_order = sorted(self.game_state.player_order, key=sort_key)
        # Otherwise, keep the current order (which should be random from initial setup)
        
        self.game_state.phase = 'auction'
    
    def phase_2_auction(self, verbose):
        """Phase 2: Auction power plants with validation-retry loops

        Game engine ONLY validates and executes moves - never makes decisions.
        Invalid moves result in retries, then exceptions if max retries exceeded.
        """
        players_who_bought = set()
        players_who_passed = set()
        is_first_round = (self.game_state.round_num == 1)

        if verbose:
            print("\n--- AUCTION PHASE ---")
            # Debug: Show current market at start of auction
            print(f"  Current market: {[p.cost for p in self.game_state.current_market]}")
            print(f"  Future market: {[p.cost for p in self.game_state.future_market]}")

        # Continue until all players have bought or passed
        while len(players_who_bought) + len(players_who_passed) < len(self.players):
            # Get eligible players (in turn order)
            eligible_players = [p for p in self.game_state.player_order
                              if p not in players_who_bought and p not in players_who_passed]

            if not eligible_players:
                break

            # Check if market has plants
            if not self.game_state.current_market:
                if verbose:
                    print("No plants available in market")
                break

            # Current player gets validated action (with retries)
            current_player_idx = eligible_players[0]

            # Get validated action - raises exception if player fails after max_retries
            action = self.get_validated_auction_opening(current_player_idx, is_first_round, verbose)

            # Handle pass
            if action.action_type == ActionType.AUCTION_PASS:
                players_who_passed.add(current_player_idx)
                if verbose:
                    print(f"Player {current_player_idx}: Passed")
                continue

            # Handle buy - start auction
            plant = action.plant
            initial_bid = action.bid
            initial_discard = action.discard

            if verbose:
                print(f"\nPlayer {current_player_idx} opens bidding on plant {plant.cost} at {initial_bid}E")

            # Run validated auction
            winner_idx, final_bid, discard_card = self.run_plant_auction(
                plant, current_player_idx, initial_bid, initial_discard,
                eligible_players, players_who_passed, verbose
            )

            if winner_idx is not None:
                # Execute purchase with player's chosen discard
                self.execute_plant_purchase(winner_idx, plant, final_bid, discard_card, verbose)
                players_who_bought.add(winner_idx)
            else:
                # No one won (shouldn't happen but handle gracefully)
                if verbose:
                    print(f"No winner for plant {plant.cost}")

        # Europe rule: If all players passed without buying, remove smallest plant
        if not is_first_round and len(players_who_bought) == 0 and self.game_state.current_market:
            smallest = min(self.game_state.current_market, key=lambda c: c.cost)
            self.game_state.current_market.remove(smallest)
            if verbose:
                print(f"All players passed - removed plant {smallest.cost}")
            self.update_market_after_purchase()

        self.game_state.phase = 'buy_resources'

    def run_plant_auction(self, plant, starter_idx, initial_bid, initial_discard, eligible_players, players_who_passed, verbose):
        """Run a validated auction for a specific plant

        Args:
            plant: The plant being auctioned
            starter_idx: Player who started the auction
            initial_bid: Starting bid
            initial_discard: Card starter will discard (None if < 3 plants)
            eligible_players: List of player indices who can bid
            players_who_passed: Set of players who passed this round
            verbose: Print auction progress

        Returns:
            (winner_idx, final_bid, discard_card) or (None, None, None) if everyone passed
        """
        current_bid = initial_bid
        current_winner = starter_idx
        current_discard = initial_discard

        # Active bidders are eligible players not already passed, except starter
        active_bidders = [p for p in eligible_players
                         if p not in players_who_passed and p != starter_idx]

        # Set auction state
        self.game_state.auction_active = True
        self.game_state.auction_plant = plant
        self.game_state.auction_current_bid = current_bid
        self.game_state.auction_current_winner = current_winner
        self.game_state.auction_active_bidders = list(active_bidders)
        self.game_state.auction_starter = starter_idx

        # Log auction start
        if self.enable_logging:
            self.logger.log_state(self.game_state,
                description=f"auction_start_plant_{plant.cost}_player_{starter_idx}_bid_{initial_bid}")

        if not active_bidders:
            # No one else to bid, starter wins
            if verbose:
                print(f"  No other bidders, Player {starter_idx} wins at {initial_bid}E")

            # Clear auction state
            self.game_state.auction_active = False
            return (starter_idx, initial_bid, initial_discard)

        if verbose:
            print(f"  Active bidders: {active_bidders}")

        # Bidding loop - go through players in order until only one remains
        previous_winner = None  # Track previous winner to add them back when outbid
        while len(active_bidders) > 0:
            made_bid = False

            for player_idx in list(active_bidders):
                min_bid = current_bid + 1

                # Get validated bid action from player
                bid_action = self.get_validated_auction_bid(
                    player_idx, plant, current_bid, current_winner, min_bid, verbose
                )

                if bid_action.action_type == ActionType.AUCTION_BID_PASS:
                    active_bidders.remove(player_idx)

                    # Update auction state
                    self.game_state.auction_active_bidders = list(active_bidders)

                    # Log pass
                    if self.enable_logging:
                        self.logger.log_state(self.game_state,
                            description=f"auction_pass_player_{player_idx}")

                    if verbose:
                        print(f"  Player {player_idx}: Passed")
                    continue

                # Player made a valid bid
                new_bid = bid_action.bid
                new_discard = bid_action.discard

                # If someone else is outbidding the current winner, add previous winner back
                # to active_bidders (they can bid again now)
                if current_winner is not None and current_winner != player_idx:
                    previous_winner = current_winner
                    # Add previous winner back if they're still eligible
                    if (previous_winner not in players_who_passed and 
                        previous_winner in eligible_players and
                        previous_winner not in active_bidders):
                        active_bidders.append(previous_winner)
                        # Sort to maintain player order
                        active_bidders.sort(key=lambda x: eligible_players.index(x))

                current_bid = new_bid
                current_winner = player_idx
                current_discard = new_discard
                made_bid = True

                # Remove current winner from active_bidders - they cannot bid again
                # in this round until someone else outbids them
                if current_winner in active_bidders:
                    active_bidders.remove(current_winner)

                # Update auction state
                self.game_state.auction_current_bid = current_bid
                self.game_state.auction_current_winner = current_winner
                self.game_state.auction_active_bidders = list(active_bidders)

                # Log bid
                if self.enable_logging:
                    self.logger.log_state(self.game_state,
                        description=f"auction_bid_player_{player_idx}_amount_{new_bid}")

                if verbose:
                    print(f"  Player {player_idx}: Raises to {new_bid}E")

            # If no one made a bid this round, auction is over
            if not made_bid:
                break

        # Clear auction state
        self.game_state.auction_active = False

        # Log auction end
        if self.enable_logging:
            self.logger.log_state(self.game_state,
                description=f"auction_end_winner_{current_winner}_plant_{plant.cost}_final_bid_{current_bid}")

        return (current_winner, current_bid, current_discard)

    def validate_auction_opening(self, player_idx, action):
        """Validate a player's auction opening action

        Args:
            player_idx: Player index
            action: PlayerAction object

        Returns:
            (valid: bool, error_message: str or None)
        """
        if not isinstance(action, PlayerAction):
            return (False, "Action must be a PlayerAction object")

        player = self.players[player_idx]

        if action.action_type == ActionType.AUCTION_PASS:
            return (True, None)

        if action.action_type != ActionType.AUCTION_OPEN:
            return (False, f"Expected AUCTION_PASS or AUCTION_OPEN, got {action.action_type.value}")

        plant = action.plant
        bid = action.bid

        if plant is None:
            return (False, "Must specify plant to buy")

        if plant not in self.game_state.current_market:
            return (False, f"Plant {plant.cost} not in current market")

        if bid is None or not isinstance(bid, (int, float)):
            return (False, "Must specify bid amount")

        if bid < plant.cost:
            return (False, f"Bid {bid}E is below plant cost {plant.cost}E")

        if bid > player.money:
            return (False, f"Bid {bid}E exceeds available money {player.money}E")

        # Check if player can buy this plant
        if len(player.cards) >= 3:
            # Must be able to replace
            smallest_owned = min(player.cards, key=lambda c: c.cost)
            if plant.cost <= smallest_owned.cost:
                return (False, f"Plant {plant.cost} not better than smallest owned ({smallest_owned.cost})")

            # Must specify which plant to discard
            if action.discard is None:
                return (False, "Must specify which plant to discard (player has 3 plants)")

            if action.discard not in player.cards:
                return (False, f"Cannot discard plant {action.discard.cost} - not owned")

        return (True, None)

    def validate_auction_bid(self, player_idx, action, plant, current_bid, min_bid):
        """Validate a player's bid action during auction

        Args:
            player_idx: Player index
            action: PlayerAction object
            plant: Plant being auctioned
            current_bid: Current highest bid
            min_bid: Minimum valid bid

        Returns:
            (valid: bool, error_message: str or None, action: PlayerAction)
        """
        if not isinstance(action, PlayerAction):
            return (False, "Action must be a PlayerAction object", None)

        player = self.players[player_idx]

        if action.action_type == ActionType.AUCTION_BID_PASS:
            return (True, None, action)

        if action.action_type != ActionType.AUCTION_BID:
            return (False, f"Expected AUCTION_BID_PASS or AUCTION_BID, got {action.action_type.value}", None)

        bid_amount = action.bid

        if bid_amount is None:
            return (False, "Must specify bid amount", None)

        if bid_amount < min_bid:
            return (False, f"Bid {bid_amount}E below minimum {min_bid}E", None)

        if bid_amount > player.money:
            return (False, f"Bid {bid_amount}E exceeds available money {player.money}E", None)

        # Check discard requirement
        if len(player.cards) >= 3:
            if action.discard is None:
                return (False, "Must specify which plant to discard (player has 3 plants)", None)
            if action.discard not in player.cards:
                return (False, f"Cannot discard plant {action.discard.cost} - not owned", None)

        return (True, None, action)

    def get_validated_auction_opening(self, player_idx, is_first_round, verbose, max_retries=10):
        """Get a validated auction opening action from a player

        Asks the player's strategy for an action and validates it.
        Retries up to max_retries times if action is invalid.

        Args:
            player_idx: Player index
            is_first_round: Whether this is the first round (must buy)
            verbose: Whether to print validation errors
            max_retries: Maximum retry attempts (default 10)

        Returns:
            Validated PlayerAction with type AUCTION_PASS or AUCTION_OPEN

        Raises:
            Exception: If player strategy fails validation after max_retries
        """
        player = self.players[player_idx]
        strategy = player.strategy

        if strategy is None:
            raise Exception(f"Player {player_idx} has no strategy assigned")

        last_error = None
        for attempt in range(max_retries):
            try:
                # Ask strategy for action
                action = strategy.choose_auction_move(player, self.game_state)

                # Validate action
                valid, error = self.validate_auction_opening(player_idx, action)

                if not valid:
                    last_error = error
                    if verbose and attempt < max_retries - 1:
                        print(f"  Player {player_idx} invalid action: {error} (retry {attempt + 1}/{max_retries})")
                    continue

                # Check first round restriction
                if is_first_round and action.action_type == ActionType.AUCTION_PASS:
                    last_error = "Cannot pass in first round"
                    if verbose and attempt < max_retries - 1:
                        print(f"  Player {player_idx}: {last_error} (retry {attempt + 1}/{max_retries})")
                    continue

                return action

            except Exception as e:
                last_error = str(e)
                if verbose and attempt < max_retries - 1:
                    print(f"  Player {player_idx} strategy error: {e} (retry {attempt + 1}/{max_retries})")
                continue

        # Max retries exceeded
        # If first round and player tried to pass, force them to buy a plant
        if is_first_round and last_error == "Cannot pass in first round":
            # Force player to buy the cheapest available plant
            if self.game_state.current_market:
                cheapest_plant = min(self.game_state.current_market, key=lambda c: c.cost)
                min_bid = cheapest_plant.cost
                # Check if player can afford it
                if player.money >= min_bid:
                    if verbose:
                        print(f"  Player {player_idx}: Forced to buy plant {cheapest_plant.cost} (cannot pass in first round)")
                    return PlayerAction.auction_open(cheapest_plant, min_bid)
                else:
                    # Player can't afford cheapest plant - this is a real problem
                    raise Exception(f"Player {player_idx} cannot afford any plant in first round (has {player.money}E, cheapest plant is {min_bid}E)")
            else:
                raise Exception(f"Player {player_idx} must buy a plant in first round, but no plants available")
        
        raise Exception(f"Player {player_idx} failed to provide valid action after {max_retries} attempts. Last error: {last_error}")

    def get_validated_auction_bid(self, player_idx, plant, current_bid, current_winner, min_bid, verbose, max_retries=10):
        """Get a validated bid action from a player during an auction

        Args:
            player_idx: Player index
            plant: Plant being auctioned
            current_bid: Current highest bid
            current_winner: Player index of current high bidder
            min_bid: Minimum valid bid
            verbose: Whether to print validation errors
            max_retries: Maximum retry attempts (default 10)

        Returns:
            PlayerAction with type AUCTION_BID_PASS or AUCTION_BID

        Raises:
            Exception: If player strategy fails validation after max_retries
        """
        player = self.players[player_idx]
        strategy = player.strategy

        if strategy is None:
            raise Exception(f"Player {player_idx} has no strategy assigned")

        # Check if player can afford minimum bid
        if min_bid > player.money:
            return PlayerAction.auction_bid_pass()  # Auto-pass if can't afford

        last_error = None
        for attempt in range(max_retries):
            try:
                # Ask strategy for bid action
                if hasattr(strategy, 'bid_in_auction'):
                    action = strategy.bid_in_auction(player, self.game_state, plant, current_bid, current_winner)
                else:
                    # Strategy doesn't implement bidding - auto pass
                    return PlayerAction.auction_bid_pass()

                # Validate bid
                valid, error, validated_action = self.validate_auction_bid(
                    player_idx, action, plant, current_bid, min_bid
                )

                if not valid:
                    last_error = error
                    if verbose and attempt < max_retries - 1:
                        print(f"  Player {player_idx} invalid bid: {error} (retry {attempt + 1}/{max_retries})")
                    continue

                return validated_action

            except Exception as e:
                last_error = str(e)
                if verbose and attempt < max_retries - 1:
                    print(f"  Player {player_idx} bid error: {e} (retry {attempt + 1}/{max_retries})")
                continue

        # Max retries exceeded - auto pass
        if verbose:
            print(f"  Player {player_idx} failed to provide valid bid after {max_retries} attempts, passing. Last error: {last_error}")
        return PlayerAction.auction_bid_pass()

    def execute_plant_purchase(self, player_idx, plant, bid_amount, discard_card, verbose):
        """Execute a plant purchase after auction completes

        Args:
            player_idx: Winner of the auction
            plant: Plant purchased
            bid_amount: Final bid amount
            discard_card: Card to discard (None if player has < 3 plants)
            verbose: Whether to print progress

        This method:
        1. Adds plant to player's cards
        2. Deducts money
        3. Discards specified plant if provided
        4. Removes excess resources after discard
        5. Removes plant from market
        6. Updates market
        """
        player = self.players[player_idx]

        # Add plant and pay
        player.cards.append(plant)
        player.update_money(-bid_amount)

        if verbose:
            print(f"Player {player_idx} bought plant {plant.cost} for {bid_amount}E")

        # Discard specified plant if player had 3
        if discard_card is not None:
            if discard_card in player.cards:
                player.cards.remove(discard_card)
                if verbose:
                    print(f"  Discarded plant {discard_card.cost}")

                # Remove resources that exceed new capacity
                self.remove_excess_resources(player, verbose)
            else:
                # This shouldn't happen if validation worked
                if verbose:
                    print(f"  WARNING: Discard card {discard_card.cost} not found in player's cards")

        # Remove from market
        if plant in self.game_state.current_market:
            self.game_state.current_market.remove(plant)

        # Update market
        self.update_market_after_purchase()
        
        # Debug: Show market after update
        if verbose:
            print(f"  After market update - Current: {[p.cost for p in self.game_state.current_market]}, Future: {[p.cost for p in self.game_state.future_market]}")

        # Log state
        if self.enable_logging:
            self.logger.log_state(self.game_state,
                description=f"round_{self.game_state.round_num}_player_{player_idx}_bought_plant_{plant.cost}")

    def draw_next_plant(self):
        if not self.game_state.deck:
            return None

        plant = self.game_state.deck.pop(0)
        # Check for Step 3 card
        if hasattr(plant, 'resource') and plant.resource == 'stage three':
            self.game_state.step_3_triggered = True
            if self.game_state.deck:
                return self.game_state.deck.pop(0)
            return None
        return plant
    
    def update_market_after_purchase(self):
        """Update power plant market after a purchase

        Maintains proper market structure:
        - Step 3: 6 plants total (no current/future split)
        - Steps 1 & 2: 4 lowest in current market, 4 highest in future market
        """
        # If in Step 3, market should have 6 plants total (no separation)
        if self.game_state.step == 3:
            # Combine markets and keep 6 smallest
            all_plants = self.game_state.current_market + self.game_state.future_market

            # Fill from deck if needed
            while len(all_plants) < 6:
                new_plant = self.draw_next_plant()
                if new_plant:
                    all_plants.append(new_plant)
                else:
                    break

            # Sort and keep only 6 smallest
            all_plants.sort(key=lambda c: c.cost)
            if len(all_plants) > 6:
                # Remove excess (largest) back to deck
                excess = all_plants[6:]
                self.game_state.deck.extend(excess)
                all_plants = all_plants[:6]

            self.game_state.current_market = all_plants
            self.game_state.future_market = []
        else:
            # Steps 1 & 2: Combine, fill, sort, then split into 4 current + 4 future
            all_plants = self.game_state.current_market + self.game_state.future_market

            # IMPORTANT: In Round 1, do NOT draw from deck - only use the initial 9 dark cards
            # Only draw from deck starting in Round 2
            if self.game_state.round_num > 1:
                # Fill from deck until we have 9 plants (only after round 1)
                while len(all_plants) < 9:
                    new_plant = self.draw_next_plant()
                    if new_plant:
                        all_plants.append(new_plant)
                    else:
                        break

            # Sort all plants by cost
            all_plants.sort(key=lambda c: c.cost)

            # Split: 4 lowest go to current market, rest to future market
            self.game_state.current_market = all_plants[:4]
            self.game_state.future_market = all_plants[4:]

            # If we have more than 9 total (shouldn't happen in round 1), move largest from future to bottom of deck
            while len(self.game_state.future_market) > 5:
                largest = self.game_state.future_market.pop()
                self.game_state.deck.append(largest)
    
    def phase_3_buy_resources(self, verbose):
        """Phase 3: Buy resources (reverse player order)"""
        # Reverse order
        buy_order = list(reversed(self.game_state.player_order))

        for player_idx in buy_order:
            player = self.players[player_idx]
            strategy = player.strategy

            if strategy is None:
                raise ValueError(f"Player {player_idx} ({player.name}) has no strategy assigned")

            # Get player's resource purchase action
            action = strategy.choose_resources(player, self.game_state)

            # Validate action type
            if not isinstance(action, PlayerAction):
                raise ValueError(f"Player {player_idx} strategy must return PlayerAction object")
            if action.action_type != ActionType.RESOURCE_PURCHASE:
                raise ValueError(f"Player {player_idx} returned wrong action type: {action.action_type.value}, expected RESOURCE_PURCHASE")

            if action.resources:
                for resource_type, amount in action.resources.items():
                    if amount > 0 and resource_type in self.game_state.resources:
                        # First check capacity and plant ownership
                        if not self.validate_resource_purchase(player, resource_type, amount):
                            continue

                        # Get the cost before purchasing
                        resource = self.game_state.resources[resource_type]
                        purchase_result = resource.buy_resource(amount)

                        if isinstance(purchase_result, tuple):
                            cost = purchase_result[1]

                            # Validate player has enough money
                            if cost > player.money:
                                if verbose:
                                    print(f"Player {player_idx}: Cannot afford {amount} {resource_type} (costs {cost}E, only has {player.money}E)")
                                # Return the resources to the market
                                resource.resupply(amount)
                                continue

                            # Execute purchase
                            player.update_money(-cost)
                            player.resources[resource_type] += amount
                            if verbose:
                                print(f"Player {player_idx} bought {amount} {resource_type} for {cost}E")

                            # Log state after resource purchase
                            if self.enable_logging:
                                self.logger.log_state(self.game_state,
                                    description=f"round_{self.game_state.round_num}_player_{player_idx}_bought_{amount}_{resource_type}")
        
        self.game_state.phase = 'build'
    
    def validate_resource_purchase(self, player, resource_type, amount):
        """Validate that player can buy this resource"""
        # Check if player owns plants using this resource type
        has_plant = False
        total_capacity = 0
        
        for card in player.cards:
            if card.resource == resource_type:
                has_plant = True
                total_capacity += card.resource_cost * 2  # Can store 2x capacity
            elif card.resource == 'oil&gas' and resource_type in ['oil', 'gas']:
                has_plant = True
                total_capacity += card.resource_cost * 2  # Hybrid: total capacity
        
        if not has_plant:
            return False
        
        # Check capacity
        current_amount = player.resources.get(resource_type, 0)
        if current_amount + amount > total_capacity:
            return False
        
        return True

    def remove_excess_resources(self, player, verbose=False):
        """Remove resources that exceed capacity after discarding a power plant

        When a player discards a power plant, they may have more resources than
        their remaining plants can store. This method removes the excess.
        """
        # Calculate current capacity for each resource type
        capacities = {'coal': 0, 'oil': 0, 'gas': 0, 'uranium': 0}

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                capacities['uranium'] += card.resource_cost * 2
            elif resource_type == 'oil&gas':
                # Hybrid plants can store oil OR gas (total capacity is shared)
                capacities['oil'] += card.resource_cost * 2
                capacities['gas'] += card.resource_cost * 2
            elif resource_type in ['coal', 'oil', 'gas']:
                capacities[resource_type] += card.resource_cost * 2

        # Remove excess resources
        for resource_type in ['coal', 'oil', 'gas', 'uranium']:
            current = player.resources.get(resource_type, 0)
            max_capacity = capacities[resource_type]

            if current > max_capacity:
                excess = current - max_capacity
                player.resources[resource_type] = max_capacity
                if verbose:
                    print(f"  Removed {excess} {resource_type} (exceeded capacity)")

    def phase_4_build(self, verbose):
        """Phase 4: Build generators (reverse player order)"""
        # Reverse order
        build_order = list(reversed(self.game_state.player_order))

        # First round: all players must build at least one city
        is_first_round = (self.game_state.round_num == 1)

        for player_idx in build_order:
            player = self.players[player_idx]
            strategy = player.strategy

            if strategy is None:
                raise ValueError(f"Player {player_idx} ({player.name}) has no strategy assigned")

            # Get city building action
            action = strategy.choose_cities_to_build(player, self.game_state)

            # Validate action type
            if not isinstance(action, PlayerAction):
                raise ValueError(f"Player {player_idx} strategy must return PlayerAction object")
            if action.action_type != ActionType.CITY_BUILD:
                raise ValueError(f"Player {player_idx} returned wrong action type: {action.action_type.value}, expected CITY_BUILD")

            if action.cities:
                for city_name in action.cities:
                    if city_name in self.game_state.city_occupancy:
                        # Check if player already has a generator in this city
                        if city_name in player.generators:
                            if verbose:
                                print(f"Player {player_idx}: Already owns a generator in {city_name}")
                            continue

                        # Calculate cost
                        position = len(self.game_state.city_occupancy[city_name])
                        if position == 3:
                            print(f"{city_name} is full")
                            continue
                        building_cost = [10, 15, 20][position]
                        connection_cost = self.calculate_connection_cost(
                            player_idx, city_name
                        )
                        total_cost = building_cost + connection_cost

                        # Check if affordable and valid
                        # Step 1: position < 1 (1 player), Step 2: position < 2 (2 players), Step 3: position < 3 (3 players)
                        if player.money >= total_cost and position < self.game_state.step:
                            player.update_money(-total_cost)
                            player.generators.append(city_name)
                            self.game_state.city_occupancy[city_name].append(player_idx)

                            if verbose:
                                print(f"Player {player_idx} built in {city_name} for {total_cost}E (building: {building_cost}E, connection: {connection_cost}E)")

                            # Log state after building
                            if self.enable_logging:
                                self.logger.log_state(self.game_state,
                                    description=f"round_{self.game_state.round_num}_player_{player_idx}_built_in_{city_name}")

                            # Check if game should end immediately (player reached threshold)
                            threshold = 17 if self.num_players == 4 else 18
                            if len(player.generators) >= threshold:
                                if verbose:
                                    print(f"\nPlayer {player_idx} reached {threshold} cities! Game ending immediately.")
                                if self.enable_logging:
                                    self.logger.log_state(self.game_state, description="game_end_condition_triggered")
                                self.game_state.game_over = True
                                return  # End build phase immediately

                        # Check if any plant should be removed (plant number <= cities)
                        self.remove_plants_below_city_count(player_idx)
        
        self.game_state.phase = 'bureaucracy'
    
    def calculate_connection_cost(self, player_idx, target_city):
        """Calculate shortest path connection cost"""
        player = self.players[player_idx]
        
        if not player.generators:
            return 0  # First city is free
        
        # Find shortest path from any existing city to target
        min_cost = float('inf')
        
        # Convert graph format
        graph = {}
        for node1, connections in self.game_state.board_graph.items():
            city1 = node1[1] if isinstance(node1, tuple) else node1
            graph[city1] = {}
            for node2, cost in connections.items():
                city2 = node2[1] if isinstance(node2, tuple) else node2
                graph[city1][city2] = cost
        
        # Simple shortest path (Dijkstra-like, simplified)
        for start_city in player.generators:
            if start_city in graph and target_city in graph:
                # Direct connection
                if target_city in graph.get(start_city, {}):
                    cost = graph[start_city][target_city]
                    min_cost = min(min_cost, cost)
                else:
                    # Try 2-hop paths (simplified)
                    for intermediate in graph.get(start_city, {}):
                        if target_city in graph.get(intermediate, {}):
                            cost = graph[start_city][intermediate] + graph[intermediate][target_city]
                            min_cost = min(min_cost, cost)
        
        # If no path found, use a default high cost
        if min_cost == float('inf'):
            min_cost = 50  # Default high cost
        
        return int(min_cost)
    
    def remove_plants_below_city_count(self, player_idx):
        """Remove plants from market if plant number <= any player's city count"""
        player = self.players[player_idx]
        city_count = len(player.generators)
        
        # Check all players for max city count
        max_cities = max([len(p.generators) for p in self.players])
        
        # Check current market
        to_remove = []
        for plant in self.game_state.current_market:
            if plant.cost <= max_cities:
                to_remove.append(plant)
        
        for plant in to_remove:
            self.game_state.current_market.remove(plant)
            new_plant = self.draw_next_plant()
            if new_plant:
                self.game_state.current_market.append(new_plant)
        
        self.game_state.current_market.sort(key=lambda c: c.cost)
    
    def phase_5_bureaucracy(self, verbose):
        """Phase 5: Bureaucracy - earn money, resupply, update market"""
        # 1. Earn money based on cities powered (and consume resources)
        for player_idx, player in enumerate(self.players):
            strategy = player.strategy

            if strategy is None:
                raise ValueError(f"Player {player_idx} ({player.name}) has no strategy assigned")

            # Get player's power action
            action = strategy.choose_cities_to_power(player, self.game_state)

            # Validate action type
            if not isinstance(action, PlayerAction):
                raise ValueError(f"Player {player_idx} strategy must return PlayerAction object")
            if action.action_type != ActionType.POWER_CITIES:
                raise ValueError(f"Player {player_idx} returned wrong action type: {action.action_type.value}, expected POWER_CITIES")

            # Extract power plan (int or detailed list)
            cities_to_power = action.power_plan
            if not isinstance(cities_to_power, int):
                # If detailed power plan provided, convert to int for now (simplified implementation)
                # TODO: Implement detailed power plan validation
                cities_to_power = len(cities_to_power) if cities_to_power else 0

            # Validate: can't power more cities than connected
            max_cities = len(player.generators)
            if cities_to_power > max_cities:
                if verbose:
                    print(f"Player {player_idx} tried to power {cities_to_power} cities but only has {max_cities} generators, limiting to {max_cities}")
                cities_to_power = max_cities

            # Validate: check if player has resources to power that many
            actual_powered = self.validate_and_power_cities(player, cities_to_power, verbose)

            payment = PAYMENT_TABLE.get(actual_powered, 0)
            player.update_money(payment)
            if verbose:
                print(f"Player {player_idx} powered {actual_powered} cities, earned {payment}E")
        
        # 2. Resupply resources
        step_idx = self.game_state.step - 1
        for resource_type, resource in self.game_state.resources.items():
            if resource_type in RESUPPLY_TABLES:
                resupply_amount = RESUPPLY_TABLES[resource_type][self.num_players][step_idx]
                resource.resupply(resupply_amount)
                if verbose:
                    print(f"Resupplied {resupply_amount} {resource_type}")
        
        # 3. Update power plant market
        if self.game_state.step == 1 or self.game_state.step == 2:
            # Steps 1 & 2: Place highest numbered power plant from future market on bottom of deck
            if self.game_state.future_market:
                largest = max(self.game_state.future_market, key=lambda c: c.cost)
                self.game_state.future_market.remove(largest)
                self.game_state.deck.append(largest)
                if verbose:
                    print(f"Moved plant {largest.cost} from future market to bottom of deck")

            # Draw a new plant to replace it
            new_plant = self.draw_next_plant()
            if new_plant:
                self.game_state.future_market.append(new_plant)
                self.game_state.future_market.sort(key=lambda c: c.cost)
                if verbose:
                    print(f"Drew plant {new_plant.cost} to future market")

        elif self.game_state.step == 3:
            # Step 3: Remove smallest numbered power plant from the game and replace it
            all_market_plants = self.game_state.current_market + self.game_state.future_market
            if all_market_plants:
                smallest = min(all_market_plants, key=lambda c: c.cost)

                # Remove from whichever market it's in
                if smallest in self.game_state.current_market:
                    self.game_state.current_market.remove(smallest)
                elif smallest in self.game_state.future_market:
                    self.game_state.future_market.remove(smallest)

                if verbose:
                    print(f"Removed smallest plant {smallest.cost} from game (Step 3)")

                # Draw a new plant to replace it
                new_plant = self.draw_next_plant()
                if new_plant:
                    # In Step 3, add to combined market and keep 6 smallest
                    all_plants = self.game_state.current_market + self.game_state.future_market
                    all_plants.append(new_plant)
                    all_plants.sort(key=lambda c: c.cost)
                    self.game_state.current_market = all_plants[:6]
                    self.game_state.future_market = []
                    if verbose:
                        print(f"Drew plant {new_plant.cost} to replace it")

        self.game_state.phase = 'determine_order'
    
    def validate_and_power_cities(self, player, requested_cities, verbose=False):
        """Validate player can power requested cities and consume resources

        Returns: Number of cities actually powered (may be less than requested)
        """
        # Calculate maximum cities player can power with available resources
        max_possible = self.calculate_cities_powered(player)

        # Can't power more than possible
        cities_to_power = min(requested_cities, max_possible)

        if cities_to_power != requested_cities and verbose:
            print(f"  Requested {requested_cities} but can only power {cities_to_power} with available resources")

        # Consume resources
        self.consume_resources_for_power(player, cities_to_power)

        return cities_to_power

    def calculate_cities_powered(self, player):
        """Calculate how many cities a player can power (without consuming resources)"""
        cities_connected = len(player.generators)
        
        # Calculate total power from plants with resources
        total_power = 0
        
        for card in player.cards:
            if card.resource == 'green':
                # Ecological plants always work
                total_power += card.cities
            elif card.resource in ['coal', 'gas', 'oil', 'uranium']:
                # Check if player has enough resources
                resource_type = card.resource
                if resource_type == 'nuclear':
                    resource_type = 'uranium'
                available = player.resources.get(resource_type, 0)
                if available >= card.resource_cost:
                    total_power += card.cities
            elif card.resource == 'oil&gas':
                # Hybrid: can use oil or gas
                oil_available = player.resources.get('oil', 0)
                gas_available = player.resources.get('gas', 0)
                if oil_available + gas_available >= card.resource_cost:
                    total_power += card.cities
        
        # Can only power as many cities as connected
        return min(cities_connected, total_power)
    
    def consume_resources_for_power(self, player, cities_to_power):
        """Consume resources to power the specified number of cities"""
        if cities_to_power == 0:
            return
        
        # Sort plants by efficiency (cities per resource cost), prefer green
        plants_to_use = []
        for card in player.cards:
            if card.resource == 'green':
                plants_to_use.append((card, 'green', 0))
            else:
                resource_type = card.resource
                if resource_type == 'nuclear':
                    resource_type = 'uranium'
                available = player.resources.get(resource_type, 0) if resource_type != 'oil&gas' else (
                    player.resources.get('oil', 0) + player.resources.get('gas', 0)
                )
                if available >= card.resource_cost:
                    plants_to_use.append((card, resource_type, card.resource_cost))
        
        # Sort by efficiency (green first, then by cities/cost)
        plants_to_use.sort(key=lambda x: (x[1] != 'green', -x[0].cities / float(x[2] + 1)))
        
        # Use plants to power cities
        cities_powered = 0
        for card, resource_type, cost in plants_to_use:
            if cities_powered >= cities_to_power:
                break
            
            if resource_type == 'green':
                cities_powered += card.cities
            else:
                # Consume resources
                if resource_type == 'oil&gas':
                    # Use cheaper resource first
                    oil_avail = player.resources.get('oil', 0)
                    gas_avail = player.resources.get('gas', 0)
                    if oil_avail >= cost:
                        player.resources['oil'] -= cost
                        self.game_state.resources['oil'].use_resource(cost)
                    elif gas_avail >= cost:
                        player.resources['gas'] -= cost
                        self.game_state.resources['gas'].use_resource(cost)
                    else:
                        # Use combination
                        remaining = cost
                        if oil_avail > 0:
                            use_oil = min(remaining, oil_avail)
                            player.resources['oil'] -= use_oil
                            self.game_state.resources['oil'].use_resource(use_oil)
                            remaining -= use_oil
                        if remaining > 0:
                            player.resources['gas'] -= remaining
                            self.game_state.resources['gas'].use_resource(remaining)
                else:
                    player.resources[resource_type] -= cost
                    self.game_state.resources[resource_type].use_resource(cost)
                
                cities_powered += card.cities
    
    def check_step_transitions(self, verbose):
        """Check and handle step transitions"""
        # Step 1 -> Step 2
        if self.game_state.step == 1:
            threshold = STEP_2_THRESHOLDS.get(self.num_players, 7)
            for player in self.players:
                if len(player.generators) >= threshold:
                    self.game_state.step = 2
                    if verbose:
                        print(f"\nSTEP 2 TRIGGERED! (Player has {len(player.generators)} cities)")
                    # Europe: remove smallest plant, don't replace
                    if self.game_state.current_market:
                        smallest = min(self.game_state.current_market, key=lambda c: c.cost)
                        self.game_state.current_market.remove(smallest)
                        self.update_market_after_purchase()
                    break
        
        # Step 2 -> Step 3
        if self.game_state.step == 2 and self.game_state.step_3_triggered:
            self.game_state.step = 3
            if verbose:
                print("\nSTEP 3 TRIGGERED!")
            # Remove smallest plant
            if self.game_state.current_market:
                smallest = min(self.game_state.current_market, key=lambda c: c.cost)
                self.game_state.current_market.remove(smallest)
            # Combine markets (Step 3 has 6 plants total)
            all_plants = self.game_state.current_market + self.game_state.future_market
            all_plants.sort(key=lambda c: c.cost)
            self.game_state.current_market = all_plants[:6]
            self.game_state.future_market = []
    
    def check_end_game(self):
        """Check if game should end (17 cities for 4 players, 18 for others)"""
        # Game ends when a player reaches the threshold based on number of players
        # 4 players: 17 cities, 5-6 players: 18 cities
        threshold = 17 if self.num_players == 4 else 18
        
        for player in self.players:
            if len(player.generators) >= threshold:
                self.game_state.game_over = True
                return True
        return False
    
    def determine_winner(self):
        """Determine winner: most cities powered, tie-breaker: most money"""
        best_players = []
        best_powered = -1
        
        for player_idx, player in enumerate(self.players):
            cities_powered = self.calculate_cities_powered(player)
            if cities_powered > best_powered:
                best_powered = cities_powered
                best_players = [(player_idx, player)]
            elif cities_powered == best_powered:
                best_players.append((player_idx, player))
        
        # Tie-breaker: most money
        if len(best_players) > 1:
            best_players.sort(key=lambda x: x[1].money, reverse=True)
        
        return best_players[0][0]
    
    def print_final_scores(self, verbose):
        """Print final scores for all players"""
        if not verbose:
            return
        
        print("\nFinal Scores:")
        for player_idx, player in enumerate(self.players):
            cities_powered = self.calculate_cities_powered(player)
            cities_connected = len(player.generators)
            print(f"Player {player_idx}: {cities_powered} cities powered, {cities_connected} cities connected, {player.money}E")

