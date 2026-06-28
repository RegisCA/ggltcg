# Backend Scripts

## Game Analysis Tools

### diagnose_ai_game.py

Quick diagnostic tool for analyzing AI V4 game failures.

**Usage**:
```bash
# Analyze specific turn
python backend/scripts/diagnose_ai_game.py <game_id> <turn_number>

# Analyze all turns in a game
python backend/scripts/diagnose_ai_game.py <game_id>
```

**Examples**:
```bash
# Analyze Turn 3 of game be31bc7d
python backend/scripts/diagnose_ai_game.py be31bc7d-3be9-4cae-af35-f5ffd5fe9d14 3

# Analyze all turns in game 4d80a9c6
python backend/scripts/diagnose_ai_game.py 4d80a9c6-2b9d-402a-b7fb-db9d37dc18aa
```

**Features**:
- 🔴 **CC Hallucination Detection**: Automatically detects when AI claims wrong CC amount
- 🟠 **Illegal Sequence Identification**: Finds sequences that exceed available CC
- 🟡 **Execution Failures**: Shows which actions failed during execution
- 📊 **Strategy Analysis**: Displays AI's reasoning and selected sequences
- ⚡ **Fast**: Uses production API, no database access needed

**Output Example**:
```
============================================================
TURN 3 ANALYSIS
============================================================
AI Version: 4
CC Available: 5
CC Claimed (Request 1): 8
  ⚠️  MISMATCH: Delta of 3 CC

🚨 ISSUES FOUND: 2

🔴 CC_HALLUCINATION (CRITICAL)
   AI claimed 8 CC but actually had 5 CC (delta: 3)

🟠 ILLEGAL_SEQUENCES (HIGH)
   3/8 sequences exceed available CC
     - Sequence 0: 7 CC (exceeds 5 CC)
     - Sequence 6: 6 CC (exceeds 5 CC)
```

**Requirements**:
- Python 3.8+
- `requests` library (`pip install requests`)
- Access to production API (https://ggltcg.onrender.com)

**Related Documentation**:
- [AI Current State](../../docs/development/ai/AI_CURRENT_STATE.md)
- [AI V4 Improvements Tracking (archived)](../../docs/development/ai/archive/AI_V4_IMPROVEMENTS_TRACKING.md)
