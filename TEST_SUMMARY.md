# Power Grid Rule Compliance Test Summary

## Overview

This document summarizes the rule compliance testing framework created for the Power Grid simulation. The tests ensure the game follows Power Grid Deluxe rules for Europe map with 4 players.

## Files Created

1. **`test_rule_compliance.py`** - Comprehensive unit tests for all major game rules
2. **`validate_game_rules.py`** - Standalone script to validate log files from completed games
3. **`RULE_COMPLIANCE_TESTS.md`** - Documentation on how to use the tests

## Test Coverage

### Auction Phase Rules ✅
- First round: all players must buy a plant (cannot pass)
- Players cannot bid if they are the current high bidder
- Players cannot bid after passing
- Minimum bid validation (must be >= current_bid + 1)
- Opening bid must be >= plant cost

### Resource Purchase Rules ✅
- Cannot buy resources without owning appropriate plant
- Cannot exceed storage capacity (2x resource_cost per plant)
- Hybrid plants can store oil or gas

### Building Phase Rules ✅
- Step 1: Only 1 player per city
- Step 2: Up to 2 players per city
- Step 3: Up to 3 players per city
- Building costs: 10E (1st), 15E (2nd), 20E (3rd)

### Market Rules ✅
- Step 1-2: 4 plants in current market
- Step 3: 6 plants total in market
- Plants sorted by cost
- Plants with number <= city count removed

### Game Flow Rules ✅
- Player order: most cities, then largest plant
- Step 2 triggers at 7 cities (4 players)
- Game ends at 18 cities
- Winner: most cities powered, tie-breaker: most money

## Potential Bugs Identified

### 1. Auction: Current Winner Can Bid Again ⚠️

**Issue**: In `game_engine.py`, `run_plant_auction()` method (lines 362-412), when a player bids and becomes the `current_winner`, they remain in the `active_bidders` list. This means they could bid again in the next iteration, which violates Power Grid rules.

**Rules**: According to Power Grid rules, once you're the high bidder, you cannot bid again until someone else outbids you.

**Current Code**:
```python
# When player bids:
current_winner = player_idx  # Line 394
# Player remains in active_bidders list
```

**Expected Behavior**: The current winner should be excluded from active_bidders until someone else bids. Or, the loop should skip the current winner when iterating.

**Suggested Fix**: After line 395, add:
```python
# Remove current winner from active bidders temporarily
# They can only bid again after someone else bids
# (This is handled by the logic that resets active_bidders after each bid round)
```

Actually, the issue is more subtle. The loop structure means:
1. Player bids, becomes current_winner
2. Loop continues to next iteration
3. current_winner is still in active_bidders
4. They could bid again

The fix should prevent the current_winner from being in active_bidders for the next round. Or, modify the loop to skip the current_winner.

**Recommended Fix**: After setting `current_winner`, temporarily mark them so they're skipped in the next round, or remove them from active_bidders until someone else bids.

## How to Run Tests

### Unit Tests
```bash
pytest test_rule_compliance.py -v
```

### Log File Validation
```bash
python validate_game_rules.py
```

### Run Both
```bash
# Run tests
pytest test_rule_compliance.py -v

# Then validate log file
python validate_game_rules.py
```

## Test Results Interpretation

### ✅ All Tests Pass
The game engine correctly enforces all tested rules. You can run games with confidence.

### ❌ Some Tests Fail
- Review the failure messages
- Check the specific rule violation
- Fix the logic in `game_engine.py`
- Re-run tests to verify fix

### ⚠️ Log File Violations
If `validate_game_rules.py` finds violations:
1. Note the game state (round, phase) where violation occurred
2. Check the specific rule being violated
3. Review the auction/building/resource logic for that phase
4. Fix the bug and re-run a game to generate a new log

## Example: Testing for Auction Bug

To specifically test if the current winner can bid again:

```python
def test_current_winner_cannot_bid_again():
    """Test that current winner cannot bid again until outbid"""
    # Setup auction where player 1 bids
    # Verify player 1 cannot bid again on next iteration
    # Verify player 1 can only bid again after player 2 bids
```

This test would catch the potential bug mentioned above.

## Log File Checks

The `validate_game_rules.py` script checks:
- Player order correctness
- Auction state validity (current_winner not in active_bidders)
- Step-based city occupancy limits
- Market structure by step
- Player plant count (max 3)
- Player money (no negatives)
- Resource storage capacity
- Market sorting
- Step transition conditions
- Game end conditions

## Next Steps

1. **Run the tests** to identify any current rule violations
2. **Run a game** to generate a log file
3. **Validate the log file** to check for violations
4. **Fix any bugs** identified by the tests or log validation
5. **Re-run tests** to verify fixes

## Continuous Integration

These tests can be integrated into a CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run rule compliance tests
  run: pytest test_rule_compliance.py -v

- name: Run game and validate log
  run: |
    python run_game.py
    python validate_game_rules.py
```

## Contributing

When adding new game features or fixing bugs:
1. Add corresponding tests to `test_rule_compliance.py`
2. Update this document if new rules are tested
3. Ensure all tests pass before merging
