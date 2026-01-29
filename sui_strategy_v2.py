"""
SuiStrategyV2 - Improved Power Grid Strategy

Key improvements based on test results:
1. Fixed Card comparison bugs
2. Better plant evaluation (like SmartTriggerStrategy)
3. Predictive endgame triggering
4. Anti-deadlock logic
5. Smarter resource stockpiling based on turn order
"""

from player_strategies import Strategy, StrategyUtils
from player_action import PlayerAction


class SuiStrategyV2(Strategy):
    """
    Improved strategy that learns from SmartTriggerStrategy's success.
    Focus: Win the power comparison when endgame triggers.
    """
    
    def __init__(self):
        self.thresholds = {2: 18, 3: 17, 4: 17, 5: 15, 6: 14}
    
    def get_endgame_threshold(self, num_players):
        return self.thresholds.get(num_players, 17)
    
    def evaluate_plant(self, plant, player, game_state):
        """
        Score plants based on efficiency, resource availability, and game stage.
        Higher score = more valuable.
        """
        if plant.resource == 'green':
            # Green plants are premium - no fuel costs
            return plant.cities * 30 + game_state.step * 10
        
        # Get resource type and cost
        res_type = self._get_resource_type(plant, game_state)
        if res_type not in game_state.resources:
            return plant.cities * 8  # Fallback
        
        res = game_state.resources[res_type]
        avg_price = self._get_avg_resource_cost(res)
        fuel_cost = plant.resource_cost * avg_price
        
        # Efficiency: cities per fuel cost with diminishing returns
        efficiency = (plant.cities ** 1.5) / max(1, fuel_cost)
        
        # Resource scarcity multiplier
        scarcity_mult = max(0.5, res.count / 15.0)
        
        # Stage bonus - plants more valuable as game progresses
        step_bonus = game_state.step * 12
        
        # Early game bonus for future value
        future_bonus = (max(0, 15 - game_state.round_num) / 15) * 10
        
        # Type bonuses
        hybrid_bonus = 8 if plant.resource == 'oil&gas' else 0
        nuclear_bonus = 12 if plant.resource == 'nuclear' else 0
        
        return efficiency * scarcity_mult * (1 + future_bonus / 10) + step_bonus + hybrid_bonus + nuclear_bonus
    
    def _get_resource_type(self, plant, game_state):
        """Get the resource type for a plant (handling hybrids)"""
        if plant.resource == 'nuclear':
            return 'uranium'
        if plant.resource == 'oil&gas':
            oil = game_state.resources.get('oil')
            gas = game_state.resources.get('gas')
            oil_avg = self._get_avg_resource_cost(oil) if oil else 99
            gas_avg = self._get_avg_resource_cost(gas) if gas else 99
            return 'oil' if oil_avg < gas_avg else 'gas'
        return plant.resource
    
    def _get_avg_resource_cost(self, resource):
        """Calculate average cost per unit"""
        if not resource:
            return 12
        poss = resource.poss_purchases()
        if not poss:
            return 12
        return sum(poss.values()) / len(poss)
    
    def _get_least_valuable_plant(self, player, game_state):
        """Find the plant with lowest value to discard"""
        if not player.cards:
            return None
        # Use cost as simple proxy to avoid comparison issues
        return min(player.cards, key=lambda c: c.cost)
    
    def choose_auction_move(self, player, game_state):
        """Buy plants with good value scores"""
        available_plants = game_state.current_market
        must_buy = game_state.round_num == 1
        
        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()
        
        # Score plants by value minus cost penalty
        plant_scores = []
        for p in affordable:
            value = self.evaluate_plant(p, player, game_state)
            score = value - p.cost * 1.1  # Cost penalty
            plant_scores.append((score, p))
        
        plant_scores.sort(reverse=True)
        best_score, best_plant = plant_scores[0]
        
        # Buy if must buy or good value
        if must_buy or best_score > 8:
            # Determine bid
            bid = max(best_plant.cost, min(player.money - 10, best_plant.cost + 3))
            
            # Determine discard if needed
            discard = None
            if len(player.cards) >= 3:
                # Check if new plant is better than worst owned
                worst = min(player.cards, key=lambda c: c.cost)
                if best_plant.cost > worst.cost:
                    discard = worst
                else:
                    return PlayerAction.auction_pass()
            
            return PlayerAction.auction_open(best_plant, bid, discard)
        
        return PlayerAction.auction_pass()
    
    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """Bid based on plant value vs cost"""
        my_value = self.evaluate_plant(plant, player, game_state)
        min_bid = current_bid + 1
        
        if min_bid > player.money:
            return PlayerAction.auction_bid_pass()
        
        # Only bid if value exceeds bid
        if my_value < min_bid * 1.15:
            return PlayerAction.auction_bid_pass()
        
        # Check opponent value - overbid if they want it badly
        opponent = game_state.players[current_winner]
        opp_value = self.evaluate_plant(plant, opponent, game_state)
        overbid = 4 if opp_value > my_value * 1.2 else 1
        
        bid = min(min_bid + overbid, player.money)
        
        # Discard if needed
        discard = None
        if len(player.cards) >= 3:
            worst = min(player.cards, key=lambda c: c.cost)
            if plant.cost > worst.cost:
                discard = worst
            else:
                return PlayerAction.auction_bid_pass()
        
        return PlayerAction.auction_bid(bid, discard)
    
    def choose_resources(self, player, game_state):
        """Buy resources with stockpiling when in good turn order"""
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)
        
        # Check turn order - fewer cities = earlier = cheaper resources
        my_cities = len(player.generators)
        min_cities = min(len(p.generators) for p in game_state.players)
        is_late_order = my_cities <= min_cities + 1
        
        # Multiplier based on turn order and game stage
        multiplier = 2.2 if is_late_order else 1.4
        if game_state.step >= 3 or game_state.round_num >= 10:
            multiplier *= 1.6  # Stockpile late game
        
        # Sort plants by value to fuel best ones first
        sorted_plants = sorted(
            player.cards, 
            key=lambda c: self.evaluate_plant(c, player, game_state), 
            reverse=True
        )
        
        for plant in sorted_plants:
            if plant.resource == 'green':
                continue
            
            res_type = self._get_resource_type(plant, game_state)
            if res_type not in game_state.resources:
                continue
            
            res = game_state.resources[res_type]
            current = player.resources.get(res_type, 0) + purchases.get(res_type, 0)
            space = capacities[res_type] - current
            
            if space <= 0:
                continue
            
            # Calculate how much to buy
            needed = plant.resource_cost * multiplier
            to_buy = int(min(needed, space, res.count))
            
            if to_buy <= 0:
                continue
            
            # Check affordability
            cost = StrategyUtils.get_resource_cost(res, to_buy)
            while to_buy > 0 and (cost is None or player.money < cost):
                to_buy -= 1
                if to_buy > 0:
                    cost = StrategyUtils.get_resource_cost(res, to_buy)
            
            if to_buy > 0 and cost is not None:
                purchases[res_type] = purchases.get(res_type, 0) + to_buy
        
        return PlayerAction.resource_purchase(purchases)
    
    def choose_cities_to_build(self, player, game_state):
        """Build cities with predictive endgame triggering"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])
        
        num_players = len(game_state.players)
        threshold = self.get_endgame_threshold(num_players)
        my_current = len(player.generators)
        my_power = StrategyUtils.calculate_max_powered_cities(player)
        
        # Calculate opponent potential builds
        opps = [p for p in game_state.players if p != player]
        opp_potentials = []
        for opp in opps:
            opp_current = len(opp.generators)
            opp_power = StrategyUtils.calculate_max_powered_cities(opp)
            
            # Estimate how many cities opp can build
            opp_avail = StrategyUtils.get_available_cities(opp, game_state)
            opp_costs = [(c, StrategyUtils.calculate_city_cost(opp, c, game_state)) 
                        for c in opp_avail]
            opp_costs.sort(key=lambda x: x[1])
            
            opp_budget = opp.money
            opp_max_build = 0
            for _, cost in opp_costs:
                if opp_budget >= cost:
                    opp_budget -= cost
                    opp_max_build += 1
                else:
                    break
            
            opp_potential = min(opp_current + opp_max_build, opp_power)
            opp_potentials.append(opp_potential)
        
        # Calculate my potential
        my_costs = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) 
                   for c in available]
        my_costs.sort(key=lambda x: x[1])
        
        my_budget = player.money
        my_max_build = 0
        for _, cost in my_costs:
            if my_budget >= cost:
                my_budget -= cost
                my_max_build += 1
            else:
                break
        
        my_potential = min(my_current + my_max_build, my_power)
        max_opp_potential = max(opp_potentials) if opp_potentials else 0
        
        # Check if game is late
        total_cities = sum(len(p.generators) for p in game_state.players)
        is_late = game_state.round_num >= 9 or total_cities >= 50 or game_state.step == 3
        will_end = max_opp_potential >= threshold or my_potential >= threshold
        
        # Decide how many to build
        if will_end or (is_late and my_potential > max_opp_potential):
            # Endgame trigger - build to max powerable
            target = min(my_max_build, my_power - my_current, threshold - my_current + 2)
        elif my_potential > max_opp_potential + 1:
            # Can dominate - trigger now
            target = min(my_max_build, threshold - my_current)
        else:
            # Normal play - lag behind leader by 1
            leader = max(len(p.generators) for p in game_state.players)
            target = max(0, leader - 1 - my_current)
            
            # Minimum expansion if flush with cash
            if player.money > 100:
                target = max(target, 2)
            if my_current == 0:
                target = max(target, 1)
        
        target = min(target, my_max_build, len(available))
        to_build = [c for c, _ in my_costs[:target]]
        
        return PlayerAction.city_build(to_build)
    
    def choose_cities_to_power(self, player, game_state):
        """Always power maximum cities"""
        max_powerable = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(max_powerable)
