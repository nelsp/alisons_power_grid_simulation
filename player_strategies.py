"""
Test Player Strategies for Power Grid
Each strategy implements methods to make game decisions
"""

import random
from abc import ABC, abstractmethod
from player_action import PlayerAction, ActionType


class Strategy(ABC):
    """Base strategy interface that all player strategies must implement

    The game engine expects all strategies to provide these four methods.
    Each method is called during its respective phase of the game.
    """

    @abstractmethod
    def choose_auction_move(self, player, game_state):
        """Choose whether to open an auction and on which plant (Phase 2: Auction)

        The strategy should determine from game_state:
        - Available plants: game_state.current_market
        - Whether must buy: game_state.round_num == 1
        - Affordability: player.money vs plant.cost
        - Plant limit: len(player.cards) < 3 or need to specify discard

        Args:
            player: The player making the decision
            game_state: Current game state (contains current_market, round_num, etc.)

        Returns:
            PlayerAction with action_type AUCTION_PASS or AUCTION_OPEN
        """
        pass

    @abstractmethod
    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Respond to someone else's auction opening (Phase 2: Auction)

        The strategy should determine from parameters:
        - Minimum bid: current_bid + 1
        - Maximum bid: player.money
        - Whether to discard: len(player.cards) >= 3
        - Current winner: Who you're bidding against (important for strategic decisions)

        Args:
            player: The player making the decision
            game_state: Current game state
            plant: Plant being auctioned
            current_bid: Current highest bid to beat
            current_winner: Player index of current high bidder (critical strategic info)

        Returns:
            PlayerAction with action_type AUCTION_BID_PASS or AUCTION_BID
        """
        pass

    @abstractmethod
    def choose_resources(self, player, game_state):
        """Choose which resources to purchase (Phase 3: Buy Resources)

        The strategy should determine from game_state:
        - Available resources: game_state.resources (dict of resource_type -> Resource object)
        - Capacity limits: player.cards resource requirements
        - Affordability: player.money vs resource costs

        Args:
            player: The player making the decision
            game_state: Current game state (contains resources dict)

        Returns:
            PlayerAction with action_type RESOURCE_PURCHASE
        """
        pass

    @abstractmethod
    def choose_cities_to_build(self, player, game_state):
        """Choose which cities to build generators in (Phase 4: Build)

        The strategy should determine from game_state:
        - Must build: Check if any player built this round (game engine will validate)
        - Available cities: game_state.city_occupancy (check occupancy < step)
        - Connection costs: game_state.board_graph
        - Other players: game_state.players (for end-game optimization)

        Args:
            player: The player making the decision
            game_state: Current game state (contains city_occupancy, board_graph, players)

        Returns:
            PlayerAction with action_type CITY_BUILD
        """
        pass

    @abstractmethod
    def choose_cities_to_power(self, player, game_state):
        """Choose which plants to use and how many cities to power (Phase 5: Bureaucracy)

        The strategy specifies which power plants to use and which resources to consume.
        The game engine validates this selection and awards payment.

        The strategy should determine:
        - Which plants to activate (must have required resources)
        - Resource allocation for hybrid plants (oil&gas)
        - How many cities to power (limited by generators built)
        - Trade-off between earning money now vs saving resources

        Args:
            player: The player making the decision
            game_state: Current game state

        Returns:
            PlayerAction with action_type POWER_CITIES
            power_plan can be either:
            - int: Number of cities to power (engine picks plants greedily)
            - list: Detailed power plan [{'plant': Card, 'resources': {'coal': 2}}, ...]
        """
        pass


class StrategyUtils:
    """Common utility functions for all strategies"""

    @staticmethod
    def get_available_cities(player, game_state):
        """Get cities player can build in (not already owned, has space for current step)"""
        available = []
        for city_name, occupancy in game_state.city_occupancy.items():
            # Check player doesn't already own a generator here
            if city_name in player.generators:
                continue

            # Check if there's space based on current game step
            position = len(occupancy)
            if position < game_state.step:
                available.append(city_name)

        return available

    @staticmethod
    def calculate_city_cost(player, city_name, game_state):
        """Calculate total cost to build in a city (building + connection)"""
        # Building cost based on position
        position = len(game_state.city_occupancy[city_name])
        building_cost = [10, 15, 20][position] if position < 3 else 999

        # Connection cost
        connection_cost = StrategyUtils.estimate_connection_cost(player, city_name, game_state)

        return building_cost + connection_cost

    @staticmethod
    def estimate_connection_cost(player, city_name, game_state):
        """Estimate connection cost to a city"""
        if not player.generators:
            return 0  # First city is free

        # Find shortest path from any existing city
        min_cost = float('inf')

        # Convert graph format
        graph = {}
        for node1, connections in game_state.board_graph.items():
            city1 = node1[1] if isinstance(node1, tuple) else node1
            graph[city1] = {}
            for node2, cost in connections.items():
                city2 = node2[1] if isinstance(node2, tuple) else node2
                graph[city1][city2] = cost

        # Check direct connections from owned cities
        for start_city in player.generators:
            if start_city in graph and city_name in graph.get(start_city, {}):
                cost = graph[start_city][city_name]
                min_cost = min(min_cost, cost)
            else:
                # Try 2-hop paths (simplified pathfinding)
                for intermediate in graph.get(start_city, {}):
                    if city_name in graph.get(intermediate, {}):
                        cost = graph[start_city][intermediate] + graph[intermediate][city_name]
                        min_cost = min(min_cost, cost)

        # If no path found, use high default cost
        if min_cost == float('inf'):
            min_cost = 50

        return int(min_cost)

    @staticmethod
    def get_resource_capacities(player):
        """Calculate total capacity for each resource type based on owned plants"""
        capacities = {'coal': 0, 'oil': 0, 'gas': 0, 'uranium': 0}

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                capacities['uranium'] += card.resource_cost * 2
            elif resource_type == 'oil&gas':
                # Hybrid plants: can store oil OR gas (total capacity shared)
                capacities['oil'] += card.resource_cost * 2
                capacities['gas'] += card.resource_cost * 2
            elif resource_type in capacities:
                capacities[resource_type] += card.resource_cost * 2

        return capacities

    @staticmethod
    def get_resource_cost(resource, amount):
        """Calculate cost to buy a certain amount of resource"""
        poss_purchases = resource.poss_purchases()
        return poss_purchases.get(amount, None)

    @staticmethod
    def get_affordable_plants(player, available_plants):
        """Get plants the player can afford and are valid to buy
        
        When player has 3 plants, they can only buy plants with cost > smallest owned plant.
        """
        affordable = [p for p in available_plants if player.money >= p.cost]
        
        # If player has 3 plants, must only consider plants better than smallest owned
        if len(player.cards) >= 3:
            smallest_owned = min(player.cards, key=lambda c: c.cost)
            affordable = [p for p in affordable if p.cost > smallest_owned.cost]
        
        return affordable

    @staticmethod
    def can_buy_plant(player):
        """Check if player can buy a plant
        
        Players can always buy a plant if they have money.
        If they have 3 plants, they must discard one (handled by get_affordable_plants).
        """
        return True  # Always can buy if there are valid plants available

    @staticmethod
    def has_game_ended_with_players(players):
        """Check if any player has 18 or more generators (game ending condition)"""
        return any(len(player.generators) >= 18 for player in players)

    @staticmethod
    def calculate_max_powered_cities(player):
        """Calculate maximum number of cities player can power with current resources

        Returns the number of cities that can be powered based on:
        - Available power plants (sorted by cities powered, descending)
        - Available resources to fuel those plants
        """
        if not player.cards:
            return 0

        # Sort plants by cities they can power (descending)
        plants = sorted(player.cards, key=lambda c: c.cities, reverse=True)

        # Track available resources
        available_resources = dict(player.resources)
        cities_powered = 0

        for plant in plants:
            resource_type = plant.resource

            # Green plants don't need resources
            if resource_type == 'green':
                cities_powered += plant.cities
                continue

            # Map nuclear to uranium
            if resource_type == 'nuclear':
                resource_type = 'uranium'

            # Handle hybrid plants
            if resource_type == 'oil&gas':
                # Can use oil OR gas, use whichever has more available
                oil_available = available_resources.get('oil', 0)
                gas_available = available_resources.get('gas', 0)

                if oil_available >= plant.resource_cost:
                    available_resources['oil'] -= plant.resource_cost
                    cities_powered += plant.cities
                elif gas_available >= plant.resource_cost:
                    available_resources['gas'] -= plant.resource_cost
                    cities_powered += plant.cities
                # If can't power, skip this plant
            else:
                # Regular plants
                if available_resources.get(resource_type, 0) >= plant.resource_cost:
                    available_resources[resource_type] -= plant.resource_cost
                    cities_powered += plant.cities
                # If can't power, skip this plant

        return cities_powered

    @staticmethod
    def get_max_powerable_cities(player):
        """Get maximum cities player can actually power (limited by generators)
        
        This is the minimum of:
        - Cities that can be powered with available resources
        - Cities where player has built generators
        
        Use this in choose_cities_to_power() to avoid requesting more than possible.
        """
        max_power = StrategyUtils.calculate_max_powered_cities(player)
        cities_connected = len(player.generators)
        return min(max_power, cities_connected)

    @staticmethod
    def can_end_game(player, available_cities, game_state):
        """Check if player can reach 18 generators and calculate how many they could power

        Returns:
            tuple: (can_reach_18, max_cities_can_power)
        """
        current_generators = len(player.generators)

        # Calculate how many more cities we can build
        cities_can_build = len(available_cities)
        max_generators = current_generators + cities_can_build

        # Check if we can reach 18
        can_reach_18 = max_generators >= 18

        # Calculate max cities we can power with current resources
        max_powered = StrategyUtils.calculate_max_powered_cities(player)

        return can_reach_18, max_powered


class RandomStrategy(Strategy):
    """Random strategy: makes random legal moves"""

    def choose_auction_move(self, player, game_state):
        """Choose a random plant to buy, or pass"""
        available_plants = game_state.current_market
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        if must_buy:
            affordable = StrategyUtils.get_affordable_plants(player, available_plants)
            if affordable:
                plant = random.choice(affordable)
                discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
                return PlayerAction.auction_open(plant, plant.cost, discard)
            else:
                return PlayerAction.auction_pass()  # Can't afford any
        elif random.random() > 0.3:
            affordable = StrategyUtils.get_affordable_plants(player, available_plants)
            if affordable:
                plant = random.choice(affordable)
                # Ensure bid doesn't exceed player's money
                max_bid = min(plant.cost + 10, player.money)
                bid = random.randint(plant.cost, max_bid)
                discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
                return PlayerAction.auction_open(plant, bid, discard)
        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Decide whether to bid in an ongoing auction"""
        min_bid = current_bid + 1
        max_bid = player.money

        # Random strategy: 50% chance to bid if can afford
        if min_bid <= max_bid and random.random() > 0.5:
            # Bid randomly between min and a bit higher
            max_willing = min(plant.cost + 5, max_bid)
            if max_willing >= min_bid:
                bid_amount = random.randint(min_bid, max_willing)
                discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
                return PlayerAction.auction_bid(bid_amount, discard)
        return PlayerAction.auction_bid_pass()
    
    def choose_resources(self, player, game_state):
        """Buy random resources for owned plants"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        # Try to buy resources for each plant
        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource based on what's available
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                # Check current total for this resource type
                current = player.resources.get(resource_type, 0)
                max_capacity = capacities[resource_type]

                # Don't exceed capacity
                space_available = max_capacity - current
                if space_available <= 0:
                    continue

                # Randomly decide how much to buy (up to capacity)
                desired = random.randint(0, min(space_available, card.resource_cost * 2))

                # Check if we already plan to buy this resource
                already_buying = purchases.get(resource_type, 0)

                # Make sure total purchase doesn't exceed capacity
                can_buy = max_capacity - current - already_buying
                amount_to_buy = min(desired, can_buy)

                if amount_to_buy > 0:
                    # Check if resource is available in market
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(amount_to_buy, available_amount)

                    if amount_to_buy > 0:
                        # Check affordability
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Choose random cities to build in"""
        available = StrategyUtils.get_available_cities(player, game_state)

        if not available:
            return PlayerAction.city_build([])

        # Check if game has ended (any player has 18+ generators)
        # If so, try to build to maximize powered cities
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            # must_build is determined by game rules, strategies handle it implicitly
            cities = self._build_for_end_game(player, game_state, available)
            return PlayerAction.city_build(cities)

        # Note: must_build requirement will be validated by game engine
        # Strategy just chooses cities based on current game state
        if len(player.generators) == 0 or random.random() < 0.7:
            # Must build at least one - choose cheapest affordable city
            affordable = []
            for city in available:
                cost = StrategyUtils.calculate_city_cost(player, city, game_state)
                if player.money >= cost:
                    affordable.append((city, cost))

            if affordable:
                # Pick random from affordable cities
                city, _ = random.choice(affordable)
                return PlayerAction.city_build([city])
            return PlayerAction.city_build([])
        else:
            # Optional building - 80% chance to try
            if random.random() > 0.2:
                # Build 1-3 cities randomly, respecting budget
                cities_to_build = []
                remaining_money = player.money

                # Shuffle available cities for random selection
                shuffled_cities = available[:]
                random.shuffle(shuffled_cities)

                max_cities = min(3, len(shuffled_cities))
                for city in shuffled_cities[:max_cities]:
                    cost = StrategyUtils.calculate_city_cost(player, city, game_state)
                    if remaining_money >= cost:
                        cities_to_build.append(city)
                        remaining_money -= cost

                return PlayerAction.city_build(cities_to_build)

        return PlayerAction.city_build([])

    def choose_cities_to_power(self, player, game_state):
        """Random: Power maximum cities possible"""
        # Simple strategy: always power as many as possible (limited by generators built)
        cities = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(cities)

    def _build_for_end_game(self, player, game_state, available):
        """Build cities to maximize powered cities when game is ending"""
        # Calculate how many cities we can currently power
        current_powered = StrategyUtils.calculate_max_powered_cities(player)

        # Build as many cities as we can afford, up to what we can power
        cities_to_build = []
        remaining_money = player.money
        target_cities = min(len(available), current_powered - len(player.generators))

        if target_cities <= 0:
            # Still try to build at least one if we have no generators
            target_cities = 1 if len(player.generators) == 0 else 0

        # Sort by cost and build cheapest first
        cities_with_cost = [(city, StrategyUtils.calculate_city_cost(player, city, game_state))
                           for city in available]
        cities_with_cost.sort(key=lambda x: x[1])

        for city, cost in cities_with_cost:
            if len(cities_to_build) >= target_cities:
                break
            if remaining_money >= cost:
                cities_to_build.append(city)
                remaining_money -= cost

        return cities_to_build


