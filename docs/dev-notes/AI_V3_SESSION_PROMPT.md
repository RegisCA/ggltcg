# Session Prompt: GGLTCG AI v3 - Turn Planning Architecture

## Context Summary

**Project**: GGLTCG (Googooland Trading Card Game) - fast-paced card game (avg 10 turns, 3-4 critical turns per player)

**Current AI Version**: v2.9
- Makes **isolated decisions** one action at a time with no memory between decisions
- **Problem**: Locally-reasonable but globally-poor play patterns - plays cards without considering CC budget for the entire turn
- **Performance**: Inconsistent CC efficiency - ranges from 11-18 CC to sleep 6 cards (1.83 - 3.0 CC per card)
  - Sometimes plays efficiently (11 CC = excellent)
  - Often wastes CC (18 CC = 3x worse than optimal)
  - Root issue: No turn-level planning or CC budgeting

**Root Cause**: LLMs making isolated decisions cannot do multi-step CC budgeting or strategic sequencing

## Proposed Solution: v3 Turn Planning Architecture

### Core Insight from Strategy Document

The strategy document provides a **4-phase turn planning framework**:

1. **Threat Assessment** - Evaluate opponent's board by threat level (CRITICAL > HIGH > MEDIUM > LOW)
2. **Resource Inventory** - Catalog all cards and calculate possible action sequences with CC costs
3. **Threat Mitigation Strategy** - Generate removal sequences, prioritize by threat and CC efficiency
4. **Offensive Opportunities** - Use remaining CC for direct attacks or tempo plays

**Key Principle**: "Minimize the average CC cost of sleeping opponent cards" - evaluate every sequence by total CC spent ÷ opponent cards slept

**Target Metric**: ≤ 2.5 CC per opponent card slept (current range: 1.83 - 3.0, need consistency)

### Two-Phase System

**Phase 1: Strategic Planning** (once per turn start)
- AI receives full game state
- Generates structured plan: threat analysis → resource inventory → action sequence → CC budget
- Output: JSON with ordered action list, CC allocations, reasoning for each step
- **Important**: Game state only changes from AI's own actions - no opponent interrupts during turn

**Phase 2: Execution Loop** (repeated until turn ends)
- Get current valid actions (ActionValidator already filters by CC, legality)
- AI matches next planned action to valid actions list using **card IDs**
- Execute action, game state updates
- Continue to next planned action
- End when plan complete or no more actions

### Simplified Architecture

**No re-planning needed** - Game state only changes from AI's actions, which are planned. The plan accounts for state changes (e.g., "After I play Archer, I'll have 0 CC remaining, so end turn")

**No flexible matching needed** - Use card IDs consistently. Planned action references card ID, execution matches on card ID.

## Implementation Approach

### File Structure
```
backend/src/game_engine/ai/
├── llm_player.py          # Main AI interface (modify)
├── turn_planner.py        # NEW: Phase 1 planning
├── prompts/
    ├── planning_prompt.py      # NEW: 4-phase framework prompt
    ├── execution_prompt.py     # NEW: Simple "follow the plan" prompt
    ├── system_prompt.py        # Keep v2.9 as fallback
    ├── card_library.py         # (unchanged)
    ├── formatters.py           # (unchanged, reuse game state formatting)
    └── schemas.py              # Add TurnPlan schema, version 3.0
```

### Component Design

#### 1. TurnPlanner (`turn_planner.py`)

```python
class TurnPlanner:
    def create_plan(
        self, 
        game_state: GameState,
        player_id: str,
        game_engine: GameEngine
    ) -> TurnPlan:
        """
        Generate turn plan using 4-phase framework.
        
        Phase 1: Threat Assessment
        - Categorize opponent cards: CRITICAL/HIGH/MEDIUM/LOW
        - Identify: immediate combat threats, continuous effects, restrictions
        
        Phase 2: Resource Inventory  
        - Action cards: CC generation, removal, cost reduction, theft, combat mods
        - Toy cards: in play (stats, abilities) + in hand (combo potential)
        - Calculate action sequences with total CC costs
        
        Phase 3: Threat Mitigation Strategy
        - Generate removal paths for each threat (tussle, Archer, Action card)
        - Calculate CC efficiency: total CC ÷ cards slept
        - Select sequence that removes highest-priority threats
        
        Phase 4: Offensive Opportunities
        - Remaining CC after threat removal
        - Direct attack windows (opponent has 0 toys OR Paper Plane in play)
        - CC generation for extra actions (Surge, Rush, Umbruh)
        
        Returns: TurnPlan with ordered actions and CC budget
        """
```

#### 2. Planning Prompt (`planning_prompt.py`)

