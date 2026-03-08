# AI V4 Execution Failure Analysis
## Game: 0a24b599-4b46-4c32-925c-59d6ec78046a, Turn 3

---

## EXECUTIVE SUMMARY

**ROOT CAUSE IDENTIFIED**: The AI V4 architecture has a critical flaw in how it handles cards across zones. The Sequence Generator (Request 1) generated illegal sequences that attempted to play cards from the Sleep Zone, and the Strategic Selector/Converter failed to detect or correct this issue.

**Impact Severity**: HIGH - This affects all games where the AI needs to play cards and causes execution to fall back to LLM-based action selection.

---

## FINDINGS

### 1. Request 1 (Sequence Generator) Generated ILLEGAL Sequences ⚠️

**Issue**: ALL 8 sequences attempted to play cards that were in the Sleep Zone, not in Hand.

**Evidence**:
- Prompt showed cards in Sleep Zone: Surge, Knight, Paper Plane
- Prompt showed cards in Hand: Wake, Umbruh, Archer
- Generated sequences: "play Surge [825bdd54-02bf-4cc6-84a8-c8a0361b4316] -> play Knight [41f0682b-3f36-4a6c-a2b1-78d4303b7405] ..."

**Prompt Constraint** (from request1_prompt):
```
## CRITICAL PLAY CONSTRAINT
**You can ONLY play cards from YOUR HAND (Hand).** Cards in YOUR TOYS IN PLAY (In Play) 
or YOUR SLEEP ZONE (Sleep Zone) CANNOT be played. You must use card IDs from the YOUR HAND section above.
```

**LLM Behavior**: The LLM completely ignored this constraint and generated sequences using cards from the Sleep Zone.

**Validation Status**: The sequences passed validation (8 generated, 8 after validation, 0 rejected).
- This means the TurnPlanValidator did NOT catch that these cards were from the wrong zone.

---

### 2. Request 2 (Strategic Selector) Received Invalid Data

**Issue**: Request 2 received string-based sequences that referenced illegal card plays.

**Evidence from request2_prompt**:
```xml
<valid_sequences>
<sequence index="0" label="[Balanced]">
<description>play Surge [825bdd54-02bf-4cc6-84a8-c8a0361b4316] -> play Knight [41f0682b-3f36-4a6c-a2b1-78d4303b7405] -> tussle 41f0682b-3f36-4a6c-a2b1-78d4303b7405->c02de099-bb75-4cef-ba9a-6eab9aab3bb1 -> end_turn | CC: 3/5 spent | Sleeps: 1</description>
<cc_spent>3/5</cc_spent>
<cards_slept>1</cards_slept>
</sequence>
...
</valid_sequences>
```

**LLM Selection**: Request 2 correctly selected Sequence 0 based on efficiency reasoning.

---

### 3. Conversion to TurnPlan Corrupted Data ❌

**Issue**: `convert_sequence_to_turn_plan()` function in `strategic_selector.py` recalculates CC costs by looking up cards in the player's hand.

**Code Path** (strategic_selector.py:191-210):
```python
# Build a lookup of card costs from hand
hand_costs = {card.name: card.cost for card in player.hand}

# Convert actions to PlannedAction format
action_sequence = []
cc_remaining = player.cc

for action in sequence.get("actions", []):
    card_name = action.get("card_name", "")
    action_type = action.get("action_type")
    
    # Determine actual CC cost based on action type
    if action_type == "play_card":
        # Look up actual card cost from hand
        cc_cost = max(0, hand_costs.get(card_name, 0))  # ⚠️ RETURNS 0 IF NOT IN HAND
```

**What Happened**:
1. hand_costs = {"Wake": 1, "Umbruh": 1, "Archer": 0}
2. Surge not in hand → cc_cost = 0 (WRONG! Should be flagged as invalid)
3. Knight not in hand → cc_cost = 0 (WRONG! Should be 1)

**Result in action_sequence**:
```json
{
  "cc_cost": 0,
  "card_name": "Surge",
  "action_type": "play_card"
},
{
  "cc_cost": 0,  // ⚠️ CORRUPTED! Should be 1
  "card_name": "Knight",
  "action_type": "play_card"
}
```