class GreedyStrategy(Strategy):
    """Greedy strategy: tries to expand and power many cities"""

    def choose_auction_move(self, player, game_state):
        """Buy plants that power many cities"""
        available_plants = game_state.current_market
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        if must_buy:
            # Choose plant that powers most cities
            best_plant = max(affordable, key=lambda p: p.cities)
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(best_plant, best_plant.cost, discard)

        # Prefer plants that power many cities
        affordable.sort(key=lambda p: p.cities, reverse=True)
        plant = affordable[0]
        bid = min(plant.cost + 5, player.money)
        discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
        return PlayerAction.auction_open(plant, bid, discard)

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Greedy: Bid aggressively on plants that power many cities"""
        min_bid = current_bid + 1
        max_bid = player.money

        # Want plants with high city count
        if plant.cities >= 4 and min_bid <= max_bid:
            # Willing to pay up to plant cost + cities
            max_willing = min(plant.cost + plant.cities, max_bid)
            if max_willing >= min_bid:
                bid_amount = min(min_bid + 2, max_willing)
                discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
                return PlayerAction.auction_bid(bid_amount, discard)
        elif plant.cities >= 3 and min_bid <= max_bid * 0.5:
            # Moderate interest
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_bid(min_bid, discard)
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Buy resources for all owned plants"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                current = player.resources.get(resource_type, 0)
                max_capacity = capacities[resource_type]
                needed = max_capacity - current

                if needed > 0:
                    # Check availability and affordability
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(needed, available_amount)

                    if amount_to_buy > 0:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build in as many cities as affordable"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        # Check if game has ended - maximize powered cities
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            current_powered = StrategyUtils.calculate_max_powered_cities(player)
            target_cities = min(len(available), current_powered - len(player.generators))
            if target_cities <= 0:
                target_cities = 1 if len(player.generators) == 0 else 0
        else:
            target_cities = len(available)  # Build as many as possible (greedy)

        cities_to_build = []
        budget = player.money

        # Sort by cost to build cheapest first
        cities_with_cost = [(city, StrategyUtils.calculate_city_cost(player, city, game_state))
                           for city in available]
        cities_with_cost.sort(key=lambda x: x[1])

        for city_name, total_cost in cities_with_cost:
            if len(cities_to_build) >= target_cities or budget <= 0:
                break

            if total_cost <= budget:
                cities_to_build.append(city_name)
                budget -= total_cost

        if player.generators == 0 and not cities_to_build and available:
            # Must build at least one, choose cheapest
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            cities_to_build = [city]

        return PlayerAction.city_build(cities_to_build)

    def choose_cities_to_power(self, player, game_state):
        """Greedy: Power maximum cities possible"""
        # Greedy strategy: always power as many as possible for maximum income (limited by generators built)
        cities = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(cities)


class ConservativeStrategy(Strategy):  # MyStrategy base - with fixes
    """Lag-behind strategy with endgame burst - FIXED to avoid sandbagging trap"""

    def __init__(self):
        self.lag_factor = 1  # Reduced from likely 2
        self.endgame_threshold = 17  # 4p Europe

    def choose_auction_move(self, player, game_state):
        """Conservative: Only buy when necessary or excellent value"""
        available_plants = game_state.current_market
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        # Must buy in round 1 - choose cheapest efficient plant
        if must_buy:
            # Prefer plants with good efficiency (cities per cost)
            best_plant = max(affordable, key=lambda p: p.cities / float(p.cost) if p.cost > 0 else 0)
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(best_plant, best_plant.cost, discard)

        # Conservative: Only buy if plant is very efficient and affordable
        # Look for plants with efficiency > 0.3 (cities/cost)
        efficient_plants = [p for p in affordable if p.cost > 0 and p.cities / float(p.cost) > 0.3]
        
        if not efficient_plants:
            return PlayerAction.auction_pass()

        # Choose most efficient plant, but bid conservatively (at cost)
        best_plant = max(efficient_plants, key=lambda p: p.cities / float(p.cost) if p.cost > 0 else 0)
        discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
        
        # Only bid if we have plenty of money (conservative)
        if player.money >= best_plant.cost * 2:
            return PlayerAction.auction_open(best_plant, best_plant.cost, discard)
        
        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Conservative: Only bid on very efficient plants"""
        min_bid = current_bid + 1
        max_bid = player.money

        if min_bid > max_bid:
            return PlayerAction.auction_bid_pass()

        # Only bid if plant is very efficient (cities per cost > 0.3)
        efficiency = plant.cities / float(plant.cost) if plant.cost > 0 else 0
        if efficiency < 0.3:
            return PlayerAction.auction_bid_pass()

        # Conservative: Only bid if we have plenty of money left
        # Don't bid if it would leave us with less than 2x the plant cost
        if max_bid < min_bid or player.money - min_bid < plant.cost * 2:
            return PlayerAction.auction_bid_pass()

        # Bid minimum to stay in, but only if very efficient
        if efficiency > 0.4:
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_bid(min_bid, discard)
        
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Conservative: Buy resources conservatively, just enough to power plants"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        # Buy resources for each plant, but conservatively
        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                current = player.resources.get(resource_type, 0)
                max_capacity = capacities[resource_type]
                space_available = max_capacity - current

                if space_available <= 0:
                    continue

                # Conservative: Buy just enough for one turn (resource_cost amount)
                already_buying = purchases.get(resource_type, 0)
                can_buy = max_capacity - current - already_buying
                desired = card.resource_cost  # Just buy what's needed for one turn
                amount_to_buy = min(desired, can_buy, space_available)

                if amount_to_buy > 0:
                    available_amount = resources[resource_type].count
                    if available_amount >= amount_to_buy:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build to lag behind, secure cheap areas; burst in endgame - FIXED"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        max_other = max(len(p.generators) for p in game_state.players if p != player)
        my_cities = len(player.generators)
        threshold = self.get_endgame_threshold(len(game_state.players))

        # FIXED: Proactive Step 2 trigger
        if game_state.step == 1 and game_state.round_num > 6 and my_cities < 7:
            to_build_count = max(0, 7 - my_cities)
            # Build cheapest to trigger
            cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
            cities_with_cost.sort(key=lambda x: x[1])
            to_build = [city for city, cost in cities_with_cost[:to_build_count] if player.money >= cost]
            return PlayerAction.city_build(to_build)

        if max_other >= threshold or my_cities >= threshold:
            return self.endgame_build(player, game_state, available)

        target = max(0, max_other - self.lag_factor)
        to_build_count = target - my_cities

        # Always build first if none
        if my_cities == 0:
            to_build_count = max(to_build_count, 1)

        # FIXED: Minimum expansion mid-game
        if player.money > 120 and my_cities < 8:
            to_build_count = max(to_build_count, 2)

        # FIXED: Lowered thresholds
        close_to_endgame = self.is_near_endgame(game_state)
        has_excess_money = player.money > 80
        if close_to_endgame or has_excess_money:
            plant_capacity = sum(c.cities for c in player.cards)
            target_cities = min(plant_capacity, threshold)
            to_build_count = max(to_build_count, target_cities - my_cities)

        # Cap: Higher late-game
        max_per_round = 12 if (has_excess_money or close_to_endgame) else 6
        to_build_count = min(to_build_count, len(available), max_per_round)

        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])  # Cheapest first

        to_build = []
        budget = player.money
        for city, cost in cities_with_cost:
            if len(to_build) >= to_build_count:
                break
            if cost <= budget:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)

    def choose_cities_to_power(self, player, game_state):
        """Power max unless saving for endgame - FIXED to always max"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(max_powerable)

    # FIXED Helpers
    def get_endgame_threshold(self, num_players):
        """Get endgame threshold based on number of players"""
        thresholds = {
            3: 21,
            4: 17,
            5: 15,
            6: 14
        }
        return thresholds.get(num_players, 17)  # Default to 17 for 4 players

    def is_near_endgame(self, game_state):
        max_cities = max(len(p.generators) for p in game_state.players)
        return max_cities >= 7  # Earlier trigger

    def endgame_build(self, player, game_state, available):
        threshold = self.get_endgame_threshold(len(game_state.players))
        my_capacity = sum(c.cities for c in player.cards)
        max_opp_capacity = max(sum(c.cities for c in p.cards) for p in game_state.players if p != player)

        target = threshold if my_capacity >= max_opp_capacity - 1 else threshold - 1  # FIXED: Looser

        current = len(player.generators)
        to_build_count = max(0, target - current)
        to_build_count = min(to_build_count, len(available), 12)  # FIXED: Higher cap

        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])

        to_build = []
        budget = player.money
        for city, cost in cities_with_cost:
            if len(to_build) >= to_build_count:
                break
            if budget >= cost:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)  # Return PlayerAction

    # [Keep other helpers like evaluate_plant, get_endgame_threshold, etc.]


class BalancedStrategy(Strategy):
    """Balanced strategy: tries to balance expansion and efficiency"""

    def choose_auction_move(self, player, game_state):
        """Buy efficient plants (cities per cost)"""
        available_plants = game_state.current_market
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        if must_buy:
            # Choose efficient plant
            best_plant = max(affordable, key=lambda p: p.cities / float(p.cost))
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(best_plant, best_plant.cost, discard)

        # Prefer efficient plants we can afford
        best_plant = max(affordable, key=lambda p: p.cities / float(p.cost))
        bid = min(best_plant.cost + 3, player.money)
        discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
        return PlayerAction.auction_open(best_plant, bid, discard)

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Balanced: Bid based on efficiency (cities per cost)"""
        min_bid = current_bid + 1
        max_bid = player.money

        efficiency = plant.cities / float(plant.cost) if plant.cost > 0 else 0

        # If plant is efficient (>0.15 cities per euro) and affordable
        if efficiency > 0.15 and min_bid <= max_bid:
            # Willing to pay up to a moderate amount over plant cost
            max_willing = min(plant.cost + int(plant.cities * 1.5), max_bid)
            if max_willing >= min_bid:
                # Bid moderately
                bid_amount = min(min_bid + 1, max_willing)
                discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
                return PlayerAction.auction_bid(bid_amount, discard)
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Buy resources efficiently"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                # Buy to 1.5x production capacity (safety margin but not full)
                target = int(card.resource_cost * 1.5)
                current = player.resources.get(resource_type, 0)
                max_capacity = capacities[resource_type]
                needed = min(target - current, max_capacity - current)

                if needed > 0:
                    # Check availability and affordability
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(needed, available_amount)

                    if amount_to_buy > 0:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build strategically"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        # Check if game has ended - maximize powered cities
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            current_powered = StrategyUtils.calculate_max_powered_cities(player)
            target_cities = min(len(available), current_powered - len(player.generators))
            if target_cities <= 0:
                target_cities = 1 if len(player.generators) == 0 else 0

            cities_to_build = []
            budget = player.money
            cities_with_cost = [(city, StrategyUtils.calculate_city_cost(player, city, game_state))
                               for city in available]
            cities_with_cost.sort(key=lambda x: x[1])

            for city, cost in cities_with_cost:
                if len(cities_to_build) >= target_cities or budget < cost:
                    break
                cities_to_build.append(city)
                budget -= cost

            return PlayerAction.city_build(cities_to_build)

        # Build 1-2 cities per turn based on game state
        # Build if we have good income potential or need first generator
        cities_to_build = []
        budget = player.money

        if len(player.generators) == 0:
            # Must build first generator
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            return PlayerAction.city_build([city])
        elif len(player.generators) < 10:
                # Early game: build more (up to 2 cities)
                num = min(2, len(available))
                for city in random.sample(available, num):
                    cost = StrategyUtils.calculate_city_cost(player, city, game_state)
                    if budget >= cost:
                        cities_to_build.append(city)
                        budget -= cost
        else:
            # Late game: be more selective (build 1 city)
            if random.random() > 0.5 and available:
                city = random.choice(available)
                cost = StrategyUtils.calculate_city_cost(player, city, game_state)
                if budget >= cost:
                    cities_to_build.append(city)

        return PlayerAction.city_build(cities_to_build)

    def choose_cities_to_power(self, player, game_state):
        """Balanced: Power based on resource situation and game state"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)

        # Check resource situation - if running low, conserve
        total_resources = sum(player.resources.values())
        total_capacity = sum(StrategyUtils.get_resource_capacities(player).values())

        if total_capacity > 0:
            resource_ratio = total_resources / total_capacity

            # If resources below 40%, consider powering fewer cities
            if resource_ratio < 0.4 and len(player.generators) >= 8:
                cities = max(0, max_powerable - 1)
            else:
                cities = max_powerable
        else:
            # Otherwise power maximum (limited by generators built)
            cities = max_powerable

        return PlayerAction.power_cities(cities)

class MyStrategy(Strategy):
    """My strategy: saves money, builds slowly"""

    def choose_auction_move(self, player, game_state):
        """Buy lowest indexed plant from my_least_cost list, discard highest indexed card"""
        """this is my list of plants to buy from cheapest to most expensive"""
        my_least_cost = [8, 3, 4, 22, 9, 5, 25, 20, 10, 16, 33, 34, 23, 29, 12, 30, 18, 6, 37, 19, 38, 26, 13, 46, 27, 14, 7, 42, 21, 35, 50, 36, 44, 15, 31, 24, 17, 28, 11]
        available_plants = game_state.current_market
        # print(f"current market: {game_state.current_market}")
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        # Find the lowest-indexed available plant from my_least_cost list
        available_plant_costs = {p.cost: p for p in affordable}
        selected_plant = None
        selected_plant_cost = None
        
        for plant_cost in my_least_cost:
            if plant_cost in available_plant_costs:
                selected_plant = available_plant_costs[plant_cost]
                selected_plant_cost = plant_cost
                break
        
        if not selected_plant:
            # No plant from my_least_cost list is available and affordable
            return PlayerAction.auction_pass()

        # Find the highest-indexed card from player's current cards
        discard = None
        if len(player.cards) >= 3:
            # Find which card has the highest index in my_least_cost
            highest_index = -1
            for card in player.cards:
                try:
                    card_index = my_least_cost.index(card.cost)
                    if card_index > highest_index:
                        highest_index = card_index
                        discard = card
                except ValueError:
                    # Card cost not in my_least_cost, use highest cost as fallback
                    if discard is None or card.cost > discard.cost:
                        discard = card
            
            # If no card found in my_least_cost, discard highest cost card
            if discard is None:
                discard = max(player.cards, key=lambda c: c.cost)

        # Check if must buy (first round)
        if must_buy:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        # Only buy if we have enough money left (keep reserve)
        reserve = 4
        if selected_plant.cost <= player.money - reserve:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """My: Only bid on cheap plants, don't bid high"""
        min_bid = current_bid + 1
        max_bid = player.money

        # Only interested if current bid is still low
        reserve = 120  # Keep money in reserve
        if plant.cost <= 10 and min_bid <= plant.cost + 1 and min_bid <= max_bid - reserve:
            # Only bid minimum, don't escalate
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_bid(min_bid, discard)
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Buy minimal resources"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                # Only buy what's needed for one production
                current = player.resources.get(resource_type, 0)
                needed = (2*(card.resource_cost)) - current

                if needed > 0:
                    # Check availability and affordability
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(needed, available_amount)

                    if amount_to_buy > 0:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build only if can afford easily"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        # Check if game has ended - maximize powered cities
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            current_powered = StrategyUtils.calculate_max_powered_cities(player)
            target_cities = min(len(available), current_powered - len(player.generators))
            if target_cities <= 0:
                target_cities = 1 if len(player.generators) == 0 else 0

            cities_to_build = []
            budget = player.money
            cities_with_cost = [(city, StrategyUtils.calculate_city_cost(player, city, game_state))
                               for city in available]
            cities_with_cost.sort(key=lambda x: x[1])

            for city, cost in cities_with_cost:
                if len(cities_to_build) >= target_cities or budget < cost:
                    break
                cities_to_build.append(city)
                budget -= cost

            return PlayerAction.city_build(cities_to_build)

        # Normal conservative behavior - save money if we have few resources
        if player.money < 30 and len(player.generators) > 0:
            return PlayerAction.city_build([])  # Save money

        # Build in cheapest city if we have money or need our first generator
        if player.money >= 5 or len(player.generators) == 0:
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            return PlayerAction.city_build([city])

        return PlayerAction.city_build([])

    def choose_cities_to_power(self, player, game_state):
        """Conservative: Power enough to maintain cash flow, save resources if wealthy"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)

        # If we have enough money (>60E), consider saving resources for later
        if player.money > 20 and len(player.generators) >= 4:
            # Power fewer cities to conserve resources
            cities = max(0, max_powerable - 1)
        else:
            # Otherwise power maximum (limited by generators built)
            cities = max_powerable

        return PlayerAction.power_cities(cities)

class TestStrategy(Strategy):
    """Test strategy: saves money, builds slowly"""

    def choose_auction_move(self, player, game_state):
        """Buy lowest indexed plant from my_least_cost list, discard highest indexed card"""
        """this is my list of plants to buy from cheapest to most expensive"""
        my_least_cost = [8, 3, 4, 22, 9, 5, 25, 20, 10, 16, 33, 34, 23, 29, 12, 30, 18, 6, 37, 19, 38, 26, 13, 46, 27, 14, 7, 42, 21, 35, 50, 36, 44, 15, 31, 24, 17, 28, 11]
        available_plants = game_state.current_market
        # print(f"current market: {game_state.current_market}")
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        # Find the lowest-indexed available plant from my_least_cost list
        available_plant_costs = {p.cost: p for p in affordable}
        selected_plant = None
        selected_plant_cost = None
        
        for plant_cost in my_least_cost:
            if plant_cost in available_plant_costs:
                selected_plant = available_plant_costs[plant_cost]
                selected_plant_cost = plant_cost
                break
        
        if not selected_plant:
            # No plant from my_least_cost list is available and affordable
            return PlayerAction.auction_pass()

        # Find the highest-indexed card from player's current cards
        discard = None
        if len(player.cards) >= 3:
            # Find which card has the highest index in my_least_cost
            highest_index = -1
            for card in player.cards:
                try:
                    card_index = my_least_cost.index(card.cost)
                    if card_index > highest_index:
                        highest_index = card_index
                        discard = card
                except ValueError:
                    # Card cost not in my_least_cost, use highest cost as fallback
                    if discard is None or card.cost > discard.cost:
                        discard = card
            
            # If no card found in my_least_cost, discard highest cost card
            if discard is None:
                discard = max(player.cards, key=lambda c: c.cost)

        # Check if must buy (first round)
        if must_buy:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        # Only buy if we have enough money left (keep reserve)
        reserve = 20
        if selected_plant.cost <= player.money - reserve:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Test: Only bid on cheap plants, don't bid high"""
        min_bid = current_bid + 1
        max_bid = player.money

        # Only interested if current bid is still low
        reserve = 120  # Keep money in reserve
        if plant.cost <= 15 and min_bid <= plant.cost + 2 and min_bid <= max_bid - reserve:
            # Only bid minimum, don't escalate
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_bid(min_bid, discard)
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Buy minimal resources"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                # Only buy what's needed for one production
                current = player.resources.get(resource_type, 0)
                needed = (2*(card.resource_cost)) - current

                if needed > 0:
                    # Check availability and affordability
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(needed, available_amount)

                    if amount_to_buy > 0:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Pick the city that connects to our network such that the sum (building + connection)
        is less than all other potential cities; build there if affordable."""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        # For each candidate: total cost = building + connection to our network.
        # Sort by this sum; the city with minimum sum is preferred over all others.
        cities_with_sum = [
            (city, StrategyUtils.calculate_city_cost(player, city, game_state))
            for city in available
        ]
        cities_with_sum.sort(key=lambda x: x[1])

        # Game-ended branch: maximize powered cities, still prefer min-sum cities first
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            current_powered = StrategyUtils.calculate_max_powered_cities(player)
            target_cities = min(len(available), current_powered - len(player.generators))
            if target_cities <= 0:
                target_cities = 1 if len(player.generators) == 0 else 0

            cities_to_build = []
            budget = player.money
            for city, cost in cities_with_sum:
                if len(cities_to_build) >= target_cities or budget < cost:
                    break
                cities_to_build.append(city)
                budget -= cost

            return PlayerAction.city_build(cities_to_build)

        # Normal: save money if we have few resources
        if player.money < 30 and len(player.generators) > 0:
            return PlayerAction.city_build([])

        # Build in the city with minimum sum (building + connection) if affordable
        if player.money >= 30 or len(player.generators) == 0:
            best_city, best_cost = cities_with_sum[0]
            if player.money >= best_cost:
                return PlayerAction.city_build([best_city])

        return PlayerAction.city_build([])

    def choose_cities_to_power(self, player, game_state):
        """Conservative: Power enough to maintain cash flow, save resources if wealthy"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)

        # If we have enough money (>60E), consider saving resources for later
        if player.money > 20 and len(player.generators) >= 2:
            # Power fewer cities to conserve resources
            cities = max(0, max_powerable - 1)
        else:
            # Otherwise power maximum (limited by generators built)
            cities = max_powerable

        return PlayerAction.power_cities(cities)