Based on strategy document structure:
- Show 4-phase framework as decision structure
- Provide threat prioritization list (Sock Sorcerer, Wizard, Gibbers = CRITICAL, etc.)
- Include action sequence examples from strategy doc (e.g., "Archer + Surge + Umbruh" walkthrough)
- Emphasize CC efficiency calculation
- Output: JSON schema with action_sequence (card IDs, CC costs), reasoning per phase

#### 3. Execution Prompt (`execution_prompt.py`)

Very simple:
- Input: Current plan step, valid actions, actions taken so far
- Task: "Select the action matching current plan step. If plan step unavailable, select closest alternative. If plan complete, end turn."
- Output: action_number (1-based index into valid_actions)

#### 4. Modified LLMPlayer (`llm_player.py`)

```python
class LLMPlayer:
    def __init__(self):
        self.planner = TurnPlanner()
        self.current_plan = None
        # Keep old prompt-based selection as fallback
    
    def select_action(self, game_state, player_id, valid_actions, game_engine):
        """
        Main turn logic:
        
        If first action of turn:
            - Create plan via TurnPlanner
            - Store plan
        
        Match current plan step to valid_actions using card IDs
        
        If plan complete or no match:
            - Select "end turn"
        
        Return action_index
        """
```

### Data Schema

```python
# schemas.py additions

class PlannedAction(BaseModel):
    """Single action in the plan sequence."""
    action_type: str  # "play_card", "tussle", "activate_ability", "end_turn"
    card_id: Optional[str]  # Card UUID for this action
    card_name: Optional[str]  # For human readability in logs
    target_id: Optional[str]  # Target card UUID
    cc_cost: int
    reasoning: str  # Why this specific action

class TurnPlan(BaseModel):
    """Complete turn plan."""
    # Phase 1: Threat Assessment
    threat_analysis: str  # Summary of threats by priority
    
    # Phase 2: Resource Inventory
    available_sequences: List[str]  # Descriptions of viable sequences considered
    
    # Phase 3: Selected Strategy
    strategy: str  # E.g., "Remove Knight (HIGH threat) via Archer, then direct attack 2x"
    
    # Phase 4: Action Sequence
    action_sequence: List[PlannedAction]
    
    # CC Budget
    cc_start: int
    cc_end_expected: int
    cc_efficiency: str  # "4 CC to sleep 2 cards = 2 CC per card"
    
    # Overall reasoning
    reasoning: str

PROMPTS_VERSION = "3.0"
```

## Key Implementation Details

### 1. Card ID Consistency
- Planning prompt receives game state with card IDs
- Plan stores card_id for each action
- Execution matches plan.action_sequence[N].card_id to valid_actions[X].card_id
- **No name matching, no fuzzy matching**

### 2. State Changes Handled in Plan
Plan accounts for state changes:
```python
# Example plan reasoning:
"After playing Archer (0 CC), I'll have 4 CC remaining.
After removing Paper Plane stamina (1 CC), I'll have 3 CC remaining.
After removing Knight stamina (3 CC), I'll have 0 CC remaining.
With 0 CC, I cannot attack further, so end turn."
```

### 3. ActionValidator Integration
- ActionValidator already filters actions by CC availability
- AI doesn't need to check CC budget for individual actions
- AI plans assume valid_actions list is always legal moves

### 4. Fallback to v2.9
```python
try:
    plan = self.planner.create_plan(...)
except Exception as e:
    logger.warning(f"Planning failed: {e}, using v2.9 fallback")
    return self.select_action_v2(...)  # Old single-decision logic
```

## Success Criteria

### Primary Metrics (from Strategy Doc)

1. **CC Efficiency**: Average CC spent per opponent card slept
   - Target: ≤ 2.5 CC per card
   - Baseline (v2.9): 1.83 - 3.0 CC per card (inconsistent)
   - Measure: Total CC spent ÷ opponent cards in sleep zone at game end
   - Goal: Consistent efficiency in 2.0 - 2.5 range

2. **Threat Prioritization**: Removes highest-priority threats first
   - CRITICAL threats (Sock Sorcerer, Wizard, Gibbers) removed before LOW threats
   - Measure: Check removal order in game logs

3. **Strategic Coherence**: Turn has clear strategy reflected in action sequence
   - "Remove threats then attack" vs "Generate CC then remove threats" vs "Direct attack"
   - Measure: Plan reasoning matches actual actions taken

4. **Natural Turn Endings**: Ends turn when plan complete, not when forced by lack of actions
   - Measure: % of turns ending with >0 valid non-end-turn actions available

### Secondary Metrics

5. **Win Rate**: Compare v3 vs v2.9 in head-to-head games
6. **Game Length**: Average turns to completion (should be similar, ~10 turns)
7. **Actions Per Turn**: Track distribution (no target, just data for analysis)
8. **CC Efficiency Consistency**: Standard deviation of CC per card across games