---

### 4. Tussle Action Also Corrupted ❌

**Issue**: The tussle action lost its target information during parsing/conversion.

**From request1_response**:
```
tussle 41f0682b-3f36-4a6c-a2b1-78d4303b7405->c02de099-bb75-4cef-ba9a-6eab9aab3bb1
```

**In final action_sequence**:
```json
{
  "cc_cost": 2,
  "card_name": null,
  "action_type": "tussle",
  "target_names": null  // ⚠️ MISSING! Should have target
}
```

**Root Cause**: The string-based compact format needs to be parsed by `_parse_action_string()` in `sequence_generator.py`, which extracts the IDs. However, when `convert_sequence_to_turn_plan()` processes the sequence, it may be receiving actions that already lost this information or the parsing didn't correctly extract the target IDs.

---

### 5. Execution Fell Back to LLM ❌

**Evidence from execution_log**:
```json
{
  "method": "llm",
  "reason": "Action not available (heuristic match failed)",
  "status": "success",
  "action_index": 0,
  "planned_action": "play_card Surge"
}
```

**What This Means**:
- The AI tried to execute "play_card Surge" from the plan
- The heuristic executor couldn't find "Surge" in hand (because it's in Sleep Zone)
- Execution fell back to asking the LLM to select a valid action
- This is the "safety net" that prevented a hard failure, but it means the plan was completely useless

---

## ROOT CAUSES

### Primary Root Cause: Zone Violation Not Detected

**Location**: Request 1 (Sequence Generator) + TurnPlanValidator

**Issue**: The LLM generated illegal sequences, and the validator did not catch them.

**Why Did This Happen?**:
1. The prompt's zone constraint ("CRITICAL PLAY CONSTRAINT") is not being enforced by the LLM
2. The TurnPlanValidator may not be checking if cards are in the correct zone before allowing play

### Secondary Root Cause: Silent Data Corruption

**Location**: `convert_sequence_to_turn_plan()` in strategic_selector.py

**Issue**: When a card is not found in hand, the function silently defaults to cc_cost=0 instead of raising an error or marking the sequence as invalid.

**Code**:
```python
cc_cost = max(0, hand_costs.get(card_name, 0))  # ⚠️ Silent default
```

**Should Be**:
```python
cc_cost = hand_costs.get(card_name)
if cc_cost is None:
    raise ValueError(f"Card '{card_name}' not found in hand - cannot determine cost")
```

### Tertiary Root Cause: String-Based Sequence Format

**Location**: Request 1 output format

**Issue**: The compact string format ("play Surge [id] -> play Knight [id] -> tussle id->id") requires complex parsing that is fragile and error-prone.

**Better Approach**: Request 1 should generate structured JSON with full action objects:
```json
{
  "sequences": [
    {
      "tactical_label": "[Balanced]",
      "actions": [
        {"action_type": "play_card", "card_id": "...", "card_name": "Surge", "cc_cost": 0},
        {"action_type": "play_card", "card_id": "...", "card_name": "Knight", "cc_cost": 1},
        {"action_type": "tussle", "attacker_id": "...", "target_id": "...", "cc_cost": 2}
      ],
      "total_cc_spent": 3,
      "cards_slept": 1
    }
  ]
}
```

---

## SPECIFIC ANSWERS TO YOUR QUESTIONS

### Q: Where did cc_cost=0 for Knight originate?

**A**: In `convert_sequence_to_turn_plan()` when it looked up "Knight" in hand_costs and got None (because Knight was in Sleep Zone, not Hand), then defaulted to 0.

**Line Numbers**: strategic_selector.py:205-210

### Q: Where did the incomplete tussle (missing target_names) originate?

**A**: The compact string format "tussle id->id" was parsed by `_parse_action_string()` which extracted the IDs, but somewhere in the conversion pipeline the target information was lost. This needs deeper investigation in the parsing code.

**Likely Location**: sequence_generator.py `_parse_action_string()` or strategic_selector.py `convert_sequence_to_turn_plan()` 

### Q: Are these symptoms in sequence_generator output or strategic_selector processing?