class OptimalStrategy(Strategy):
    """Optimal strategy: sandbags for turn order advantage, focuses on efficient plants and endgame power"""

    def __init__(self):
        self.lag_factor = 1  # Lag behind leader by 1 city for order advantage
        self.overbid_factor = 1.15  # Willing to overbid up to 15% for key plants
        self.stockpile_multiplier = 2  # Stock up to double needs if cheap

    def choose_auction_move(self, player, game_state):
        """Open auction on high-value plants if beneficial"""
        available_plants = game_state.current_market
        must_buy = game_state.round_num == 1
        affordable = StrategyUtils.get_affordable_plants(player, available_plants)

        if not affordable:
            return PlayerAction.auction_pass()

        # Sort by value
        affordable.sort(key=lambda p: self.evaluate_plant(p, player, game_state), reverse=True)
        best_plant = affordable[0]
        value = self.evaluate_plant(best_plant, player, game_state)
        min_bid = best_plant.cost
        max_willing = min(int(value * self.overbid_factor), player.money)

        if max_willing < min_bid:
            return PlayerAction.auction_pass()

        # Start with min if early, higher if late or leader
        bid = min_bid if not self.is_leader(player, game_state) else (min_bid + max_willing) // 2

        discard = self.get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None

        # Pass if leader unless must buy or great plant
        if self.is_leader(player, game_state) and not must_buy and value < best_plant.cost * 1.2:
            return PlayerAction.auction_pass()

        return PlayerAction.auction_open(best_plant, bid, discard)

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Bid on valuable plants, make opponents pay"""
        min_bid = current_bid + 1
        if min_bid > player.money:
            return PlayerAction.auction_bid_pass()

        value = self.evaluate_plant(plant, player, game_state)
        max_willing = min(int(value * self.overbid_factor), player.money)

        if min_bid > max_willing:
            return PlayerAction.auction_bid_pass()

        # Bid more if opponent values it highly
        opponent = game_state.players[current_winner]
        opp_value = self.evaluate_plant(plant, opponent, game_state)
        if opp_value > value:
            bid = min(min_bid + 3, max_willing)  # Make them pay
        else:
            bid = min_bid

        discard = self.get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None
        return PlayerAction.auction_bid(bid, discard)

    def choose_resources(self, player, game_state):
        """Buy resources, stockpile if cheap or endgame"""
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)
        is_last = self.is_last_in_order(player, game_state)  # Cheaper if last

        # Determine multiplier
        multiplier = self.stockpile_multiplier if is_last or self.is_near_endgame(game_state) else 1

        for plant in sorted(player.cards, key=lambda c: self.evaluate_plant(c, player, game_state), reverse=True):
            if plant.resource == 'green':
                continue

            res_type = self.select_resource_type(plant, game_state)
            if not res_type:
                continue

            needed = plant.resource_cost * multiplier
            current = player.resources.get(res_type, 0) + purchases.get(res_type, 0)
            cap = capacities[res_type]
            to_buy = min(needed - current, cap - current)

            if to_buy <= 0:
                continue

            res = game_state.resources[res_type]
            # Buy if cheap
            avg_cost = self.get_average_resource_cost(res)
            if avg_cost > 4 and not self.is_near_endgame(game_state):
                to_buy //= 2  # Less if expensive

            cost = StrategyUtils.get_resource_cost(res, to_buy)
            if cost is None or player.money < cost:
                for amt in range(to_buy - 1, 0, -1):
                    cost = StrategyUtils.get_resource_cost(res, amt)
                    if cost is not None and player.money >= cost:
                        to_buy = amt
                        break
                else:
                    continue

            purchases[res_type] = purchases.get(res_type, 0) + to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build to lag behind, secure cheap areas; burst in endgame"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        max_other = max(len(p.generators) for p in game_state.players if p != player)
        my_cities = len(player.generators)
        threshold = self.get_endgame_threshold(len(game_state.players))

        if max_other >= threshold or my_cities >= threshold:
            return self.endgame_build(player, game_state, available)

        target = max(0, max_other - self.lag_factor)
        to_build_count = target - my_cities

        # Always build first if none
        if my_cities == 0:
            to_build_count = max(to_build_count, 1)

        # Prefer cheap, expandable areas
        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])  # Cheapest first

        to_build = []
        budget = player.money
        for city, cost in cities_with_cost:
            if len(to_build) >= to_build_count:
                break
            if cost <= budget:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)

    def choose_cities_to_power(self, player, game_state):
        """Power max unless saving for endgame"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)
        if self.is_near_endgame(game_state):
            return PlayerAction.power_cities(max_powerable)
        # Save some resources if not end (but still limited by generators built)
        return PlayerAction.power_cities(max_powerable)

    # Helpers
    def evaluate_plant(self, plant, player, game_state):
        if plant.resource == 'green':
            return plant.cities * 15  # High for no cost

        res_type = self.select_resource_type(plant, game_state)
        avg_cost = self.get_average_resource_cost(game_state.resources[res_type])
        efficiency = plant.cities / (plant.resource_cost or 1)
        scarcity_penalty = 0 if self.is_resource_abundant(res_type, game_state) else -5
        step_bonus = game_state.step * 5
        return efficiency * (10 / avg_cost) + step_bonus + scarcity_penalty

    def select_resource_type(self, plant, game_state):
        if plant.resource == 'oil&gas':
            oil_cost = self.get_average_resource_cost(game_state.resources.get('oil'))
            gas_cost = self.get_average_resource_cost(game_state.resources.get('gas'))
            return 'oil' if oil_cost <= gas_cost else 'gas'
        elif plant.resource == 'nuclear':
            return 'uranium'
        return plant.resource

    def get_least_valuable_plant(self, player, game_state):
        return min(player.cards, key=lambda c: self.evaluate_plant(c, player, game_state))

    def get_average_resource_cost(self, resource):
        if not resource:
            return 8  # High if none
        purchases = resource.poss_purchases()
        if not purchases:
            return 8
        return sum(purchases.values()) / len(purchases)

    def is_resource_abundant(self, res_type, game_state):
        res = game_state.resources[res_type]
        return res.count > 10  # Arbitrary threshold

    def is_leader(self, player, game_state):
        return len(player.generators) >= max(len(p.generators) for p in game_state.players)

    def is_last_in_order(self, player, game_state):
        # Assume player order is based on cities, smaller first? No, leader is first.
        # Last in order is player with fewest cities.
        return len(player.generators) <= min(len(p.generators) for p in game_state.players)

    def endgame_build(self, player, game_state, available):
        threshold = self.get_endgame_threshold(len(game_state.players))
        my_capacity = sum(c.cities for c in player.cards)
        # Estimate opponents max power: their plant capacity
        max_opp_capacity = max(sum(c.cities for c in p.cards) for p in game_state.players if p != player)

        target = threshold if my_capacity > max_opp_capacity else threshold - 1  # Don't trigger if can't win

        current = len(player.generators)
        to_build_count = max(0, target - current)

        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])

        to_build = []
        budget = player.money
        for city, cost in cities_with_cost[:to_build_count]:
            if budget >= cost:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)

    def get_endgame_threshold(self, num_players):
        return {2: 18, 3: 17, 4: 17, 5: 15, 6: 14}.get(num_players, 17)

    def is_near_endgame(self, game_state):
        threshold = self.get_endgame_threshold(len(game_state.players))
        return max(len(p.generators) for p in game_state.players) >= threshold - 3

