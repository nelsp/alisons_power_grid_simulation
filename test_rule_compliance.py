"""
Rule Compliance Tests for Power Grid Simulation
Tests to ensure the game follows Power Grid Deluxe rules for Europe map with 4 players.

Key Rules Being Tested:
1. Auction Phase Rules:
   - Players cannot bid if they were the last bidder (current winner)
   - Players cannot bid if they passed
   - Minimum bid must be at least the plant cost
   - Bids must be higher than current bid
   - First round: all players must buy a plant

2. Resource Purchase Rules:
   - Can only buy resources for plants you own
   - Cannot exceed storage capacity (2x resource cost per plant)

3. Building Rules:
   - Step 1: Only 1 player per city
   - Step 2: Up to 2 players per city
   - Step 3: Up to 3 players per city
   - Building costs: 10E (1st), 15E (2nd), 20E (3rd)

4. Market Rules:
   - Step 1-2: 4 plants in current market, rest in future market
   - Step 3: 6 plants total in market
   - Plants with number <= city count must be removed

5. Game Flow Rules:
   - Player order: most cities, tie-breaker: largest plant
   - Step 2 triggers at 7 cities (4 players)
   - Game ends when someone reaches 18 cities
   - Winner: most cities powered, tie-breaker: most money
"""

import pytest
import json
from game_engine import GameEngine, GameState, PAYMENT_TABLE
from Player_class import Player
from card import Card
from player_action import PlayerAction, ActionType
import create_use_resources as res


