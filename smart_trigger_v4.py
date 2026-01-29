"""
SmartTriggerV4 - Single tweak: lower auction threshold (6 instead of 8)
"""

from player_strategies import Strategy, StrategyUtils
from player_action import PlayerAction


class SmartTriggerV4(Strategy):
    """
    SmartTrigger with ONE change: lower threshold for opening auctions (6 vs 8)
    """

    def __init__(self):
        self.thresholds = {2: 18, 3: 17, 4: 17, 5: 15, 6: 14}
        self.avg_build_cost_estimate = 25

    def get_endgame_threshold(self, num_players):
        return self.thresholds.get(num_players, 17)

    def evaluate_plant(self, plant, player, game_state):
        if plant.resource == 'green':
            return plant.cities * 30 + game_state.step * 10

        res_type = self._get_resource_type_for_plant(plant, game_state)
        if res_type not in game_state.resources:
            return plant.cities * 8

        res = game_state.resources[res_type]
        avg_price = self._get_avg_resource_cost(res)
        fuel_cost = plant.resource_cost * avg_price

        efficiency = (plant.cities ** 1.5) / max(1, fuel_cost)
        scarcity_mult = max(0.5, res.count / 15.0)
        step_bonus = game_state.step * 12
        future_bonus = (max(0, 15 - game_state.round_num) / 15) * 10

        hybrid_bonus = 8 if plant.resource == 'oil&gas' else 0
        nuclear_bonus = 12 if plant.resource == 'nuclear' else 0

        return efficiency * scarcity_mult * (1 + future_bonus / 10) + step_bonus + hybrid_bonus + nuclear_bonus

    def _get_resource_type_for_plant(self, plant, game_state):
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
        if not resource:
            return 12
        poss = resource.poss_purchases()
        if not poss:
            return 12
        return sum(poss.values()) / len(poss)

    def choose_auction_move(self, player, game_state):
        available_plants = game_state.current_market
        must_buy = game_state.round_num == 1

        affordable = StrategyUtils.get_affordable_plants(player, available_plants)
        if not affordable:
            return PlayerAction.auction_pass()

        plant_scores = [(self.evaluate_plant(p, player, game_state) - p.cost * 1.1, p) for p in affordable]
        plant_scores.sort(reverse=True)

        best_score, best_plant = plant_scores[0]
        
        # TWEAK: Lower threshold from 8 to 6
        if must_buy or best_score > 6:
            bid = max(best_plant.cost, min(player.money - 10, best_plant.cost + 3))
            discard = self._get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None
            return PlayerAction.auction_open(best_plant, bid, discard)

        return PlayerAction.auction_pass()

    def bid_in_auction(self, player, game_state, plant, current_bid, current_winner):
        """EXACT copy of original"""
        my_value = self.evaluate_plant(plant, player, game_state)
        min_bid = current_bid + 1

        if min_bid > player.money or my_value < min_bid * 1.15:
            return PlayerAction.auction_bid_pass()

        opp = game_state.players[current_winner]
        opp_value = self.evaluate_plant(plant, opp, game_state)
        overbid = 4 if opp_value > my_value * 1.2 else 1
        bid = min(min_bid + overbid, player.money)
        discard = self._get_least_valuable_plant(player, game_state) if len(player.cards) >= 3 else None
        return PlayerAction.auction_bid(bid, discard)

    def _get_least_valuable_plant(self, player, game_state):
        if not player.cards:
            return None
        dummy_resources = self._create_dummy_resources()
        dummy_gs = type('DummyGS', (), {'resources': dummy_resources, 'step': game_state.step, 'round_num': game_state.round_num})()
        return min(player.cards, key=lambda c: self.evaluate_plant(c, player, dummy_gs))

    def _create_dummy_resources(self):
        class DummyRes:
            def __init__(self, count=20):
                self.count = count
            def poss_purchases(self):
                return {1:4, 2:7, 3:10, 4:12}
        return {'coal': DummyRes(), 'oil': DummyRes(), 'gas': DummyRes(), 'uranium': DummyRes()}

    def choose_resources(self, player, game_state):
        """EXACT copy of original"""
        purchases = {}
        capacities = StrategyUtils.get_resource_capacities(player)
        my_cities = len(player.generators)
        is_late_order = my_cities <= min(len(p.generators) for p in game_state.players) + 1

        multiplier = 2.2 if is_late_order else 1.4
        if game_state.step >= 3 or game_state.round_num >= 10:
            multiplier *= 1.6

        for plant in sorted(player.cards, key=lambda c: self.evaluate_plant(c, player, game_state), reverse=True):
            if plant.resource == 'green':
                continue
            res_type = self._get_resource_type_for_plant(plant, game_state)
            if res_type not in game_state.resources:
                continue

            res = game_state.resources[res_type]
            current = player.resources.get(res_type, 0) + purchases.get(res_type, 0)
            space = capacities[res_type] - current
            if space <= 0:
                continue

            needed = plant.resource_cost * multiplier
            to_buy = min(needed, space, res.count)
            cost = StrategyUtils.get_resource_cost(res, to_buy)
            while to_buy > 0 and (cost is None or player.money < cost):
                to_buy -= 1
                if to_buy > 0:
                    cost = StrategyUtils.get_resource_cost(res, to_buy)
            if to_buy > 0:
                purchases[res_type] = purchases.get(res_type, 0) + to_buy

        return PlayerAction.resource_purchase(purchases)

    def choose_cities_to_build(self, player, game_state):
        """EXACT copy of original"""
        available = StrategyUtils.get_available_cities(player, game_state)
        if not available:
            return PlayerAction.city_build([])

        num_players = len(game_state.players)
        threshold = self.get_endgame_threshold(num_players)
        my_current = len(player.generators)
        my_plant_power = StrategyUtils.calculate_max_powered_cities(player)

        opps = [p for p in game_state.players if p != player]
        opp_potentials = []
        for opp in opps:
            opp_current = len(opp.generators)
            opp_plant = StrategyUtils.calculate_max_powered_cities(opp)
            opp_avail = StrategyUtils.get_available_cities(opp, game_state)
            opp_cities_cost = [(c, StrategyUtils.calculate_city_cost(opp, c, game_state)) for c in opp_avail]
            opp_cities_cost.sort(key=lambda x: x[1])
            opp_budget = opp.money
            opp_max_b = 0
            for _, cost in opp_cities_cost:
                if opp_budget >= cost:
                    opp_budget -= cost
                    opp_max_b += 1
                else:
                    break
            opp_post = min(opp_current + opp_max_b, opp_plant)
            opp_potentials.append(opp_post)

        my_max_b = 0
        my_cities_cost = [(c, StrategyUtils.calculate_city_cost(player, c, game_state)) for c in available]
        my_cities_cost.sort(key=lambda x: x[1])
        my_budget = player.money
        for _, cost in my_cities_cost:
            if my_budget >= cost:
                my_budget -= cost
                my_max_b += 1
            else:
                break
        my_potential_post_power = min(my_current + my_max_b, my_plant_power)

        max_opp_potential = max(opp_potentials) if opp_potentials else 0

        total_cities_built = sum(len(p.generators) for p in game_state.players)
        is_late_game = game_state.round_num >= 9 or total_cities_built >= 50 or game_state.step == 3
        will_be_final_approx = max_opp_potential >= threshold or my_potential_post_power >= threshold

        if will_be_final_approx or (is_late_game and my_potential_post_power > max_opp_potential):
            target_build = min(my_max_b, my_plant_power - my_current, threshold - my_current + 2)
        elif my_potential_post_power > max_opp_potential + 1:
            target_build = min(my_max_b, threshold - my_current)
        else:
            leader_cities = max(len(p.generators) for p in game_state.players)
            target_build = max(0, leader_cities - 1 - my_current)
            if player.money > 100:
                target_build = max(target_build, 2)
            if my_current == 0:
                target_build = max(target_build, 1)

        target_build = min(target_build, my_max_b, len(available))
        to_build = [c for c, _ in my_cities_cost[:target_build]]

        return PlayerAction.city_build(to_build)

    def choose_cities_to_power(self, player, game_state):
        max_powerable = StrategyUtils.get_max_powerable_cities(player)
        return PlayerAction.power_cities(max_powerable)