class PowerGridMasterStrategy(Strategy):
    """Ultimate strategy - FIXED to aggressively trigger Step 2 & endgame"""

    def __init__(self):
        self.lag_by_step = {1: 1, 2: 0, 3: 0}  # FIXED: Reduced Step 1 lag
        self.overbid_factor = 1.25
        self.base_stockpile = 1.8
        self.endgame_threshold = 17

    def choose_auction_move(self, player, game_state):
        available_plants = game_state.current_market
        must_buy = game_state.round_num == 1
        can_buy_more = len(player.cards) < 3

        affordable = [p for p in available_plants if player.money >= p.cost]
        if not affordable or (not must_buy and not can_buy_more):
            return PlayerAction.auction_pass()

        # Sort by net value: evaluate - cost
        def net_value(p):
            eval_score = self.evaluate_plant(p, player, game_state)
            return eval_score - p.cost

        affordable.sort(key=net_value, reverse=True)
        best_plant = affordable[0]
        min_bid = best_plant.cost
        value = self.evaluate_plant(best_plant, player, game_state)
        max_willing = min(int(value * self.overbid_factor), player.money)

        if max_willing < min_bid:
            return PlayerAction.auction_pass()

        # Bid strategy: min early, higher late
        bid_increment = (max_willing - min_bid) // 3
        bid = min_bid + bid_increment * game_state.step

        discard = self.get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None

        # Leaders pass unless exceptional value
        if self.is_leader(player, game_state) and not must_buy and net_value(best_plant) < 5:
            return PlayerAction.auction_pass()

        return PlayerAction.auction_open(best_plant, bid, discard)

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        min_bid = current_bid + 1
        if min_bid > player.money:
            return PlayerAction.auction_bid_pass()

        value = self.evaluate_plant(plant, player, game_state)
        max_willing = min(int(value * self.overbid_factor), player.money)

        if min_bid > max_willing:
            return PlayerAction.auction_bid_pass()

        # Drain aggressive opponents
        opponent = game_state.players[current_winner]
        opp_value = self.evaluate_plant(plant, opponent, game_state)
        bid_increment = 3 if opp_value > value * 1.1 else 1
        bid = min(min_bid + bid_increment, max_willing)

        discard = self.get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None
        return PlayerAction.auction_bid(bid, discard)

    def choose_resources(self, player, game_state):
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)
        is_cheap_order = self.is_late_order(player, game_state)  # 3rd/4th best for resources

        multiplier = self.base_stockpile if is_cheap_order else 1.2
        if game_state.step == 3 or self.is_near_endgame(game_state):
            multiplier *= 2
        elif game_state.step == 2:
            multiplier *= 1.5

        for plant in sorted(player.cards, key=lambda c: self.evaluate_plant(c, player, game_state), reverse=True):
            if plant.resource == 'green':
                continue
            res_type = self.select_resource_type(plant, game_state.resources)
            if res_type not in game_state.resources:
                continue

            res = game_state.resources[res_type]
            scarcity_mult = 1.5 if res.count < 6 else 1
            needed = plant.resource_cost * multiplier * scarcity_mult

            current_total = player.resources.get(res_type, 0) + purchases.get(res_type, 0)
            space = capacities[res_type] - current_total
            to_buy = min(needed, space)

            if to_buy > 0:
                # Convert to integer for resource purchases (resources are whole units)
                to_buy = int(to_buy)
                cost = StrategyUtils.get_resource_cost(res, to_buy)
                if cost is None or player.money < cost:
                    for amt in range(to_buy, 0, -1):
                        cost = StrategyUtils.get_resource_cost(res, amt)
                        if cost is not None and player.money >= cost:
                            to_buy = amt
                            break
                if to_buy > 0:
                    purchases[res_type] = purchases.get(res_type, 0) + to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_power(self, player, game_state):
        """Always power maximum possible cities for max money"""
        # Use helper method that properly limits by both resources and generators
        max_powerable = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(max_powerable)

    def choose_cities_to_build(self, player, game_state):
        """FIXED: Proactive Step trigger, lower thresholds, min expansion"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        my_cities = len(player.generators)
        max_other = max(len(p.generators) for p in game_state.players if p != player)

        if self.is_endgame(game_state):
            return self.endgame_build(player, game_state, available)

        # FIXED: Proactive Step 2 trigger
        if game_state.step == 1 and game_state.round_num > 6 and my_cities < 7:
            to_build_count = max(0, 7 - my_cities)
            cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
            cities_with_cost.sort(key=lambda x: x[1])
            to_build = [city for city, cost in cities_with_cost[:to_build_count] if player.money >= cost]
            return PlayerAction.city_build(to_build)

        lag = self.lag_by_step.get(game_state.step, 0)
        target = max_other - lag
        behind = max_other - my_cities
        
        if behind > lag * 2:
            to_build_count = min(6, behind)
        else:
            to_build_count = max(0, target - my_cities)

        if my_cities == 0:
            to_build_count = max(to_build_count, 1)

        # FIXED: Lowered excess & min expansion
        close_to_endgame = self.is_near_endgame(game_state)
        has_excess_money = player.money > 80  # FIXED
        if player.money > 120 and my_cities < 8:  # FIXED: New min expansion
            to_build_count = max(to_build_count, 2)

        if close_to_endgame or has_excess_money:
            plant_capacity = sum(c.cities for c in player.cards)
            target_cities = min(plant_capacity, self.endgame_threshold)
            needed = target_cities - my_cities
            if needed > 0:
                to_build_count = max(to_build_count, min(needed, 8))

        # FIXED: Step 3 always aggressive
        if game_state.step == 3:
            plant_capacity = sum(c.cities for c in player.cards)
            target_cities = min(plant_capacity, self.endgame_threshold)
            to_build_count = max(to_build_count, target_cities - my_cities)

        # FIXED: Higher caps
        max_per_round = 12 if (has_excess_money or close_to_endgame or game_state.step == 3) else 8
        to_build_count = min(to_build_count, len(available), max_per_round)

        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])

        to_build = []
        budget = player.money
        for city, cost in cities_with_cost[:to_build_count]:
            if budget >= cost:
                to_build.append(city)
                budget -= cost
            else:
                break

        return PlayerAction.city_build(to_build)

    # FIXED Helpers
    def is_near_endgame(self, game_state):
        max_cities = max(len(p.generators) for p in game_state.players)
        return max_cities >= 7  # FIXED: Earlier

    def is_endgame(self, game_state):
        max_cities = max(len(p.generators) for p in game_state.players)
        return max_cities >= 9  # FIXED: Earlier

    def endgame_build(self, player, game_state, available):
        my_power = StrategyUtils.calculate_max_powered_cities(player)
        opp_powers = [StrategyUtils.calculate_max_powered_cities(p) for p in game_state.players if p != player]
        max_opp_power = max(opp_powers) if opp_powers else 0

        current = len(player.generators)
        threshold = self.endgame_threshold

        # FIXED: Looser condition
        if my_power >= max_opp_power - 1:
            target = threshold
        else:
            target = min(threshold - 1, my_power)

        to_build_count = max(0, target - current)
        to_build_count = min(to_build_count, len(available), 12)  # FIXED: Higher cap

        cities_with_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        cities_with_cost.sort(key=lambda x: x[1])

        to_build = []
        budget = player.money
        
        for city, cost in cities_with_cost:
            if len(to_build) >= to_build_count:
                break
            if budget >= cost:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)  # FIXED: Return Action

    # Helper methods
    def evaluate_plant(self, plant, player, game_state):
        if plant.resource == 'green':
            return plant.cities * 25 + game_state.step * 15

        res_type = self.select_resource_type(plant, game_state.resources)
        if res_type not in game_state.resources:
            return plant.cities * 5  # Fallback

        res = game_state.resources[res_type]
        avg_price = self.get_average_resource_cost(res)
        res_cost = plant.resource_cost * avg_price

        capacity_value = plant.cities * (25 - game_state.round_num // 2)  # Declining marginal
        efficiency = capacity_value / max(1, res_cost)

        scarcity = 1.0 if res.count >= 8 else 0.8 if res.count >= 4 else 0.6
        step_bonus = game_state.step * 8
        hybrid_bonus = 5 if plant.resource == 'oil&gas' else 0

        return efficiency * scarcity + step_bonus + hybrid_bonus

    def select_resource_type(self, plant, resources):
        if plant.resource == 'nuclear':
            return 'uranium'
        if plant.resource == 'oil&gas':
            oil_avg = self.get_average_resource_cost(resources.get('oil', None)) if 'oil' in resources else 99
            gas_avg = self.get_average_resource_cost(resources.get('gas', None)) if 'gas' in resources else 99
            return 'oil' if oil_avg < gas_avg else 'gas'
        return plant.resource

    def get_least_valuable_plant(self, player, game_state):
        if not player.cards:
            return None
        # Dummy resources for eval - create instances with poss_purchases method
        def create_dummy_resource():
            class DummyResource:
                def __init__(self):
                    self.count = 20
                def poss_purchases(self):
                    # Return a simple cost structure for evaluation
                    return {1: 1, 2: 2, 3: 3, 4: 4}
            return DummyResource()
        
        dummy_resources = {r: create_dummy_resource() for r in ['coal', 'oil', 'gas', 'uranium']}
        # Create dummy game state with all required attributes (including round_num)
        dummy_game_state = type('GS', (), {
            'resources': dummy_resources, 
            'step': game_state.step if hasattr(game_state, 'step') else 2,
            'round_num': game_state.round_num if hasattr(game_state, 'round_num') else 10
        })()
        return min(player.cards, key=lambda c: self.evaluate_plant(c, player, dummy_game_state))

    def get_average_resource_cost(self, resource):
        if not resource or resource.count == 0:
            return 12
        poss = resource.poss_purchases()
        return sum(poss.values()) / len(poss) if poss else 8

    def is_leader(self, player, game_state):
        return len(player.generators) >= max((len(p.generators) for p in game_state.players), default=0)

    def is_late_order(self, player, game_state):
        """3rd or 4th for cheap resources"""
        return len(player.generators) <= sorted([len(p.generators) for p in game_state.players])[1]  # 2nd smallest or smaller

class MyMightyStrategy(Strategy):
    """Greedy strategy: tries to expand and power many cities"""

    def choose_auction_move(self, player, game_state):
        """Buy lowest indexed plant from my_least_cost list, discard highest indexed card"""
        """this is my list of plants to buy from cheapest to most expensive"""
        my_least_cost = [8, 3, 4, 22, 9, 5, 25, 20, 10, 16, 33, 34, 23, 29, 12, 30, 18, 6, 37, 19, 38, 26, 13, 46, 27, 14, 7, 42, 21, 35, 50, 36, 44, 15, 31, 24, 17, 28, 11]
        available_plants = game_state.current_market
        # print(f"current market: {game_state.current_market}")
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        # Find the lowest-indexed available plant from my_least_cost list
        available_plant_costs = {p.cost: p for p in affordable}
        selected_plant = None
        selected_plant_cost = None
        
        for plant_cost in my_least_cost:
            if plant_cost in available_plant_costs:
                selected_plant = available_plant_costs[plant_cost]
                selected_plant_cost = plant_cost
                break
        
        if not selected_plant:
            # No plant from my_least_cost list is available and affordable
            return PlayerAction.auction_pass()

        # Find the highest-indexed card from player's current cards
        discard = None
        if len(player.cards) >= 3:
            # Find which card has the highest index in my_least_cost
            highest_index = -1
            for card in player.cards:
                try:
                    card_index = my_least_cost.index(card.cost)
                    if card_index > highest_index:
                        highest_index = card_index
                        discard = card
                except ValueError:
                    # Card cost not in my_least_cost, use highest cost as fallback
                    if discard is None or card.cost > discard.cost:
                        discard = card
            
            # If no card found in my_least_cost, discard highest cost card
            if discard is None:
                discard = max(player.cards, key=lambda c: c.cost)

        # Check if must buy (first round)
        if must_buy:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        # Only buy if we have enough money left (keep reserve)
        reserve = 4
        if selected_plant.cost <= player.money - reserve:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        # """Greedy: Bid aggressively on plants that power many cities"""
        # min_bid = current_bid + 1
        # max_bid = player.money

        # # Want plants with high city count
        # if plant.cities >= 14 and min_bid <= max_bid:
        #     # Willing to pay up to plant cost + cities
        #     max_willing = min(plant.cost + plant.cities, max_bid)
        #     if max_willing >= min_bid:
        #         bid_amount = min(min_bid + 2, max_willing)
        #         discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
        #         return PlayerAction.auction_bid(bid_amount, discard)
        # elif plant.cities >= 3 and min_bid <= max_bid * 0.5:
        #     # Moderate interest
        #     discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
        #     return PlayerAction.auction_bid(min_bid, discard)
        return PlayerAction.auction_bid_pass()

    def choose_resources(self, player, game_state):
        """Buy resources for all owned plants"""
        resources = game_state.resources
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)

        for card in player.cards:
            if card.resource == 'green':
                continue

            resource_type = card.resource
            if resource_type == 'nuclear':
                resource_type = 'uranium'
            elif resource_type == 'oil&gas':
                # Choose cheaper resource
                if 'oil' in resources and 'gas' in resources:
                    oil_cost = StrategyUtils.get_resource_cost(resources['oil'], 1)
                    gas_cost = StrategyUtils.get_resource_cost(resources['gas'], 1)
                    resource_type = 'oil' if oil_cost and gas_cost and oil_cost <= gas_cost else 'gas'
                elif 'oil' in resources:
                    resource_type = 'oil'
                elif 'gas' in resources:
                    resource_type = 'gas'
                else:
                    continue

            if resource_type in resources:
                current = player.resources.get(resource_type, 0)
                max_capacity = capacities[resource_type]
                needed = max_capacity - current

                if needed > 0:
                    # Check availability and affordability
                    available_amount = resources[resource_type].count
                    amount_to_buy = min(needed, available_amount)

                    if amount_to_buy > 0:
                        cost = StrategyUtils.get_resource_cost(resources[resource_type], amount_to_buy)
                        if cost is not None and player.money >= cost:
                            purchases[resource_type] = purchases.get(resource_type, 0) + amount_to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """Build in as many cities as affordable"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        # Check if game has ended - maximize powered cities
        if StrategyUtils.has_game_ended_with_players(game_state.players):
            current_powered = StrategyUtils.calculate_max_powered_cities(player)
            target_cities = min(len(available), current_powered - len(player.generators))
            if target_cities <= 0:
                target_cities = 1 if len(player.generators) == 0 else 0
        else:
            target_cities = len(available)  # Build as many as possible (greedy)

        cities_to_build = []
        budget = player.money

        # Sort by cost to build cheapest first
        cities_with_cost = [(city, StrategyUtils.calculate_city_cost(player, city, game_state))
                           for city in available]
        cities_with_cost.sort(key=lambda x: x[1])

        for city_name, total_cost in cities_with_cost:
            if len(cities_to_build) >= target_cities or budget <= 0:
                break

            if total_cost <= budget:
                cities_to_build.append(city_name)
                budget -= total_cost

        if player.generators == 0 and not cities_to_build and available:
            # Must build at least one, choose cheapest
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            cities_to_build = [city]

        return PlayerAction.city_build(cities_to_build)

    def choose_cities_to_power(self, player, game_state):
        """Greedy: Power maximum cities possible"""
        # Greedy strategy: always power as many as possible for maximum income (limited by generators built)
        cities = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(cities)