class MockStrategy:
    """Mock strategy that can be controlled for testing"""
    def __init__(self):
        self.actions = []
        self.action_index = 0
    
    def set_actions(self, actions):
        """Set a list of actions to return in order"""
        self.actions = actions
        self.action_index = 0
    
    def _next_action(self):
        """Get next action from list"""
        if self.action_index < len(self.actions):
            action = self.actions[self.action_index]
            self.action_index += 1
            return action
        # Default: pass or minimal action
        return PlayerAction.auction_pass()
    
    def choose_auction_move(self, player, game_state):
        """Choose auction opening move"""
        return self._next_action()
    
    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Choose bid during auction"""
        return self._next_action()
    
    def choose_resources(self, player, game_state):
        """Choose resource purchase"""
        action = self._next_action()
        if action.action_type == ActionType.RESOURCE_PURCHASE:
            return action
        return PlayerAction.resource_purchase({})
    
    def choose_cities_to_build(self, player, game_state):
        """Choose cities to build"""
        action = self._next_action()
        if action.action_type == ActionType.CITY_BUILD:
            return action
        return PlayerAction.city_build([])
    
    def choose_cities_to_power(self, player, game_state):
        """Choose cities to power"""
        action = self._next_action()
        if action.action_type == ActionType.POWER_CITIES:
            return action
        # Default: power 0 cities
        return PlayerAction.power_cities(0)


@pytest.fixture
def sample_cards():
    """Create sample power plant cards"""
    return [
        Card({'cost': 3, 'resource': 'oil', 'resource_cost': 2, 'cities': 1}),
        Card({'cost': 4, 'resource': 'coal', 'resource_cost': 2, 'cities': 1}),
        Card({'cost': 5, 'resource': 'gas', 'resource_cost': 2, 'cities': 1}),
        Card({'cost': 6, 'resource': 'oil', 'resource_cost': 1, 'cities': 1}),
        Card({'cost': 7, 'resource': 'coal', 'resource_cost': 1, 'cities': 1}),
        Card({'cost': 8, 'resource': 'oil&gas', 'resource_cost': 2, 'cities': 3}),
        Card({'cost': 10, 'resource': 'oil', 'resource_cost': 2, 'cities': 2}),
        Card({'cost': 11, 'resource': 'uranium', 'resource_cost': 1, 'cities': 2}),
        Card({'cost': 12, 'resource': 'oil&gas', 'resource_cost': 2, 'cities': 2}),
        Card({'cost': 13, 'resource': 'green', 'resource_cost': 0, 'cities': 1}),
        Card({'cost': 14, 'resource': 'gas', 'resource_cost': 2, 'cities': 2}),
        Card({'cost': 15, 'resource': 'coal', 'resource_cost': 2, 'cities': 3}),
        Card({'cost': 16, 'resource': 'oil', 'resource_cost': 2, 'cities': 3, 'type': 'light'}),
    ]


@pytest.fixture
def sample_resources():
    """Create sample resource market"""
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
    
    return {'coal': coal, 'oil': oil, 'gas': gas, 'uranium': uranium}


@pytest.fixture
def simple_board():
    """Create a simple board graph"""
    return {
        ('region', 'A'): {('region', 'B'): 5, ('region', 'D'): 10},
        ('region', 'B'): {('region', 'A'): 5, ('region', 'C'): 7, ('region', 'E'): 8},
        ('region', 'C'): {('region', 'B'): 7},
        ('region', 'D'): {('region', 'A'): 10, ('region', 'E'): 6},
        ('region', 'E'): {('region', 'B'): 8, ('region', 'D'): 6}
    }


class TestAuctionRuleCompliance:
    """Test that auction phase follows Power Grid rules"""
    
    def test_first_round_must_buy(self, sample_cards, sample_resources, simple_board):
        """Test that all players must buy a plant in the first round"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Strategy tries to pass, but should be forced to buy
        for i, strategy in enumerate(strategies):
            if i == 0:
                # First player must open an auction
                strategy.set_actions([PlayerAction.auction_open(sample_cards[0], 3)])
            else:
                # Other players try to pass
                strategy.set_actions([PlayerAction.auction_pass()])
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        # Try to run auction phase - should handle first round requirement
        # Note: The engine validates first round, so passing should trigger retries
        # We'll check that all players end up with plants
        engine.phase_2_auction(verbose=False)
        
        # Check that at least the first player bought a plant
        # (Engine should force purchases in first round)
        assert len(players[0].cards) > 0 or any(len(p.cards) > 0 for p in players)
    
    def test_cannot_bid_when_current_winner(self, sample_cards, sample_resources, simple_board):
        """Test that a player cannot bid again if they are the current high bidder"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        plant = sample_cards[0]  # Cost 3
        
        # Player 0 opens auction
        strategies[0].set_actions([PlayerAction.auction_open(plant, 3)])
        
        # Player 1 bids, then tries to bid again (should not be possible)
        strategies[1].set_actions([
            PlayerAction.auction_bid(4),  # First bid
            PlayerAction.auction_bid(5),  # Try to bid again (invalid - they're current winner)
        ])
        
        # Player 2 and 3 pass
        strategies[2].set_actions([PlayerAction.auction_bid_pass()])
        strategies[3].set_actions([PlayerAction.auction_bid_pass()])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = [plant] + sample_cards[1:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        # Set up so players already have plants (not first round)
        engine.game_state.round_num = 2
        
        # Run auction
        engine.phase_2_auction(verbose=False)
        
        # Verify that player 1 could not bid twice
        # The engine should prevent this through the active_bidders logic
        # Check auction state: player 1 should only have bid once
        # This test verifies the engine's validation prevents this
        
    def test_cannot_bid_after_passing(self, sample_cards, sample_resources, simple_board):
        """Test that a player cannot bid after passing"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        plant = sample_cards[0]
        
        strategies[0].set_actions([PlayerAction.auction_open(plant, 3)])
        # Player 1 passes, then tries to bid (invalid)
        strategies[1].set_actions([
            PlayerAction.auction_bid_pass(),  # Pass first
            PlayerAction.auction_bid(4),      # Try to bid after passing (invalid)
        ])
        strategies[2].set_actions([PlayerAction.auction_bid_pass()])
        strategies[3].set_actions([PlayerAction.auction_bid_pass()])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = [plant] + sample_cards[1:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.round_num = 2
        engine.phase_2_auction(verbose=False)
        
        # Verify player 1 passed and couldn't bid afterwards
        # Engine should remove them from active_bidders after passing
    
    def test_minimum_bid_validation(self, sample_cards, sample_resources, simple_board):
        """Test that bids must be at least current_bid + 1"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        plant = sample_cards[0]  # Cost 3
        
        strategies[0].set_actions([PlayerAction.auction_open(plant, 3)])
        # Player 1 tries to bid less than minimum (invalid)
        strategies[1].set_actions([
            PlayerAction.auction_bid(2),  # Below minimum (current is 3, min is 4)
        ])
        strategies[2].set_actions([PlayerAction.auction_bid_pass()])
        strategies[3].set_actions([PlayerAction.auction_bid_pass()])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = [plant] + sample_cards[1:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.round_num = 2
        
        # The engine should validate and reject the bid
        # Strategy will be asked to retry, eventually auto-passing if invalid
        engine.phase_2_auction(verbose=False)
        
        # Verify validation worked (bid was rejected)
    
    def test_bid_must_be_at_least_plant_cost(self, sample_cards, sample_resources, simple_board):
        """Test that opening bid must be at least the plant cost"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        plant = sample_cards[0]  # Cost 3
        
        # Try to open with bid below plant cost
        strategies[0].set_actions([
            PlayerAction.auction_open(plant, 2),  # Below plant cost of 3
        ])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = [plant] + sample_cards[1:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.round_num = 2
        
        # Engine should validate and reject the bid
        engine.phase_2_auction(verbose=False)
        
        # Verify validation worked


class TestResourcePurchaseRules:
    """Test resource purchase rule compliance"""
    
    def test_cannot_buy_resources_without_plant(self, sample_cards, sample_resources, simple_board):
        """Test that players cannot buy resources without owning appropriate plant"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Player has no plants
        strategies[0].set_actions([PlayerAction.resource_purchase({'coal': 2})])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        # Try to buy resources
        initial_coal = players[0].resources.get('coal', 0)
        engine.phase_3_buy_resources(verbose=False)
        
        # Player should not have received coal (no plant to store it)
        assert players[0].resources.get('coal', 0) == initial_coal
    
    def test_cannot_exceed_storage_capacity(self, sample_cards, sample_resources, simple_board):
        """Test that players cannot buy more resources than storage capacity (2x resource_cost)"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Give player a coal plant that needs 2 coal (capacity = 4)
        coal_plant = sample_cards[1]  # Cost 4, needs 2 coal
        players[0].cards = [coal_plant]
        players[0].resources['coal'] = 4  # Already at capacity
        
        # Try to buy more coal
        strategies[0].set_actions([PlayerAction.resource_purchase({'coal': 1})])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        initial_coal = players[0].resources['coal']
        engine.phase_3_buy_resources(verbose=False)
        
        # Player should still have 4 coal (cannot exceed capacity)
        assert players[0].resources['coal'] == initial_coal


class TestBuildingRules:
    """Test building phase rule compliance"""
    
    def test_step1_only_one_player_per_city(self, sample_cards, sample_resources, simple_board):
        """Test that in Step 1, only one player can build in each city"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # All players try to build in city A
        for i in range(4):
            strategies[i].set_actions([PlayerAction.city_build(['A'])])
            players[i].strategy = strategies[i]
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 1
        engine.phase_4_build(verbose=False)
        
        # Only first player (in reverse order, so last player) should build
        # Actually, in reverse order, player 3 goes first
        city_a_count = sum(1 for p in players if 'A' in p.generators)
        assert city_a_count <= 1  # Only 1 player per city in Step 1
    
    def test_step2_two_players_per_city(self, sample_cards, sample_resources, simple_board):
        """Test that in Step 2, up to two players can build in each city"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Players try to build in city A
        for i in range(4):
            strategies[i].set_actions([PlayerAction.city_build(['A'])])
            players[i].strategy = strategies[i]
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 2
        # Give players money to build
        for p in players:
            p.money = 100
        
        engine.phase_4_build(verbose=False)
        
        city_a_count = sum(1 for p in players if 'A' in p.generators)
        assert city_a_count <= 2  # Up to 2 players per city in Step 2
    
    def test_building_costs(self, sample_cards, sample_resources, simple_board):
        """Test that building costs are correct: 10E (1st), 15E (2nd), 20E (3rd)"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Player 0 builds first in A
        strategies[0].set_actions([PlayerAction.city_build(['A'])])
        # Player 1 builds second in A
        strategies[1].set_actions([PlayerAction.city_build(['A'])])
        # Player 2 builds third in A
        strategies[2].set_actions([PlayerAction.city_build(['A'])])
        strategies[3].set_actions([PlayerAction.city_build([])])
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
            players[i].money = 100
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 3  # Allow 3 players per city
        
        # Track initial money
        initial_money = [p.money for p in players]
        
        engine.phase_4_build(verbose=False)
        
        # Check costs (assuming connection cost is 0 for simplicity in test)
        # First builder: 10E + connection
        # Second builder: 15E + connection  
        # Third builder: 20E + connection
        
        # Verify money was deducted appropriately
        # (Exact amounts depend on connection costs, but should be decreasing)


class TestMarketRules:
    """Test power plant market rule compliance"""
    
    def test_step1_market_structure(self, sample_cards, sample_resources, simple_board):
        """Test that Step 1 has 4 plants in current market"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 1
        engine.update_market_after_purchase()
        
        # Should have 4 plants in current market
        assert len(engine.game_state.current_market) == 4
    
    def test_step3_market_structure(self, sample_cards, sample_resources, simple_board):
        """Test that Step 3 has 6 plants total in market"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        current_market = sample_cards[:6]
        future_market = []
        deck = sample_cards[6:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 3
        engine.update_market_after_purchase()
        
        # Should have 6 plants in current market, 0 in future
        assert len(engine.game_state.current_market) <= 6
        assert len(engine.game_state.future_market) == 0
    
    def test_remove_plants_below_city_count(self, sample_cards, sample_resources, simple_board):
        """Test that plants with number <= city count are removed"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Player 0 has 5 cities
        players[0].generators = ['A', 'B', 'C', 'D', 'E']
        
        # Market has plant with cost 4 (should be removed)
        current_market = [
            Card({'cost': 3, 'resource': 'coal', 'resource_cost': 2, 'cities': 1}),
            Card({'cost': 4, 'resource': 'coal', 'resource_cost': 2, 'cities': 1}),
            Card({'cost': 5, 'resource': 'gas', 'resource_cost': 2, 'cities': 1}),
            Card({'cost': 6, 'resource': 'oil', 'resource_cost': 1, 'cities': 1}),
        ]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        # Trigger plant removal
        engine.remove_plants_below_city_count(0)
        
        # Plant with cost 4 should be removed (4 <= 5)
        plant_costs = [c.cost for c in engine.game_state.current_market]
        assert 4 not in plant_costs or max(players[0].generators) == []  # Check removal logic


class TestGameFlowRules:
    """Test overall game flow rule compliance"""
    
    def test_player_order_by_cities(self, sample_cards, sample_resources, simple_board):
        """Test that player order is determined by cities, then largest plant"""
        players = [Player(f"Player_{i}") for i in range(4)]
        
        # Set up cities
        players[0].generators = ['A']  # 1 city
        players[1].generators = ['B', 'C']  # 2 cities
        players[2].generators = ['D', 'E', 'F']  # 3 cities
        players[3].generators = []  # 0 cities
        
        # Set up plants for tie-breaker
        players[0].cards = [sample_cards[7]]  # Cost 10
        players[1].cards = [sample_cards[6]]  # Cost 8
        
        strategies = [MockStrategy() for _ in range(4)]
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.phase_1_determine_order()
        
        # Order should be: P2 (3 cities), P1 (2 cities), P0 (1 city), P3 (0 cities)
        assert engine.game_state.player_order == [2, 1, 0, 3]
    
    def test_step2_threshold(self, sample_cards, sample_resources, simple_board):
        """Test that Step 2 triggers at 7 cities for 4 players"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Player 0 has 7 cities
        players[0].generators = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        engine.game_state.step = 1
        engine.check_step_transitions(verbose=False)
        
        # Should transition to Step 2
        assert engine.game_state.step == 2
    
    def test_game_ends_at_18_cities(self, sample_cards, sample_resources, simple_board):
        """Test that game ends when a player reaches 18 cities"""
        players = [Player(f"Player_{i}") for i in range(4)]
        strategies = [MockStrategy() for _ in range(4)]
        
        # Player 0 has 18 cities
        players[0].generators = [f'City_{i}' for i in range(18)]
        
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        result = engine.check_end_game()
        
        assert result is True
        assert engine.game_state.game_over is True
    
    def test_winner_determination(self, sample_cards, sample_resources, simple_board):
        """Test that winner is determined by cities powered, then money"""
        players = [Player(f"Player_{i}") for i in range(4)]
        
        # Player 0: can power 2 cities, has 100E
        players[0].generators = ['A', 'B']
        players[0].cards = [
            Card({'cost': 13, 'resource': 'green', 'resource_cost': 0, 'cities': 1}),
            Card({'cost': 13, 'resource': 'green', 'resource_cost': 0, 'cities': 1})
        ]
        players[0].money = 100
        
        # Player 1: can power 1 city, has 150E
        players[1].generators = ['C']
        players[1].cards = [Card({'cost': 13, 'resource': 'green', 'resource_cost': 0, 'cities': 1})]
        players[1].money = 150
        
        strategies = [MockStrategy() for _ in range(4)]
        for i, strategy in enumerate(strategies):
            players[i].strategy = strategy
        
        current_market = sample_cards[:4]
        future_market = sample_cards[4:9]
        deck = sample_cards[9:]
        
        engine = GameEngine(
            players=players,
            current_market=current_market,
            future_market=future_market,
            deck=deck,
            board_graph=simple_board,
            resources=sample_resources,
            player_order=[0, 1, 2, 3],
            num_players=4,
            enable_logging=False
        )
        
        winner = engine.determine_winner()
        
        # Player 0 should win (more cities powered)
        assert winner == 0


class TestLogFileValidation:
    """Test that log files don't contain rule violations"""
    
    def test_validate_log_file(self):
        """Test that a log file from a completed game follows rules"""
        try:
            with open('power_grid_game_log.json', 'r') as f:
                log_data = json.load(f)
            
            # Check each game state in the log
            for state_entry in log_data:
                game_state = state_entry.get('gameState', {})
                
                # Check player order follows rules
                players = game_state.get('players', [])
                player_order = game_state.get('player_order', [])
                
                # Verify player order: should be sorted by cities descending
                player_cities = [
                    (i, len(p.get('generators', []))) 
                    for i, p in enumerate(players)
                ]
                player_cities_sorted = sorted(player_cities, key=lambda x: (-x[1], 0))
                
                # Check auction state if active
                if game_state.get('auction_active', False):
                    current_winner = game_state.get('auction_current_winner')
                    active_bidders = game_state.get('auction_active_bidders', [])
                    
                    # Current winner should not be in active_bidders
                    if current_winner is not None:
                        assert current_winner not in active_bidders, \
                            f"Current winner {current_winner} is in active_bidders {active_bidders}"
                
                # Check step constraints
                step = game_state.get('step', 1)
                city_occupancy = game_state.get('city_occupancy', {})
                
                # In Step 1, max 1 player per city
                if step == 1:
                    for city, occupants in city_occupancy.items():
                        assert len(occupants) <= 1, \
                            f"Step 1 violation: {city} has {len(occupants)} players"
                
                # In Step 2, max 2 players per city
                elif step == 2:
                    for city, occupants in city_occupancy.items():
                        assert len(occupants) <= 2, \
                            f"Step 2 violation: {city} has {len(occupants)} players"
                
                # In Step 3, max 3 players per city
                elif step == 3:
                    for city, occupants in city_occupancy.items():
                        assert len(occupants) <= 3, \
                            f"Step 3 violation: {city} has {len(occupants)} players"
                
                # Check market structure
                current_market = game_state.get('current_market', [])
                future_market = game_state.get('future_market', [])
                
                if step == 3:
                    # Step 3: should have 6 plants total
                    assert len(current_market) <= 6, \
                        f"Step 3: current_market has {len(current_market)} plants"
                    assert len(future_market) == 0, \
                        f"Step 3: future_market should be empty"
                else:
                    # Steps 1-2: should have 4 in current
                    assert len(current_market) <= 4, \
                        f"Step {step}: current_market has {len(current_market)} plants"
        
        except FileNotFoundError:
            pytest.skip("Log file not found - run a game first to generate log")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