### Anti-Metrics (Things NOT to measure)

- ❌ "Action count per turn" - No target number, depends on situation
- ❌ "Doesn't play cards when CC=0" - Engine already prevents this
- ❌ "No wasted toys" - Sometimes playing extra toys is correct (tempo, effects)

## Testing Strategy

### Phase 1: Planning Quality (Offline)
- Generate plans for 10 diverse game states
- Verify:
  - Threat analysis identifies correct priorities (manual review)
  - Action sequences are legal (all card IDs exist, CC math adds up)
  - CC efficiency is calculated correctly
  - Plans account for state changes ("After X, I'll have Y CC...")

### Phase 2: Execution Fidelity
- Given fixed plan, verify action selection matches plan steps
- Test: Plan says "tussle Knight (id: abc-123)", valid_actions includes tussle Knight, AI selects it
- Test: Plan step not available (Knight already slept), AI adapts or ends turn

### Phase 3: Full Games
- Run 20 games: v3 vs v2.9
- Collect metrics: CC efficiency, threat prioritization, win rate
- Review game logs for coherence and strategy quality

### Phase 4: Simulation Testing
- Use existing simulation framework (Control_Ka, Aggro_Rush, Tempo_Charge decks)
- Run 90-game simulations comparing v3 vs v2.9
- Measure:
  - Average CC spent to win (target: consistent 11-14 range)
  - Standard deviation of CC efficiency
  - Win rate by matchup
  - Game duration consistency

### Phase 5: Edge Cases
- Turn 1 (low CC, must defend)
- Mid-game (complex board, multiple threats)
- Endgame (1-2 cards left, must close out win)
- Combo scenarios (Archer + multiple targets, Wake + Sun, Ka + tusslers)

## Resources

- **Strategy Document**: `/Users/regis/Downloads/GGLTCG Turn Planning Strategy Guide Gemini 3 Flash.md`
  - Read thoroughly, implement 4-phase framework exactly
  - Use threat priority list (Section 1.3)
  - Reference example walkthrough (Turn 2 example at end)
  - Apply "Strategic Principles Summary" section

- **Current Implementation**:
  - `/Users/regis/Projects/ggltcg/backend/src/game_engine/ai/llm_player.py`
  - `/Users/regis/Projects/ggltcg/backend/src/game_engine/ai/prompts/`
  - `/Users/regis/Projects/ggltcg/backend/src/game_engine/validation/action_validator.py`

- **Game Rules**: `/Users/regis/Projects/ggltcg/docs/rules/GGLTCG Rules v1_1.md`
- **Architecture**: `/Users/regis/Projects/ggltcg/docs/development/ARCHITECTURE.md`
- **Simulation System**: `/Users/regis/Projects/ggltcg/backend/src/simulation/`

## Performance Baseline (v2.9)

From simulation data (Control_Ka vs Control_Ka, 90 games):
- CC efficiency range: 11-18 CC to sleep 6 cards
- Best case: 11 CC = 1.83 CC per card (excellent)
- Worst case: 18 CC = 3.0 CC per card (poor)
- **Problem**: Inconsistency - AI sometimes finds efficient path, often doesn't
- Average turns: 6-10 turns
- Average game duration: 12-19 seconds

**v3 Goal**: Consistent CC efficiency in 11-15 CC range (1.83 - 2.5 CC per card)

## Next Steps

1. **Study strategy document** - Understand 4-phase framework, threat priorities, example walkthrough
2. **Design planning prompt** - Structure around 4 phases, include threat priority reference, show CC efficiency calculation
3. **Implement TurnPlanner** - Generate plans following framework
4. **Test planning offline** - Verify plans are coherent and legal for sample game states
5. **Implement simple execution** - Match plan step to valid action by card ID
6. **Integrate into LLMPlayer** - Replace single-decision logic with plan→execute loop
7. **Run test games** - Collect CC efficiency, threat prioritization metrics
8. **Run simulations** - Compare v3 vs v2.9 on standard test decks
9. **Iterate on planning prompt** - Based on observed plan quality issues

## Critical Reminders

- **Use card IDs only** - No name matching, no flexible matching
- **No opponent interrupts** - Plan doesn't need to handle mid-turn state changes from opponent
- **ActionValidator handles legality** - Don't duplicate CC checks or legal move validation in prompts
- **CC efficiency is the primary metric** - Every plan should calculate and minimize CC per card slept
- **Plans account for their own state changes** - "After action X, I'll have Y CC remaining"
- **Threat priorities from strategy doc** - CRITICAL (Sock Sorcerer, Wizard, Gibbers) > HIGH (Knight, Belchaletta, etc.)
