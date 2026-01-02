# AI V4 Design: Dual-Request with Contextual Examples

**Date**: January 2, 2026  
**Status**: Ready for Implementation  
**Authors**: Based on lessons learned from V3/V3.2 failures  
**Reviewed by**: Gemini 3 Flash (feedback incorporated)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background: Why V4](#background-why-v4)
3. [Architecture](#architecture)
4. [Temperature Strategy](#temperature-strategy)
5. [Contextual Example Library](#contextual-example-library)
6. [Implementation Steps](#implementation-steps)
7. [Prompt Structures](#prompt-structures)
8. [Success Metrics](#success-metrics)
9. [Developer Guidelines](#developer-guidelines)
10. [File Reference](#file-reference)

---

## Executive Summary

**Problem**: V3/V3.2 asked a single LLM request to do too much (understand state + generate sequences + validate legality + select strategically). Result: 12k+ char prompts still produced illegal actions.

**Solution**: Split into two focused requests:
- **Request 1**: Generate LEGAL sequences only (~4k chars) — mechanics-focused, low temperature
- **Request 2**: Select STRATEGICALLY with 3 contextual examples (~5k chars) — strategy-focused, higher temperature

**Model**: `gemini-2.5-flash` for both requests (better reasoning than flash-lite)

**Measurement**: Simulation-based metrics — CC efficiency, average game length, v2 fallback rate

**Key Insight**: This design shifts the LLM from being a "Game Engine" (which it isn't) to being a "Game Strategist" (which it is), offloading rigid math and rule-checking to deterministic server-side validators.

---

## Background: Why V4

### V3/V3.2 Failure Analysis

| Version | Prompt Size | Approach | Result |
|---------|-------------|----------|--------|
| V3.0 | 13.5k chars | "Explore all possibilities" | Same errors despite 3x mentions |
| V3.2 | 12.3k chars | "PRIORITY 1-5 directive" | Worse than V2 in user testing |

**Root Cause**: Information overload + competing concerns = execution discipline failure.

Key insight: "STR > 0 was mentioned 3 times but violated repeatedly. Information wasn't the problem."

LLMs frequently fail at math when they are simultaneously trying to be "clever" or "strategic." The solution is separation of concerns.

### What Works

- V2 single-action selection: Reliable but limited (not acceptable as primary solution)
- Dynamic card guidance loading (YAML): Only relevant cards included
- Existing validators: CC budget, suicide attack, opponent toy tracking
- Simulation system: Can measure outcomes across many games

### Design Principles (MUST FOLLOW)

1. **Separation of concerns** — Mechanics (Request 1) separate from strategy (Request 2)
2. **Dynamic loading over static embedding** — Load only relevant guidance/examples
3. **Concrete examples over abstract rules** — Show, don't tell
4. **Positive patterns over anti-patterns** — "ALWAYS do X" not "DON'T do Y"
5. **Small focused prompts** — Each request has ONE job
6. **Validate before selecting** — Request 2 only sees legal options
7. **Task at the end** — Place `<task>` XML tag at the bottom of every prompt

---

## Architecture

```
Game State
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  REQUEST 1: Sequence Generation                              │
│  ─────────────────────────────────────────────────────────   │
│  Model: gemini-2.5-flash                                    │
│  Temperature: 0.2 (deterministic, rule-following)           │
│  Prompt: ~4k chars (XML-structured)                         │
│  Output: JSON array of 5-10 sequences with tactical labels  │
│                                                              │
│  Focus: Generate LEGAL sequences only                       │
│  NO strategy, NO examples — just mechanics                  │
│  Must output: total_cc_spent for each sequence              │
│  Must vary: aggressive, defensive, resource-building        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ (server-side validation via TurnPlanValidator)
    │
    ▼ (filtered valid sequences — guaranteed legal)
    │
    ▼ (add tactical labels: [Aggressive Removal], [Board Setup], etc.)
    │
┌─────────────────────────────────────────────────────────────┐
│  REQUEST 2: Strategic Selection                              │
│  ─────────────────────────────────────────────────────────   │
│  Model: gemini-2.5-flash                                    │
│  Temperature: 0.7 (allows weighing tempo vs efficiency)     │
│  Prompt: ~5k chars (XML-structured + 3 examples)            │
│  Output: JSON {selected_index, reasoning}                   │
│                                                              │
│  Focus: Pick the WINNING sequence                           │
│  Uses 3 contextual examples relevant to current game        │
│  Prioritizes combo examples when multiple key cards present │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Selected Plan → Execution (existing TurnPlanner flow)
```

### Why Two Requests?

| Single Request (V3) | Dual Request (V4) |
|---------------------|-------------------|
| Must understand AND generate AND validate AND select | Each request has ONE job |
| 12k+ chars with competing instructions | ~4k + ~5k focused prompts |
| Validation mixed with strategy | Validation happens BETWEEN requests |
| Examples buried in noise | Examples are the focus of Request 2 |
| Single temperature for all tasks | Optimized temperature per task |

---

## Temperature Strategy

**Critical Insight**: Different tasks require different temperature settings.

| Request | Temperature | Rationale |
|---------|-------------|-----------|
| Request 1 (Generator) | 0.2 | Deterministic rule-following. We want consistent, legal sequences. |
| Request 2 (Selector) | 0.7 | Creative weighing of tempo vs efficiency vs aggression. |

**Fallback Strategy**: If Request 1 yields 0 valid sequences after validation, retry once with `temperature=1.0` before falling back to V2 single-action mode.

---

## Contextual Example Library

### Design Philosophy

Examples should be **contextual and relevant**:
- No point showing Knight examples if Knight isn't in the game
- Turn 1 guidance is irrelevant on Turn 8
- **Combo examples** take priority when multiple key cards are present

### Example Selection Logic

```python
def get_relevant_examples(game_state: GameState, player_id: str) -> list[str]:
    """Return exactly 3 examples relevant to current game state."""
    examples = []
    player = game_state.players[player_id]
    card_names = {c.name for c in player.hand + player.in_play}
    turn = game_state.turn_number
    
    # 1. Check for COMBO examples first (highest priority)
    if "Surge" in card_names and "Knight" in card_names:
        examples.append(COMBO_EXAMPLES["surge_knight"])
    elif "Archer" in card_names and any_low_sta_opponent:
        examples.append(COMBO_EXAMPLES["archer_finish"])
    
    # 2. Add phase-based example (always include one)
    if turn <= 3:
        examples.append(PHASE_EXAMPLES["early_game"])
    elif turn <= 6:
        examples.append(PHASE_EXAMPLES["mid_game"])
    else:
        examples.append(PHASE_EXAMPLES["end_game"])
    
    # 3. Fill remaining slots with card-specific examples
    CARD_PRIORITY = ["Knight", "Archer", "Surge", "Paper Plane", "Drop", "Wake"]
    for card_name in CARD_PRIORITY:
        if len(examples) >= 3:
            break
        if card_name in card_names and card_name in CARD_EXAMPLES:
            # Don't duplicate if already in combo example
            if not any(card_name in ex for ex in examples):
                examples.append(CARD_EXAMPLES[card_name])
    
    # 4. Pad with generic efficiency example if needed
    while len(examples) < 3:
        examples.append(GENERIC_EXAMPLES["efficiency"])
    
    return examples[:3]
```

### Example Categories

**Combo Examples** (selected when multiple synergistic cards present):

| Combo | Cards Required | Key Teaching |
|-------|----------------|--------------|
| `surge_knight` | Surge + Knight | CC bridging enables Knight + extra plays |
| `surge_double_play` | Surge + any 2 toys | Turn 1 board presence maximization |
| `archer_finish` | Archer + low-STA opponent | Chip to 0 for guaranteed removal |
| `knight_cleanup` | Knight + direct_attack possible | Auto-win then direct attack sequence |

**Phase Examples** (one always included based on turn number):

| Phase | Turns | Key Teaching |
|-------|-------|--------------|
| `early_game` | 1-3 | Board building, CC efficiency, avoid traps (Drop T1) |
| `mid_game` | 4-6 | Pressure with toy advantage, favorable trades |
| `end_game` | 7+ | Lethal detection, closing sequences |

**Card Examples** (fill remaining slots):

| Card | Example Name | Key Teaching |
|------|--------------|--------------|
| Knight | `knight_auto_win` | Always tussle on YOUR turn — auto-wins |
| Archer | `archer_chip_to_zero` | 3x activate_ability on 3 STA = auto-sleep |
| Surge | `surge_enables_combo` | +1 CC unlocks plays that seemed impossible |
| Paper Plane | `bypass_direct_attack` | direct_attack even with opponent toys (special) |
| Drop | `drop_needs_target` | Useless Turn 1 as P1 — no opponent toys |
| Wake | `wake_then_play` | activate_ability Wake → returns card → then play it |

### File Structure

```
backend/src/game_engine/ai/prompts/examples/
├── __init__.py
├── combo_examples.py    # Surge+Knight, Archer+finish, etc.
├── phase_examples.py    # Early/mid/end game patterns
├── card_examples.py     # Per-card tactical patterns
└── loader.py            # Selection logic with combo priority
```

---

## Implementation Steps

### Step 1: Establish Baseline Metrics

**Goal**: Quantify current V3.2 performance before making changes.

**Add to `backend/src/simulation/config.py`**:
```python
@dataclass
class GameResult:
    # ... existing fields ...
    total_cc_spent_by_winner: int = 0
    illegal_action_count: int = 0
    v2_fallback_count: int = 0
    # NEW: Average game length metric
    # (already have turn_count, just need to aggregate)
```

**Run baseline**: 50 games with V3.2 + gemini-2.5-flash-lite

---

### Step 2: Create Contextual Example Library

**Goal**: Build example library with combo detection.

**Files to create**:
- `examples/__init__.py`
- `examples/combo_examples.py` — Surge+Knight, etc.
- `examples/phase_examples.py` — Early/mid/end game
- `examples/card_examples.py` — Individual card patterns
- `examples/loader.py` — Selection with combo priority

**Key requirement**: Combo examples take priority over individual card examples.

---

### Step 3: Implement Request 1 — Sequence Generator

**Goal**: Generate 5-10 LEGAL action sequences with diversity.

**File**: `backend/src/game_engine/ai/prompts/sequence_generator.py`

**Requirements**:
- Temperature: 0.2 (deterministic)
- Zero strategic guidance in prompt
- Must output `total_cc_spent` for each sequence
- Must generate diverse sequences (aggressive, defensive, resource-building)
- Instruct to find "every path that ends with CC ≥ 0"

**Diversity Filter**: If generator produces 10 nearly identical sequences, the strategist won't have a real choice. Prompt must request mix of approaches.

---

### Step 4: Add Tactical Labels (Between Requests)

**Goal**: Help Request 2 understand what each sequence is doing.

After validation, label each sequence:
- `[Aggressive Removal]` — Prioritizes tussles/direct attacks
- `[Board Setup]` — Plays toys without attacking
- `[Resource Building]` — Plays Surge/Rush for CC advantage
- `[Lethal Attempt]` — Could win this turn
- `[Conservative]` — Minimal CC spent

---

### Step 5: Implement Request 2 — Strategic Selector

**Goal**: Select the BEST sequence from validated candidates.

**File**: `backend/src/game_engine/ai/prompts/strategic_selector.py`

**Requirements**:
- Temperature: 0.7 (creative weighing)
- Include exactly 3 contextual examples
- Sequences prefixed with tactical labels
- `<task>` tag at very bottom of prompt

---

### Step 6: Wire Up V4 in TurnPlanner

**Modify**: `backend/src/game_engine/ai/turn_planner.py`

**Changes**:
1. Add `PLANNING_VERSION=4.0` support
2. Implement dual-request flow with temperature settings
3. Track `v2_fallback_count`
4. Implement retry with temp=1.0 before V2 fallback

---

### Step 7: Run Comparison Simulation

**Compare**:
- CC efficiency (lower is better)
- **Average game length** (lower is better — strategic skill)
- V2 fallback rate (lower is better)
- Illegal action rate (lower is better)

---

## Prompt Structures

### Request 1: Sequence Generator (~4k chars)

```xml
<system>You are a MOVE GENERATOR for a card game. Generate LEGAL action sequences only. Do NOT optimize for strategy.</system>

<rules>
  <win_condition>Sleep all 6 opponent cards</win_condition>
  <zones>HAND (playable) → IN_PLAY (can attack) → SLEEP (out of game)</zones>
  
  <actions>
    <action type="play_card" cost="card_cost">Play card from hand to in_play</action>
    <action type="tussle" cost="2">
      Attack opponent toy. Requires: your toy has STR greater than 0.
      Combat: Attacker gets +1 SPD. Higher SPD strikes first.
    </action>
    <action type="direct_attack" cost="2">
      Attack opponent directly. Requires: your toy has STR greater than 0 AND opponent has 0 toys in play.
    </action>
    <action type="activate_ability" cost="varies">Use card's special ability</action>
    <action type="end_turn" cost="0">End your turn (always valid)</action>
  </actions>
  
  <constraints>
    <constraint>Total CC spent must not exceed CC available</constraint>
    <constraint>STR must be greater than 0 for tussle or direct_attack</constraint>
    <constraint>direct_attack requires opponent to have exactly 0 toys in play</constraint>
    <constraint>Each sequence must end with end_turn</constraint>
  </constraints>
</rules>

<current_state>
  <turn>{turn_number}</turn>
  <your_cc>{cc_available}</your_cc>
  
  <your_hand>
    {formatted_hand_with_restrictions}
  </your_hand>
  
  <your_toys>
    {formatted_in_play_with_restrictions}
  </your_toys>
  
  <opponent_toys>
    {formatted_opponent_in_play}
  </opponent_toys>
</current_state>

<task>
Generate 5-10 different LEGAL action sequences.
Each sequence must end with end_turn.
VARY the sequences: include aggressive (attacks), defensive (board setup), and resource-building options.
Output total_cc_spent for each sequence.
Focus on finding every legal path where CC ends at 0 or above.
</task>
```

**Card Restriction Formatting** (prevents "role blindness"):
```
Archer (ID: 7b9a) [RESTRICTION: CANNOT ATTACK - 0 STR] — Stats: 0/0/5
Paper Plane (ID: 3c2d) [SPECIAL: Can bypass blockers] — Stats: 2/2/1
```

---

### Request 2: Strategic Selector (~5k chars)

```xml
<system>You select the BEST action sequence to WIN the game efficiently.</system>

<goal>
Select the sequence that maximizes your chance of winning.
Priority order:
1. LETHAL — Can you win THIS turn? Always check first.
2. REMOVAL — Sleep opponent's toys to reduce their threats.
3. TEMPO — Build board advantage (more toys than opponent).
4. EFFICIENCY — Spend less CC per card slept.
</goal>

<metrics>
  <metric name="cc_efficiency">CC spent per card slept. Lower is better. Target: under 3.0</metric>
  <metric name="board_advantage">Your toys minus opponent toys. Higher is better.</metric>
  <metric name="lethal_check">Can you sleep ALL remaining opponent cards this turn?</metric>
</metrics>

<game_phase>{early_game|mid_game|end_game}</game_phase>

<examples>
{example_1_xml}

{example_2_xml}

{example_3_xml}
</examples>

<current_situation>
  <turn>{turn_number}</turn>
  <your_cc>{cc_available}</your_cc>
  <opponent_cards_remaining>{total_opponent_cards}</opponent_cards_remaining>
  <opponent_toys_in_play>{opponent_in_play_count}</opponent_toys_in_play>
  <your_toys_in_play>{your_in_play_count}</your_toys_in_play>
</current_situation>

<valid_sequences>
{sequences_with_tactical_labels}
</valid_sequences>

<task>
Select the best sequence by its index (0-based).
Explain your reasoning, referencing the examples if relevant.
</task>
```

---

## Success Metrics

| Metric | How to Measure | Baseline (V3.2) | Target (V4) |
|--------|----------------|-----------------|-------------|
| CC Efficiency | `winner_cc_spent / 6` | TBD | < 4.0 CC/card |
| **Avg Game Length** | `mean(turn_count)` for wins | TBD | Lower = better strategic skill |
| V2 Fallback Rate | `v2_fallbacks / total_turns` | TBD | < 5% |
| Illegal Action Rate | `rejected_actions / total_actions` | TBD | < 2% |
| Win Rate | Simulation vs same opponent | TBD | ≥ baseline |

**Key Insight**: CC Efficiency measures tactical skill, but **Average Game Length** measures strategic skill. An AI might be efficient at sleeping cards but play too slowly. Both metrics matter.

---

## Developer Guidelines

### Before You Start

1. **Read the full codebase** for any file you're modifying
2. **Run existing tests** before making changes
3. **Check for existing helpers** — don't reinvent:
   - `format_game_state_for_ai()` in `prompts/__init__.py`
   - `format_hand_for_planning_v3()` in `planning_prompt_v3.py`
   - `format_in_play_for_planning_v3()` in `planning_prompt_v3.py`
   - `TurnPlanValidator` in `validators/turn_plan_validator.py`

### Running the Backend

```bash
cd backend
source ../.venv/bin/activate  # Note: venv is at project root
python run_server.py
```

### Running Tests

```bash
# All AI planning tests (requires GOOGLE_API_KEY)
cd backend
source ../.venv/bin/activate
pytest tests/test_ai_turn1_planning.py -v

# Specific test
pytest tests/test_ai_turn1_planning.py -v -k "surge_knight"

# Unit tests only (no API calls)
pytest tests/test_prompt_compression.py -v
pytest tests/test_llm_player_v3.py -v
```

### Environment Variables

In `backend/.env`:
```bash
PLANNING_VERSION=4.0          # Use V4 dual-request
GEMINI_MODEL=gemini-2.5-flash # Better reasoning
GOOGLE_API_KEY=your_key_here # Available in backend/.env
```

### Commit Checklist

Before committing:
- [ ] `pytest tests/test_prompt_compression.py -v` passes
- [ ] `pytest tests/test_llm_player_v3.py -v` passes
- [ ] At least 3 integration tests pass (with API key)
- [ ] No hardcoded values that should be in config
- [ ] Prompt sizes logged and within targets (<4k, <5k)
- [ ] Card restrictions formatted in bold uppercase after card name

---

## File Reference

### Existing Files to READ (don't modify without understanding)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `backend/src/game_engine/ai/turn_planner.py` | Plan orchestration | `create_plan()`, `_call_planning_api()` |
| `backend/src/game_engine/ai/prompts/__init__.py` | Shared helpers | `format_game_state_for_ai()` |
| `backend/src/game_engine/ai/prompts/planning_prompt_v3.py` | V3 reference | `format_hand_for_planning_v3()` |
| `backend/src/game_engine/ai/validators/turn_plan_validator.py` | Plan validation | `TurnPlanValidator` |
| `backend/src/simulation/runner.py` | Game execution | `run_game()` |

### New Files to CREATE

| File | Purpose |
|------|---------|
| `backend/src/game_engine/ai/prompts/examples/__init__.py` | Package init |
| `backend/src/game_engine/ai/prompts/examples/combo_examples.py` | Multi-card combo patterns |
| `backend/src/game_engine/ai/prompts/examples/phase_examples.py` | Turn-based examples |
| `backend/src/game_engine/ai/prompts/examples/card_examples.py` | Card-specific examples |
| `backend/src/game_engine/ai/prompts/examples/loader.py` | Dynamic example selection |
| `backend/src/game_engine/ai/prompts/sequence_generator.py` | Request 1 implementation |
| `backend/src/game_engine/ai/prompts/strategic_selector.py` | Request 2 implementation |

### Files to MODIFY

| File | Changes |
|------|---------|
| `backend/src/game_engine/ai/turn_planner.py` | Add V4 support with dual temperatures |
| `backend/src/simulation/config.py` | Add new metrics fields |
| `backend/src/simulation/runner.py` | Track new metrics |
| `backend/.env` | Update PLANNING_VERSION |

---

## Appendix: Gemini Best Practices Applied

Based on https://ai.google.dev/gemini-api/docs/prompting-strategies:

1. **Use XML tags for structure** — Clear section boundaries
2. **Positive patterns over anti-patterns** — "ALWAYS check STR > 0" not "DON'T use 0 STR"
3. **Few-shot examples** — 3 contextual examples in Request 2
4. **Context last** — Game state after rules/examples
5. **Task at the end** — `<task>` tag at bottom of every prompt
6. **Structured output** — JSON schema for predictable parsing
7. **Consistent formatting** — Same structure across all examples
8. **Temperature tuning** — Low for rules (0.2), higher for strategy (0.7)
9. **Bold restrictions** — Card limitations in uppercase immediately after card name

---

## Appendix: Gemini 3 Flash Review Feedback (Incorporated)

The following feedback was provided by Gemini 3 Flash and has been incorporated into this design:

| Feedback | How Addressed |
|----------|---------------|
| Use low temperature (0.2) for Request 1 | Added to Architecture section and Temperature Strategy |
| Use higher temperature (0.7) for Request 2 | Added to Architecture section and Temperature Strategy |
| Request 1 should have ZERO strategic guidance | Emphasized in prompt structure and architecture |
| Prioritize COMBO examples over individual cards | Added combo_examples.py and priority logic in loader |
| Add "Average Game Length" as success metric | Added to Success Metrics table |
| Place `<task>` at bottom of prompts | Added to Design Principles (#7) |
| Format card restrictions in bold uppercase | Added to card formatting specification |
| Require Generator to output `total_cc_spent` | Added to Request 1 requirements |
| Add tactical labels to sequences | Added Step 4: Tactical Labels |
| Retry with temp=1.0 before V2 fallback | Added to Temperature Strategy section |
| Request diversity in sequences | Added to Request 1 prompt and Step 3 requirements |
