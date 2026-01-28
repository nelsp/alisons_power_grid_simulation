"""
Kris Strategy for Power Grid

"""

from player_action import PlayerAction
from player_strategies import Strategy, StrategyUtils


class Kris(Strategy):
    """
    This strategy tries to be efficient when buying powerplants,
    doens't over power
    Jockeys for position for resources and generator buying
    and always puts itself in a position to win the game.
    """

    # Viable 3-plant combinations that can power 17+ cities
    ENDGAME_SETS = [
        (4, 6, 7),
        (5, 5, 7),
        (5, 6, 6),
        (5, 6, 7),
        (6, 6, 7),
    ]

    # Minimum cities-powered increase to not be discounted during evaluation
    CITIES_INCREASE_THRESHOLD = 2

    def __init__(self,
                 trigger_confidence=0.7,
                 resource_denial_weight=1.5,
                 green_premium=1.4,
                 sandbag_aggression=0.8):
        self.trigger_confidence = trigger_confidence
        self.resource_denial_weight = resource_denial_weight
        self.green_premium = green_premium
        self.sandbag_aggression = sandbag_aggression
        self.thresholds = {2: 21, 3: 17, 4: 17, 5: 15, 6: 14}
        self.removed_from_market = []  # cities values of plants removed in phase 5
        self._last_round = 0

    def get_endgame_threshold(self, num_players):
        return self.thresholds.get(num_players, 17)

    # =========================================================================
    # POWER ANALYSIS
    # =========================================================================

    def get_max_power_capacity(self, player):
        """Total cities player's plants can power"""
        return sum(p.cities for p in player.cards)

    def can_power_with_resources(self, player, plant):
        """Check if player has resources to fire this plant"""
        if plant.resource == 'green':
            return True
        if plant.resource_cost == 0:
            return True
            
        if plant.resource == 'oil&gas':
            oil = player.resources.get('oil', 0)
            gas = player.resources.get('gas', 0)
            return oil + gas >= plant.resource_cost
        elif plant.resource == 'nuclear':
            return player.resources.get('uranium', 0) >= plant.resource_cost
        else:
            return player.resources.get(plant.resource, 0) >= plant.resource_cost

    def current_power_capacity(self, player):
        """Cities player can power RIGHT NOW with current resources"""
        total = 0
        used = {'coal': 0, 'oil': 0, 'gas': 0, 'uranium': 0}
        
        for plant in sorted(player.cards, key=lambda p: p.cities, reverse=True):
            if plant.resource == 'green':
                total += plant.cities
            elif plant.resource == 'oil&gas':
                oil_avail = player.resources.get('oil', 0) - used['oil']
                gas_avail = player.resources.get('gas', 0) - used['gas']
                if oil_avail + gas_avail >= plant.resource_cost:
                    use_oil = min(oil_avail, plant.resource_cost)
                    use_gas = plant.resource_cost - use_oil
                    used['oil'] += use_oil
                    used['gas'] += use_gas
                    total += plant.cities
            elif plant.resource == 'nuclear':
                avail = player.resources.get('uranium', 0) - used['uranium']
                if avail >= plant.resource_cost:
                    used['uranium'] += plant.resource_cost
                    total += plant.cities
            elif plant.resource in used:
                avail = player.resources.get(plant.resource, 0) - used.get(plant.resource, 0)
                if avail >= plant.resource_cost:
                    used[plant.resource] = used.get(plant.resource, 0) + plant.resource_cost
                    total += plant.cities
        
        return total

    # =========================================================================
    # TOTAL COST OF OWNERSHIP
    # =========================================================================

    # Resupply amounts per resource type: {num_players: [step1, step2, step3]}
    RESUPPLY_TABLES = {
        'coal': {2: [2, 6, 2], 3: [2, 6, 2], 4: [3, 7, 4], 5: [3, 8, 4], 6: [5, 10, 5]},
        'gas': {2: [2, 3, 5], 3: [2, 3, 5], 4: [3, 4, 5], 5: [3, 5, 7], 6: [4, 6, 8]},
        'oil': {2: [2, 2, 3], 3: [2, 2, 3], 4: [3, 3, 4], 5: [4, 3, 5], 6: [4, 5, 6]},
        'uranium': {2: [1, 1, 2], 3: [1, 1, 2], 4: [1, 2, 2], 5: [2, 3, 3], 6: [2, 3, 4]},
    }

    def _sim_buy(self, board, amount):
        """Buy `amount` resources from cheapest slots on a simulated board.

        Mutates board in place. Returns (cost, actual_bought).
        """
        cost = 0
        bought = 0
        for price_bin in board:
            price = price_bin[0]
            for i, slot in enumerate(price_bin[1]):
                if slot == 1 and bought < amount:
                    price_bin[1][i] = 0
                    cost += price
                    bought += 1
        return cost, bought

    def _sim_resupply(self, board, supply, resupply_amount):
        """Place resources back onto a simulated board from the supply pool.

        Fills from most-expensive empty slots down (matching game engine logic).
        Mutates board in place. Returns new supply value.
        """
        units_to_place = min(resupply_amount, supply)
        placed = 0
        # Fill from most expensive bin down to index 1 (matches game engine resupply)
        for i in range(len(board) - 1, 0, -1):
            for j in range(len(board[i][1]) - 1, -1, -1):
                if board[i][1][j] == 0 and placed < units_to_place:
                    board[i][1][j] = 1
                    placed += 1
        return supply - placed

    def _opponent_demand_for_resource(self, opponent, resource_type, first_turn):
        """How many units of resource_type an opponent would buy.

        first_turn=True:  buy up to max storage capacity (capacity - currently held).
        first_turn=False: buy back 1 run (sum of resource_cost for matching plants).
        """
        capacity = 0
        run_demand = 0
        for card in opponent.cards:
            matches = (
                card.resource == resource_type
                or (card.resource == 'oil&gas' and resource_type in ('oil', 'gas'))
                or (card.resource == 'nuclear' and resource_type == 'uranium')
            )
            if matches:
                capacity += card.resource_cost * 2
                run_demand += card.resource_cost

        if first_turn:
            current = opponent.resources.get(resource_type, 0)
            return max(0, capacity - current)
        return run_demand

    def _total_usage_for_resource(self, game_state, resource_type, extra_plant=None):
        """Total units of resource_type consumed per turn by ALL players.

        Used to determine how much returns to total_supply after the power phase.
        extra_plant: a plant we're considering buying (adds its usage too).
        """
        total = 0
        for p in game_state.players:
            for card in p.cards:
                matches = (
                    card.resource == resource_type
                    or (card.resource == 'oil&gas' and resource_type in ('oil', 'gas'))
                    or (card.resource == 'nuclear' and resource_type == 'uranium')
                )
                if matches:
                    total += card.resource_cost
        if extra_plant:
            total += extra_plant.resource_cost
        return total

    def _calculate_fuel_cost(self, plant, player, game_state, resource_type):
        """Simulate 3 turns of fuel purchasing for one resource type.

        Models worst-case pricing by simulating opponents buying before/after us
        in resource buy order, with resupply between turns.

        Turn 1: opponents buy to max capacity.
        Turns 2-3: opponents buy back 1 run (they used resources, refill to max).
        Each turn we buy exactly plant.resource_cost units.
        Between turns: all consumed resources return to supply, then resupply.
        """
        resource = game_state.resources.get(resource_type)
        if resource is None:
            return float('inf')

        # Deep-copy board state
        board = [[b[0], list(b[1])] for b in resource.capacity_list]
        supply = resource.total_supply

        num_players = len(game_state.players)
        step = game_state.step

        resupply_amt = self.RESUPPLY_TABLES.get(resource_type, {}).get(
            num_players, [3, 3, 3]
        )[step - 1]

        # Buy order is reverse of player_order
        buy_order = list(reversed(game_state.player_order))
        my_idx = next(i for i, p in enumerate(game_state.players) if p is player)
        my_position = buy_order.index(my_idx)

        opponents_before = buy_order[:my_position]
        opponents_after = buy_order[my_position + 1:]

        # Resources consumed per turn by everyone (returns to supply after power phase)
        total_usage = self._total_usage_for_resource(
            game_state, resource_type, extra_plant=plant
        )

        total_fuel_cost = 0

        for turn in range(3):
            first_turn = (turn == 0)

            # Opponents before us buy
            for opp_idx in opponents_before:
                demand = self._opponent_demand_for_resource(
                    game_state.players[opp_idx], resource_type, first_turn
                )
                self._sim_buy(board, demand)

            # We buy our plant's fuel requirement
            our_cost, bought = self._sim_buy(board, plant.resource_cost)
            if bought < plant.resource_cost:
                # Resources unavailable — penalize at above-max-price per missing unit
                our_cost += 99999
            total_fuel_cost += our_cost

            # Opponents after us buy
            for opp_idx in opponents_after:
                demand = self._opponent_demand_for_resource(
                    game_state.players[opp_idx], resource_type, first_turn
                )
                self._sim_buy(board, demand)

            # End of turn: consumed resources return to supply, then resupply
            supply += total_usage
            supply = self._sim_resupply(board, supply, resupply_amt)

        return total_fuel_cost

    def _predict_next_round_cost(self, player, game_state, resource_type,
                                    our_buy_this_round, amount_to_check):
        """Predict cost to buy `amount_to_check` units of a resource next round.

        Simulates from the current board state:
        1. We buy `our_buy_this_round` (depleting cheap slots)
        2. Opponents after us finish buying this round
        3. All players use resources (returned to supply)
        4. Board resupplied
        5. Opponents before us buy next round
        6. Returns the cost we'd pay for `amount_to_check` at that point
        """
        resource = game_state.resources.get(resource_type)
        if resource is None:
            return float('inf')

        board = [[b[0], list(b[1])] for b in resource.capacity_list]
        supply = resource.total_supply

        num_players = len(game_state.players)
        step = game_state.step
        resupply_amt = self.RESUPPLY_TABLES.get(resource_type, {}).get(
            num_players, [3, 3, 3]
        )[step - 1]

        buy_order = list(reversed(game_state.player_order))
        my_idx = next(i for i, p in enumerate(game_state.players) if p is player)
        my_position = buy_order.index(my_idx)
        opponents_after = buy_order[my_position + 1:]
        opponents_before = buy_order[:my_position]

        total_usage = self._total_usage_for_resource(game_state, resource_type)

        # 1. We buy now
        self._sim_buy(board, our_buy_this_round)

        # 2. Opponents after us finish buying this round
        for opp_idx in opponents_after:
            demand = self._opponent_demand_for_resource(
                game_state.players[opp_idx], resource_type, first_turn=False
            )
            self._sim_buy(board, demand)

        # 3-4. Use and resupply
        supply += total_usage
        supply = self._sim_resupply(board, supply, resupply_amt)

        # 5. Next round: opponents before us buy
        for opp_idx in opponents_before:
            demand = self._opponent_demand_for_resource(
                game_state.players[opp_idx], resource_type, first_turn=False
            )
            self._sim_buy(board, demand)

        # 6. What would we pay?
        cost, bought = self._sim_buy(board, amount_to_check)
        if bought < amount_to_check:
            cost += 99999
        return cost

    def total_cost_of_ownership(self, plant, player, game_state):
        """Plant purchase price + worst-case cost to fuel it 3 times.

        Green plants have no fuel cost (returns just plant.cost).
        Oil&gas plants simulate both markets and use the cheaper option.
        """
        if plant.resource == 'green':
            return plant.cost

        if plant.resource == 'oil&gas':
            oil_fuel = self._calculate_fuel_cost(plant, player, game_state, 'oil')
            gas_fuel = self._calculate_fuel_cost(plant, player, game_state, 'gas')
            return plant.cost + min(oil_fuel, gas_fuel)

        resource_type = 'uranium' if plant.resource == 'nuclear' else plant.resource
        fuel_cost = self._calculate_fuel_cost(plant, player, game_state, resource_type)
        return plant.cost + fuel_cost

    # =========================================================================
    # ENDGAME ANALYSIS
    # =========================================================================

    def _is_submultiset(self, subset, superset):
        """Check if every element in subset appears in superset (with multiplicity)."""
        remaining = list(superset)
        for val in subset:
            if val in remaining:
                remaining.remove(val)
            else:
                return False
        return True

    def _achievable_endgame_sets(self, cities_list):
        """Return endgame sets reachable from a (possibly partial) hand of cities values."""
        cities = sorted(cities_list)
        result = []
        for target in self.ENDGAME_SETS:
            if len(cities) == len(target):
                if tuple(cities) == target:
                    result.append(target)
            elif len(cities) < len(target):
                if self._is_submultiset(cities, list(target)):
                    result.append(target)
        return result

    def _cities_powered_increase(self, plant, player):
        """Net increase in total cities powered if we buy this plant."""
        if len(player.cards) >= 3:
            worst = min(player.cards, key=lambda c: c.cost)
            return plant.cities - worst.cities
        return plant.cities

    def _endgame_viability_score(self, plant, player):
        """Score how well this plant positions us for an endgame set.

        Returns a small premium (0-15) for viable plants.
        Discounts for narrow sets, duplicate cities values, or removed plants.
        """
        # Project our hand after buying (discard lowest-cost if at 3)
        future_cards = list(player.cards)
        if len(future_cards) >= 3:
            worst = min(future_cards, key=lambda c: c.cost)
            future_cards.remove(worst)
        future_cards.append(plant)
        future_cities = sorted([c.cities for c in future_cards])

        achievable = self._achievable_endgame_sets(future_cities)
        if not achievable:
            return 0

        num_sets = len(achievable)
        # Base premium for viability + breadth bonus
        premium = 5 + (num_sets - 1) * 3  # 5 for 1 set, 8 for 2, ... 17 for 5

        # Discount for duplicate cities values that narrow our options
        existing_cities = [c.cities for c in player.cards]
        if plant.cities in existing_cities and num_sets <= 1:
            return 0  # No value in a duplicate that only fits one narrow set

        # Discount if plants we still need have been removed from the market
        for target in achievable:
            needed = list(target)
            for c in future_cities:
                if c in needed:
                    needed.remove(c)
            for val in needed:
                removed_count = sum(1 for r in self.removed_from_market if r == val)
                premium -= removed_count * 2

        return max(0, premium)

    # =========================================================================
    # AUCTION PHASE
    # =========================================================================

    def evaluate_plant(self, plant, player, game_state):
        """Score a plant based on TCO, cities-powered increase, and endgame viability."""
        tco = self.total_cost_of_ownership(plant, player, game_state)
        fuel_cost = tco - plant.cost

        # Base value: expected income from cities powered minus fuel cost
        score = plant.cities * 20 - fuel_cost

        # Discount if this plant doesn't meaningfully increase our output
        increase = self._cities_powered_increase(plant, player)
        if increase < self.CITIES_INCREASE_THRESHOLD:
            score *= 0.25

        # Endgame viability adjustment
        score += self._endgame_viability_score(plant, player)

        return score

    def choose_auction_move(self, player, game_state):
        """Buy plants, evaluated by TCO, cities increase, and endgame viability."""
        # Reset tracking when a new game starts (round drops back to 1)
        if game_state.round_num == 1 and self._last_round != 0:
            self.removed_from_market = []
        self._last_round = game_state.round_num

        must_buy = game_state.round_num == 1

        # Determine what we can afford after reserving money for cities
        cities_needed = max(0, 10 - len(player.generators))
        city_reserve = cities_needed * 15
        max_spend = player.money - city_reserve
        if max_spend < 3:
            max_spend = player.money // 2

        affordable = [p for p in game_state.current_market if p.cost <= max_spend]

        if not affordable:
            if must_buy:
                affordable = StrategyUtils.get_affordable_plants(player, game_state.current_market)
            if not affordable:
                return PlayerAction.auction_pass()

        # Rank all affordable plants by evaluate_plant score (TCO-based)
        scored = [
            (self.evaluate_plant(p, player, game_state), p)
            for p in affordable
        ]
        scored.sort(reverse=True, key=lambda x: x[0])

        # Walk the ranked list and pick the first plant worth opening on
        for score, plant in scored:
            # Only open if our valuation exceeds the base cost (unless forced to buy)
            if not must_buy and score <= plant.cost:
                continue

            # Determine discard if at 3 plants
            discard = None
            if len(player.cards) >= 3:
                worst = min(player.cards, key=lambda c: c.cost)
                if plant.cost > worst.cost:
                    discard = worst
                elif must_buy:
                    discard = worst
                else:
                    continue  # Not an upgrade over our worst

            return PlayerAction.auction_open(plant, plant.cost, discard)

        # Nothing worth opening — forced buy takes cheapest available
        if must_buy and affordable:
            plant = min(affordable, key=lambda p: p.cost)
            discard = None
            if len(player.cards) >= 3:
                discard = min(player.cards, key=lambda c: c.cost)
            return PlayerAction.auction_open(plant, plant.cost, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Bid up to our evaluated score for the plant, no higher."""
        min_bid = current_bid + 1

        # Check if we need to discard
        discard = None
        if len(player.cards) >= 3:
            worst = min(player.cards, key=lambda c: c.cost)
            if plant.cost > worst.cost:
                discard = worst
            else:
                return PlayerAction.auction_bid_pass()

        score = self.evaluate_plant(plant, player, game_state)

        # Round 1: never bid above base cost
        if game_state.round_num == 1 and min_bid > plant.cost:
            return PlayerAction.auction_bid_pass()

        # Only bid if our valuation still exceeds what we'd have to pay
        if min_bid > player.money or min_bid > score:
            return PlayerAction.auction_bid_pass()

        return PlayerAction.auction_bid(min_bid, discard)

    # =========================================================================
    # RESOURCE PHASE
    # =========================================================================

    def choose_resources(self, player, game_state):
        """Buy resources in three passes:

        1. Set aside minimum resources to fire each plant once.
        2. Project how many cities we can buy with remaining money.
        3. Spend any leftover money on additional resources up to max storage.
        """
        capacities = StrategyUtils.get_resource_capacities(player)

        # --- Aggregate demand per resource type ---
        demand = {}  # resource_type -> total resource_cost across plants
        oilgas_demand = 0
        for plant in player.cards:
            if plant.resource == 'green':
                continue
            if plant.resource == 'oil&gas':
                oilgas_demand += plant.resource_cost
            elif plant.resource == 'nuclear':
                demand['uranium'] = demand.get('uranium', 0) + plant.resource_cost
            else:
                demand[plant.resource] = demand.get(plant.resource, 0) + plant.resource_cost

        # Resolve oil&gas: pick the cheaper resource for the full amount
        if oilgas_demand > 0:
            oil_res = game_state.resources.get('oil')
            gas_res = game_state.resources.get('gas')
            oil_cost = StrategyUtils.get_resource_cost(oil_res, oilgas_demand) if oil_res else None
            gas_cost = StrategyUtils.get_resource_cost(gas_res, oilgas_demand) if gas_res else None
            if oil_cost is not None and (gas_cost is None or oil_cost <= gas_cost):
                demand['oil'] = demand.get('oil', 0) + oilgas_demand
            elif gas_cost is not None:
                demand['gas'] = demand.get('gas', 0) + oilgas_demand
            elif oil_res and oil_res.count > 0:
                demand['oil'] = demand.get('oil', 0) + oilgas_demand
            elif gas_res and gas_res.count > 0:
                demand['gas'] = demand.get('gas', 0) + oilgas_demand

        # =====================================================================
        # Pass 1: buy minimum to fire each plant once
        # =====================================================================
        purchases = {}
        budget = player.money

        for res_type, total_need in demand.items():
            res = game_state.resources.get(res_type)
            if res is None:
                continue
            current = player.resources.get(res_type, 0)
            cap = capacities.get(res_type, 0)

            min_want = max(0, total_need - current)
            min_want = min(min_want, res.count, cap - current)

            if min_want > 0:
                cost = StrategyUtils.get_resource_cost(res, min_want)
                while min_want > 0 and (cost is None or cost > budget):
                    min_want -= 1
                    cost = StrategyUtils.get_resource_cost(res, min_want) if min_want > 0 else 0
                if min_want > 0 and cost:
                    purchases[res_type] = min_want
                    budget -= cost

        # =====================================================================
        # Pass 2: project city spending to determine leftover budget
        # =====================================================================
        my_cities = len(player.generators)
        my_power = self.get_max_power_capacity(player)
        cities_want = max(0, my_power - my_cities)

        city_budget = 0
        if cities_want > 0:
            available = StrategyUtils.get_available_cities(player, game_state)
            city_costs = sorted(
                (StrategyUtils.calculate_city_cost(player, c, game_state) for c in available)
            )
            for cost in city_costs:
                if cities_want <= 0:
                    break
                if cost <= budget - city_budget:
                    city_budget += cost
                    cities_want -= 1

        leftover = budget - city_budget

        # =====================================================================
        # Pass 3: spend leftover on additional resources up to max storage
        # =====================================================================
        for res_type in demand:
            res = game_state.resources.get(res_type)
            if res is None:
                continue
            current = player.resources.get(res_type, 0)
            cap = capacities.get(res_type, 0)
            bought_so_far = purchases.get(res_type, 0)
            held = current + bought_so_far

            extra = min(cap - held, res.count - bought_so_far)
            if extra <= 0:
                continue

            # Marginal cost of extra units beyond what we already committed to buy
            total_if_buy_all = StrategyUtils.get_resource_cost(res, bought_so_far + extra)
            cost_of_min = StrategyUtils.get_resource_cost(res, bought_so_far) if bought_so_far > 0 else 0
            if total_if_buy_all is None or cost_of_min is None:
                continue
            marginal = total_if_buy_all - cost_of_min

            # Scale back to what we can afford with leftover
            while extra > 0 and marginal > leftover:
                extra -= 1
                if extra > 0:
                    total_try = StrategyUtils.get_resource_cost(res, bought_so_far + extra)
                    marginal = (total_try - cost_of_min) if total_try is not None else leftover + 1
                else:
                    marginal = 0

            if extra > 0 and marginal <= leftover:
                purchases[res_type] = bought_so_far + extra
                leftover -= marginal

        return PlayerAction.resource_purchase(purchases)

    # =========================================================================
    # BUILD PHASE - The Key Decision
    # =========================================================================

    def choose_cities_to_build(self, player, game_state):
        """Build cheapest cities up to the number we can power."""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        my_cities = len(player.generators)
        my_power = self.get_max_power_capacity(player)
        want = max(0, my_power - my_cities)

        if want == 0:
            return PlayerAction.city_build([])

        # Sort available cities by cost (cheapest first)
        city_costs = [
            (c, StrategyUtils.calculate_city_cost(player, c, game_state))
            for c in available
        ]
        city_costs.sort(key=lambda x: x[1])

        # Buy cheapest cities up to our power capacity
        to_build = []
        budget = player.money
        for city, cost in city_costs:
            if len(to_build) >= want:
                break
            if budget >= cost:
                to_build.append(city)
                budget -= cost

        return PlayerAction.city_build(to_build)

    # =========================================================================
    # POWER PHASE
    # =========================================================================

    def choose_cities_to_power(self, player, game_state):
        """Power as many cities as possible. Track future-market removals."""
        # In steps 1 & 2, the highest future-market plant gets pushed to deck bottom
        # after this phase. Record its cities value so we know what left circulation.
        if game_state.step in (1, 2) and game_state.future_market:
            highest = max(game_state.future_market, key=lambda c: c.cost)
            self.removed_from_market.append(highest.cities)

        return PlayerAction.power_cities(len(player.generators))
