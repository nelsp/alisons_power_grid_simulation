# Power Grid Rule Compliance Tests

This directory contains comprehensive tests to ensure the Power Grid simulation follows the official Power Grid Deluxe rules for Europe map with 4 players.

## Test Files

### `test_rule_compliance.py`
Comprehensive unit tests covering all major game rules:
- **Auction Phase Rules**: Bid validation, passing rules, minimum bids
- **Resource Purchase Rules**: Plant ownership, storage capacity
- **Building Rules**: Step-based city occupancy limits, building costs
- **Market Rules**: Market structure by step, plant removal rules
- **Game Flow Rules**: Player order, step transitions, win conditions

### `validate_game_rules.py`
Standalone script to validate log files from completed games for rule violations.

## Running Tests

### Run Rule Compliance Tests
```bash
# Run all rule compliance tests
pytest test_rule_compliance.py -v

# Run specific test class
pytest test_rule_compliance.py::TestAuctionRuleCompliance -v

# Run with output
pytest test_rule_compliance.py -v -s
```

### Validate Log Files
```bash
# Validate the most recent game log
python validate_game_rules.py

# Or validate a specific log file (modify script)
python validate_game_rules.py
```

## Key Rules Being Tested

### 1. Auction Phase
- ✅ Players cannot bid if they were the last bidder (current winner)
- ✅ Players cannot bid after passing
- ✅ Minimum bid must be at least plant cost for opening bid
- ✅ Bids must be higher than current bid
- ✅ First round: all players must buy a plant (cannot pass)

### 2. Resource Purchase
- ✅ Can only buy resources for plants you own
- ✅ Cannot exceed storage capacity (2x resource cost per plant)
- ✅ Hybrid plants can store oil or gas (shared capacity)

### 3. Building Phase
- ✅ Step 1: Only 1 player per city
- ✅ Step 2: Up to 2 players per city
- ✅ Step 3: Up to 3 players per city
- ✅ Building costs: 10E (1st), 15E (2nd), 20E (3rd)

### 4. Power Plant Market
- ✅ Step 1-2: 4 plants in current market, rest in future market
- ✅ Step 3: 6 plants total in market (no future market)
- ✅ Plants sorted by cost (ascending)
- ✅ Plants with number <= city count must be removed

### 5. Game Flow
- ✅ Player order: most cities (descending), tie-breaker: largest plant
- ✅ Step 2 triggers when a player reaches 7 cities (4 players)
- ✅ Game ends when someone reaches 18 cities
- ✅ Winner: most cities powered, tie-breaker: most money

### 6. Resource Storage
- ✅ Maximum 3 plants per player
- ✅ Resources cannot exceed 2x capacity per plant
- ✅ Resources must be removed when discarding plants that stored them

## Example Test Output

### Successful Test Run
```
test_rule_compliance.py::TestAuctionRuleCompliance::test_first_round_must_buy PASSED
test_rule_compliance.py::TestAuctionRuleCompliance::test_cannot_bid_when_current_winner PASSED
test_rule_compliance.py::TestResourcePurchaseRules::test_cannot_buy_resources_without_plant PASSED
...
```

### Log File Validation
```
Validating 150 game states from power_grid_game_log.json...
✅ No rule violations found in 150 game states!
```

### Rule Violation Detection
```
❌ Found 2 rule violations:

  1. round_5_after_auction: Auction violation - Current winner 2 is in active_bidders [1, 2]
  2. round_8_after_build: Step 2 violation - City Paris has 3 players (max allowed: 2)
```

## Known Issues to Watch For

### Potential Bugs in Auction Logic
1. **Current Winner Can Bid Again**: The auction loop may allow the current high bidder to bid again. The rules state that once you're the high bidder, you cannot bid again until someone else outbids you.

2. **Active Bidders List**: After a player bids and becomes the current winner, they should be removed from active_bidders until someone else bids.

### How to Fix
If violations are found:
1. Check the specific rule violation message
2. Review the relevant code in `game_engine.py`
3. Fix the logic to enforce the rule
4. Re-run tests to verify the fix

## Contributing New Tests

To add new rule tests:

1. Identify the rule from Power Grid Deluxe rulebook
2. Create a test method in the appropriate test class
3. Use `MockStrategy` to control player actions
4. Verify the rule is enforced
5. Document any edge cases

Example:
```python
def test_new_rule(self, sample_cards, sample_resources, simple_board):
    """Test that new rule is followed"""
    # Setup game state
    # Execute action
    # Assert rule compliance
```

## References

- Power Grid Deluxe Rules (included PDF)
- Europe map specific rules
- 4-player game configuration
