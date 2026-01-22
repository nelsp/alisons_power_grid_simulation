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
        """Get plants the player can afford"""
        return [p for p in available_plants if player.money >= p.cost]

    @staticmethod
    def can_buy_plant(player):
        """Check if player can buy another plant (max 3)"""
        return len(player.cards) < 3

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
        # Simple strategy: always power as many as possible
        cities = StrategyUtils.calculate_max_powered_cities(player)
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
        # Greedy strategy: always power as many as possible for maximum income
        cities = StrategyUtils.calculate_max_powered_cities(player)
        return PlayerAction.power_cities(cities)


class ConservativeStrategy(Strategy):
    """Conservative strategy: saves money, builds slowly"""

    def choose_auction_move(self, player, game_state):
        """Buy only cheap plants"""
        available_plants = game_state.current_market
        # print(f"current market: {game_state.current_market}")
        must_buy = (game_state.round_num == 1)

        if not available_plants or not StrategyUtils.can_buy_plant(player):
            return PlayerAction.auction_pass()

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        if must_buy:
            # Choose cheapest affordable
            cheapest = min(affordable, key=lambda p: p.cost)
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(cheapest, cheapest.cost, discard)

        # Only buy if we have enough money left (keep reserve)
        reserve = 20
        affordable_reserve = [p for p in affordable if p.cost <= player.money - reserve]
        if affordable_reserve:
            cheapest = min(affordable_reserve, key=lambda p: p.cost)
            discard = min(player.cards, key=lambda c: c.cost) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(cheapest, cheapest.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Conservative: Only bid on cheap plants, don't bid high"""
        min_bid = current_bid + 1
        max_bid = player.money

        # Only interested if current bid is still low
        reserve = 20  # Keep money in reserve
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
                needed = card.resource_cost - current

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
        if player.money >= 30 or len(player.generators) == 0:
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            return PlayerAction.city_build([city])

        return PlayerAction.city_build([])

    def choose_cities_to_power(self, player, game_state):
        """Conservative: Power enough to maintain cash flow, save resources if wealthy"""
        max_powered = StrategyUtils.calculate_max_powered_cities(player)

        # If we have enough money (>60E), consider saving resources for later
        if player.money > 60 and len(player.generators) >= 10:
            # Power fewer cities to conserve resources
            cities = max(0, max_powered - 2)
        else:
            # Otherwise power maximum
            cities = max_powered

        return PlayerAction.power_cities(cities)


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
        max_powered = StrategyUtils.calculate_max_powered_cities(player)

        # Check resource situation - if running low, conserve
        total_resources = sum(player.resources.values())
        total_capacity = sum(StrategyUtils.get_resource_capacities(player).values())

        if total_capacity > 0:
            resource_ratio = total_resources / total_capacity

            # If resources below 40%, consider powering fewer cities
            if resource_ratio < 0.4 and len(player.generators) >= 8:
                cities = max(0, max_powered - 1)
            else:
                cities = max_powered
        else:
            # Otherwise power maximum
            cities = max_powered

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
        reserve = 20
        if selected_plant.cost <= player.money - reserve:
            return PlayerAction.auction_open(selected_plant, selected_plant.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """My: Only bid on cheap plants, don't bid high"""
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
        if player.money >= 30 or len(player.generators) == 0:
            city = min(available, key=lambda c: StrategyUtils.calculate_city_cost(player, c, game_state))
            return PlayerAction.city_build([city])

        return PlayerAction.city_build([])

    def choose_cities_to_power(self, player, game_state):
        """Conservative: Power enough to maintain cash flow, save resources if wealthy"""
        max_powered = StrategyUtils.calculate_max_powered_cities(player)

        # If we have enough money (>60E), consider saving resources for later
        if player.money > 50 and len(player.generators) >= 8:
            # Power fewer cities to conserve resources
            cities = max(0, max_powered - 1)
        else:
            # Otherwise power maximum
            cities = max_powered

        return PlayerAction.power_cities(cities)