**A**: 
- **Zone violation**: Originated in sequence_generator (Request 1) output
- **cc_cost=0 corruption**: Introduced during strategic_selector's `convert_sequence_to_turn_plan()` processing
- **Missing tussle targets**: Likely lost during parsing/conversion (needs investigation)

---

## COMPONENT FAULT ASSIGNMENT

| Component | Fault | Severity |
|-----------|-------|----------|
| **Sequence Generator (Request 1)** | Generated illegal sequences (play from Sleep Zone) | HIGH |
| **TurnPlanValidator** | Failed to catch zone violations | HIGH |
| **convert_sequence_to_turn_plan** | Silent data corruption (cc_cost=0) | HIGH |
| **Strategic Selector (Request 2)** | No fault - selected best from invalid options | None |
| **Execution Safety Net** | Correctly fell back to LLM | None (working as designed) |

---

## RECOMMENDED FIXES

### Priority 1: Fix Zone Validation
**File**: `backend/src/game_engine/ai/turn_plan_validator.py`

Add explicit zone checking:
```python
def validate_play_card_action(self, action: PlannedAction, player: Player) -> List[ValidationError]:
    card_name = action.card_name
    card_id = action.card_id
    
    # Check if card is in hand
    card_in_hand = any(c.id == card_id or c.name == card_name for c in player.hand)
    if not card_in_hand:
        return [ValidationError(
            code="card_not_in_hand",
            message=f"Cannot play {card_name} - not in hand (check zone)",
            action_index=0,
            severity="error"
        )]
    
    # ... rest of validation
```

### Priority 2: Fix Silent Cost Lookup
**File**: `backend/src/game_engine/ai/prompts/strategic_selector.py:205-210`

Change from:
```python
cc_cost = max(0, hand_costs.get(card_name, 0))
```

To:
```python
cc_cost = hand_costs.get(card_name)
if cc_cost is None:
    logger.error(f"Card '{card_name}' not found in hand during conversion")
    raise ValueError(f"Invalid sequence: card '{card_name}' is not in hand")
```

### Priority 3: Improve Prompt Effectiveness
**File**: `backend/src/game_engine/ai/prompts/sequence_generator.py`

Strengthen zone constraints:
- Add zone prefixes to card listings (done in some places)
- Add validation examples showing rejected sequences
- Consider adding a JSON schema that enforces card IDs must be from hand

### Priority 4: Consider Structured Output
**File**: `backend/src/game_engine/ai/prompts/sequence_generator.py`

Replace string-based sequences with structured JSON actions to eliminate parsing ambiguity.

---

## FILES ANALYZED

### Full Prompts/Responses Extracted:
1. `turn3_analysis/request1_prompt_log1.txt` (5188 chars)
2. `turn3_analysis/request1_response_log1.json` (2353 chars)
3. `turn3_analysis/request2_prompt_log1.txt` (6712 chars)
4. `turn3_analysis/request2_response_log1.json` (265 chars)
5. `turn3_analysis/v4_turn_debug_log1.json` (debug metrics)
6. `turn3_analysis/execution_log_log1.json` (1 entry - LLM fallback)
7. `turn3_analysis/complete_log1.json` (full log entry with corrupted action_sequence)

### Code Files Referenced:
- `backend/src/game_engine/ai/prompts/sequence_generator.py`
- `backend/src/game_engine/ai/prompts/strategic_selector.py`
- `backend/src/game_engine/ai/turn_planner.py`
- `backend/src/game_engine/ai/turn_plan_validator.py` (needs fixing)

---

## CONCLUSION

The V4 architecture's dual-request system is sound in principle, but this investigation reveals three critical implementation gaps:

1. **Prompt compliance**: The LLM is not reliably following zone constraints
2. **Validation gaps**: The validator is not catching zone violations
3. **Silent failures**: Cost lookup defaults to 0 instead of failing loudly

All three issues must be fixed to make V4 reliable. The good news is that the execution safety net (LLM fallback) prevents hard failures, but it completely undermines the planning architecture's purpose.

**Next Steps**: Do NOT write code yet - review this analysis and confirm the recommended fix priorities before implementation.
