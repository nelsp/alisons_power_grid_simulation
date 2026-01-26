"""
EndgameSniper Strategy for Power Grid

An aggressive strategy focused on building power capacity and timing the endgame.
Tunable parameters allow testing different aggression levels.
"""

from player_action import PlayerAction
from player_strategies import Strategy, StrategyUtils


class EndgameSniper(Strategy):
    """
    Aggressive endgame strategy that:
    1. Acquires high-capacity plants early
    2. Builds cities to match power capacity  
    3. Triggers endgame when ahead on power
    """

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
    # AUCTION PHASE
    # =========================================================================

    def evaluate_plant(self, plant, player, game_state):
        """Score a plant based on power output and efficiency"""
        score = plant.cities * 15  # Base value per city powered
        
        # Green plants are gold - no fuel costs
        if plant.resource == 'green':
            score *= self.green_premium
        
        # Efficiency bonus
        if plant.resource_cost > 0:
            efficiency = plant.cities / plant.resource_cost
            score += efficiency * 8
        else:
            score += 20  # No fuel cost bonus
        
        # High capacity bonus in mid/late game
        if game_state.step >= 2 and plant.cities >= 4:
            score += plant.cities * 5
        
        # Penalty for nuclear if uranium is scarce
        if plant.resource == 'nuclear':
            uranium = game_state.resources.get('uranium')
            if uranium and uranium.count < 4:
                score -= 15
        
        return score

    def choose_auction_move(self, player, game_state):
        """Buy plants, but keep money for cities"""
        must_buy = game_state.round_num == 1
        
        # Reserve money for building cities (rough estimate)
        cities_needed = max(0, 10 - len(player.generators))
        city_reserve = cities_needed * 15  # ~15E per city average
        
        max_spend = player.money - city_reserve
        if max_spend < 3:
            max_spend = player.money // 2  # At least can spend half
        
        affordable = [p for p in game_state.current_market if p.cost <= max_spend]
        
        if not affordable:
            if must_buy:
                # Must buy - get cheapest we can afford
                affordable = StrategyUtils.get_affordable_plants(player, game_state.current_market)
            if not affordable:
                return PlayerAction.auction_pass()
        
        # Score plants
        scored = [(self.evaluate_plant(p, player, game_state), p) for p in affordable]
        scored.sort(reverse=True, key=lambda x: x[0])
        best_score, best = scored[0]
        
        capacity = self.get_max_power_capacity(player)
        
        # Determine discard if at capacity
        discard = None
        if len(player.cards) >= 3:
            worst = min(player.cards, key=lambda p: p.cost)
            # Only consider buying if new plant is better than our worst
            if best.cost > worst.cost:
                discard = worst
            else:
                # New plant not better than our worst - skip unless must buy
                if not must_buy:
                    return PlayerAction.auction_pass()
                discard = worst
        
        # Buy if: must, need capacity, or upgrading
        should_buy = (must_buy or 
                      capacity < 14 or 
                      len(player.cards) < 3 or
                      discard is not None)
        
        if should_buy:
            return PlayerAction.auction_open(best, best.cost, discard)
        
        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Bid on good plants, but don't overpay"""
        min_bid = current_bid + 1
        
        # Check if we need to discard
        discard = None
        if len(player.cards) >= 3:
            worst = min(player.cards, key=lambda p: p.cost)
            if plant.cost > worst.cost:
                discard = worst
            else:
                # Plant not better than our worst - don't bid
                return PlayerAction.auction_bid_pass()
        
        value = self.evaluate_plant(plant, player, game_state)
        max_bid = int(value * 0.9)
        
        if plant.resource == 'green' or plant.cities >= 5:
            max_bid = int(value * 1.1)
        
        if min_bid > player.money or min_bid > max_bid:
            return PlayerAction.auction_bid_pass()
        
        return PlayerAction.auction_bid(min_bid, discard)

    # =========================================================================
    # RESOURCE PHASE
    # =========================================================================

    def choose_resources(self, player, game_state):
        """Buy resources conservatively - save money for cities"""
        purchases = {}
        
        # Reserve significant money for building
        cities_to_build = max(0, 12 - len(player.generators))
        city_reserve = cities_to_build * 12
        budget = max(10, player.money - city_reserve)
        
        capacities = StrategyUtils.get_resource_capacities(player)
        
        for plant in sorted(player.cards, key=lambda p: p.cities, reverse=True):
            if plant.resource == 'green':
                continue
            
            # Determine resource type
            if plant.resource == 'nuclear':
                res_type = 'uranium'
            elif plant.resource == 'oil&gas':
                oil = game_state.resources.get('oil')
                gas = game_state.resources.get('gas')
                res_type = 'oil' if (oil and oil.count > 0) else 'gas'
            else:
                res_type = plant.resource
            
            if res_type not in game_state.resources:
                continue
            
            res = game_state.resources[res_type]
            current = player.resources.get(res_type, 0) + purchases.get(res_type, 0)
            cap = capacities.get(res_type, 0)
            
            # Buy just enough to fire once
            want = plant.resource_cost - current
            want = max(0, min(want, res.count, cap - current))
            
            if want > 0:
                cost = StrategyUtils.get_resource_cost(res, want)
                while want > 0 and (cost is None or cost > budget):
                    want -= 1
                    cost = StrategyUtils.get_resource_cost(res, want) if want > 0 else 0
                
                if want > 0 and cost:
                    purchases[res_type] = purchases.get(res_type, 0) + want
                    budget -= cost
        
        return PlayerAction.resource_purchase(purchases)

    # =========================================================================
    # BUILD PHASE - The Key Decision
    # =========================================================================

    def choose_cities_to_build(self, player, game_state):
        """Build strategically based on power capacity and opponent state"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])
        
        num_players = len(game_state.players)
        threshold = self.get_endgame_threshold(num_players)
        my_cities = len(player.generators)
        my_power = self.get_max_power_capacity(player)
        my_current_power = self.current_power_capacity(player)
        
        # Sort by cost
        city_costs = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) 
                      for c in available]
        city_costs.sort(key=lambda x: x[1])
        
        # What can we afford? Use most of our money for cities
        affordable = []
        budget = player.money - 3  # Keep minimal reserve
        for city, cost in city_costs:
            if budget >= cost:
                affordable.append(city)
                budget -= cost
        
        if not affordable:
            return PlayerAction.city_build([])
        
        # Opponent analysis
        opp_cities = [len(p.generators) for p in game_state.players if p != player]
        opp_power = [self.get_max_power_capacity(p) for p in game_state.players if p != player]
        max_opp_cities = max(opp_cities) if opp_cities else 0
        max_opp_power = max(opp_power) if opp_power else 0
        
        # Can we trigger and win?
        can_trigger = my_cities + len(affordable) >= threshold
        would_win = my_current_power > max_opp_power
        
        if can_trigger and would_win:
            # WIN NOW - build to threshold
            need = threshold - my_cities
            return PlayerAction.city_build(affordable[:need + 1])
        
        # Is someone close to triggering?
        someone_close = max_opp_cities >= threshold - 3
        
        if someone_close:
            # Build aggressively to match our power capacity
            target = min(len(affordable), my_power - my_cities)
            target = max(target, 2)
            return PlayerAction.city_build(affordable[:target])
        
        # Minimum cities we should have by round
        min_cities_by_round = {
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 9, 
            9: 11, 10: 13, 11: 14, 12: 15, 13: 16, 14: 17
        }
        min_target = min_cities_by_round.get(game_state.round_num, 10)
        
        # Target: max of (minimum growth, match opponents, approach power capacity)
        target_cities = max(min_target, max_opp_cities, my_power - 3)
        target_cities = min(target_cities, my_power + 2)  # Don't go too far past capacity
        
        to_build = target_cities - my_cities
        
        # Always build at least 1 if we can afford it
        if to_build <= 0 and len(affordable) > 0 and my_cities < threshold - 1:
            to_build = 1
        
        to_build = min(to_build, len(affordable))
        to_build = max(0, to_build)
        
        return PlayerAction.city_build(affordable[:to_build])

    # =========================================================================
    # POWER PHASE
    # =========================================================================

    def choose_cities_to_power(self, player, game_state):
        """Power as many cities as possible"""
        max_power = self.current_power_capacity(player)
        can_power = min(max_power, len(player.generators))
        return PlayerAction.power_cities(can_power)
