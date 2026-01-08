"""
Turn Planning Prompt v3 - COMPRESSED & MODULAR

Major changes from v2:
- Removed engine-duplicated validation (~2000 chars)
- Card guidance loaded dynamically from YAML (~1500 chars saved)
- Consolidated redundant constraint sections (~800 chars saved)
- Compressed examples and formatting (~500 chars saved)
Target: <10,000 chars (down from 15,426)

Architecture:
- Python validators handle: CC math, suicide attacks, opponent toy tracking
- Prompt focuses on: strategy, sequencing, combo identification
- Dynamic card loading: only include cards in current game
"""

from .card_loader import format_card_guidance_compact
from .effect_loader import generate_effect_guidance


# =============================================================================
# Core Rules (Compact Reference)
# =============================================================================

CORE_RULES = """# GAME MECHANICS

**Zones**: HAND (play from) | IN PLAY (attack with) | SLEEP (locked)
**Turn**: +4 CC/turn (max 7) | Turn 1 P1: 2 CC
**Win**: Sleep all 6 opponent cards
**Stamina**: Toy with 0 STA auto-sleeps immediately (no tussle needed)

**Action Types** (from game engine ActionType enum):
- `play_card`: Play a card from hand (costs card's CC)
- `tussle`: Combat between toys (costs 2 CC, winner sleeps loser, requires STR > 0)
- `direct_attack`: Attack opponent's hand when they have 0 toys (costs 2 CC, max 2/turn, requires STR > 0)
- `activate_ability`: Use a card's activated ability (costs varies, check effect_definitions)
- `pass`: End your turn

**Combat/Tussle** (CRITICAL MATH):
- **Attacker gets +1 SPD bonus** - this often decides the winner!
- Faster card strikes first, deals STR damage to slower card's STA
- If slower card survives (STA > 0), it strikes back
- **Card with 0 STA sleeps immediately** - cannot strike back
- Loser goes to sleep zone and CANNOT be targeted anymore

**Tussle Examples** (work through the math!):
- Umbruh (4/4/4) attacks Umbruh (4/4/4): Attacker = 5 SPD (bonus!), strikes first with 4 STR → defender 0 STA → **attacker wins clean**
- Paper Plane (2/2/1) attacks Umbruh (4/4/4): Attacker = 3 SPD, Umbruh = 4 SPD → Umbruh faster, strikes first with 4 STR → Paper Plane dies → **Umbruh wins**
- Knight vs ANYONE on YOUR turn: **Knight auto-wins** (special ability, ignore stats)

**Key Insight**: Equal-stat mirrors (like Umbruh vs Umbruh) = **attacker always wins** due to +1 SPD bonus!

**Card Types**:
- TOY: Has stats. **STR > 0 = can tussle/direct_attack. STR = 0 = CANNOT attack** (defensive only). ALL toys (even 0 STR) block opponent's direct attacks
- ACTION: Effect triggers, goes to sleep. Cannot attack

**Key Rules**:
- Can only play cards from HAND (not sleep zone)
- Wake returns sleep→hand (must still pay to play)
- Direct attack: requires opponent has EXACTLY 0 toys (max 2/turn)
- Activated abilities: can use MULTIPLE times per turn (pay CC each time)
- Continuous effects: active while in play"""


# =============================================================================
# Threat Assessment
# =============================================================================

THREAT_GUIDE = """# THREAT PRIORITY
CRITICAL: Gibbers (+1 cost tax), Sock Sorcerer (blocks removal), Wizard (cheap tussles)
HIGH: Belchaletta (+2CC/turn), Raggy (free tussles), Knight (auto-win), Paper Plane (bypasses defense)
Remove threats to maximize efficiency"""


# =============================================================================
# Sequence Planning Rules (Multi-Step Logic)
# =============================================================================

SEQUENCE_PLANNING = """# SEQUENCE PLANNING (Validator handles CC/combat math)

## Turn 1 Opening Strategy (CRITICAL)
**P1 Turn 1 (2 CC start)**: Opponent has 0 toys = DIRECT ATTACK IS AVAILABLE!
- Optimal: Play toy (0-1 CC) + Direct attack (2 CC) = sleep 1 card from hand
- Example: Surge + Umbruh + end = WRONG (Budget: 2+1=3, Spend: 0+1=1, Sleep: 0 cards)
- Example: Surge + Knight + direct_attack = CORRECT (Budget: 2+1=3, Spend: 0+1+2=3, Sleep: 1 card)
- Example: Archer + direct_attack = CORRECT (Budget: 2, Spend: 0+2=2, Sleep: 1 card, 0 CC left)
- **WITH SURGE**: 3 CC budget (can afford 1CC toy + attack) | **WITHOUT SURGE**: 2 CC budget (only 0CC toy + attack!)

**P2 Turn 1 (4 CC)**: Opponent has toys in play = must tussle first
- Clear board first, THEN direct attack if CC remains

## Strategy Framework
1. **Threat Assessment**: Identify opponent board state (count ALL toys including 0 STR)
2. **Resource Budgeting**: Starting CC + gains (Surge +1, Rush +2, HLK +1/card)
3. **Removal Sequence**: Sleep opponent toys (tussle/abilities/Drop)
4. **Finish**: Direct attack when opponent has 0 toys

## Critical Sequencing Rules

**Setup Cards First**: Surge/Rush/HLK BEFORE spending their CC
**Wake Before Play**: Wake (1CC)→card goes to hand→play card (cost)→use it
**Buff Before Combat**: VVAJ before tussling (expires end of turn)

**DIRECT ATTACK RULE (MOST IMPORTANT)**:
- Can ONLY direct attack when opponent has EXACTLY 0 toys in play
- 0 toys = CAN direct attack (Turn 1 P1, after clearing board)
- 1+ toys = CANNOT direct attack (must tussle/remove toys first)
- Archer counts as toy (blocks despite 0 STR)
- After tussle sleeps toy, count decreases
- Check remaining toys AFTER each removal action

**Multi-Step Combat**:
- One toy can tussle multiple times per turn
- Remove all opponent toys, then direct attack
- Example: Tussle→sleep toy 1→Tussle→sleep toy 2→Direct attack

## EXECUTION PROTOCOL (Follow These Steps)

**STEP 1: Calculate AVAILABLE CC (MANDATORY - DO THIS FIRST!)**
1. Check hand: Do you have Surge (+1) or Rush (+2)?
2. Calculate budget: Starting CC + Surge/Rush bonus = **TOTAL BUDGET**
3. Write it down: "My budget this turn: X CC"

**Examples:**
- Turn 1: 2 CC start, Surge in hand → Budget = 2+1 = **3 CC**
- Turn 4: 4 CC start, Surge in hand → Budget = 4+1 = **5 CC** (play Surge first!)
- Turn 5: 6 CC start, no Surge/Rush → Budget = **6 CC**

**CRITICAL**: If you need more CC to execute your plan, PLAY SURGE/RUSH FIRST!

**STEP 2: Budget Check (BEFORE Planning)**
- Sum all action costs using FIXED costs below
- If Sum > Available CC: **PLAN IS IMPOSSIBLE**

**ACTION COSTS (FIXED - MEMORIZE THESE):**
- play_card: card's cost (varies) - includes ACTION cards like Wake (1 CC), Clean (3 CC)
- **tussle: 2 CC** (always, unless Wizard/Raggy modifier)
- **direct_attack: 2 CC** (always, no exceptions)
- activate_ability: 1 CC (Archer), varies by card
- end_turn: 0 CC

**Example:** Knight (1) + Direct Attack (2) = 3 CC total
**WRONG:** Direct Attack with 1 CC - IT ALWAYS COSTS 2 CC!
- **NEGATIVE CC IS BANNED**: If cc_after < 0 at ANY step, plan is INVALID

**STEP 3: Track Opponent Toys (Dynamic)**
- **START**: Count opponent toys IN PLAY (include 0 STR toys like Archer!)
- **DURING**: Each tussle/ability that sleeps toy → count decreases by 1
- **RULE**: Can ONLY direct_attack when count = 0
- Example: 2 toys → sleep 1 → 1 remains → NO direct_attack yet

**STEP 4: Generate Actions (Exhaustive Loop)**
Priority order:
1. **SURGE/RUSH FIRST** if in hand (free CC!)
2. **CHECK ABILITIES FOR EASY WINS**:
   - Archer in play + opponent toy has low STA? Calculate: STA ≤ CC? Use ability!
   - Example: Paper Plane (1 STA) + Archer + 1 CC = instant sleep! 
   - Don't give up if you have abilities available!
3. **CHECK CARD ABILITIES** before tussling:
   - Paper Plane in hand + opponent has toys = can direct_attack (bypass!)
   - Archer in play = can use ability instead of bad tussles
4. **TUSSLE** if opponent has toys AND you'll win (2 CC)
   - **CALCULATE COMBAT FIRST**: Will I survive? Use tussle examples above!
   - If suicide (I die, deal 0 damage): SKIP, use abilities or direct_attack instead
5. **DIRECT ATTACK** if opponent has 0 toys OR Paper Plane bypass (**2 CC always**)
6. **ABILITIES** for chip damage/removal (varies)
7. **PLAY TOYS** for board presence
8. **END TURN** when CC < 2 or no valid actions

**STEP 5: Post-Action Audit**
After EACH action:
1. CC Math: cc_after = cc_before - cost (must be ≥ 0!)
2. Toy Count: If you slept toy, decrease opponent count
3. Target Validity: Can't target cards in sleep zone

**STEP 6: FINAL VALIDATION (Before submitting plan)**
Before outputting action_sequence, verify:
1. ✅ Total CC spent ≤ Budget from STEP 1?
2. ✅ Every action uses CORRECT fixed cost? (tussle=2, direct_attack=2)
3. ✅ No action has cc_after < 0?
4. ✅ If budget is insufficient, did you include Surge/Rush?
5. ❌ If validation fails: **REJECT THIS PLAN** and revise

**Modifiers**: Wizard (-1 tussle = 1 CC), Raggy (0 after turn 1), Gibbers (opponent +1 all)

## Critical Rules
❌ Negative CC at any step
❌ Direct attack with 1+ opponent toys
❌ Target cards not in play (already slept)
❌ Play from sleep without Wake first
❌ Abilities without valid targets

## Efficiency Target
≤2.5 CC per OPPONENT card slept."""


# =============================================================================
# Output Format
# =============================================================================

OUTPUT_FORMAT = """# OUTPUT FORMAT

**Required**:
```json
{
  "plan_reasoning": "Opp Board: [list ALL toys]. Count: N. Strategy: [concise plan] (<500 chars)",
  "action_sequence": [
    {
      "action_type": "play_card|tussle|direct_attack|activate_ability|end_turn",
      "card_id": "uuid",
      "card_name": "CardName",
      "target_ids": ["uuid"] (if needed),
      "cc_cost": N,
      "cc_after": N
    }
  ],
  "expected_cards_slept": N,
  "residual_cc_justification": "explain if CC>=2 at end"
}
```

**Reasoning Template**: "Opp Board: [Archer, Umbruh]. Count: 2. Strategy: Tussle both, then direct attack"
- MUST list ALL opponent toys
- Count determines direct attack eligibility
- Show CC math if complex

**Action Sequence Rules** (VALIDATE EACH ACTION):
- ONE action per object (no combining)
- Use [ID: uuid] for all card_ids/target_ids
- **cc_after MUST be >=0 for EVERY step** (if ANY action goes negative, plan is INVALID)
- **tussle/direct_attack MUST include card_id** - specify which card is attacking
- **tussle/direct_attack requires STR > 0** - Archer (0 STR) CANNOT attack!
- Direct attack: NO target_ids (hits random hand card)
- **NEVER select a sequence you marked as INVALID in sequences_considered!**
- If all sequences are invalid: ADD Surge/Rush to enable the plan

**Example Turn**:
Start: 4 CC, Hand: [Surge, Knight], Opp: [Umbruh]
1. play_card Surge (0 CC, +1 gain) → 5 CC
2. play_card Knight (1 CC) → 4 CC
3. tussle Knight→Umbruh (2 CC) → 2 CC (Umbruh sleeped, 0 toys remain)
4. direct_attack Knight (2 CC) → 0 CC (hand card slept)
Expected: 2 cards slept, 5 CC spent → 2.5 CC/card ✓"""


# =============================================================================
# Main Prompt Generator
# =============================================================================

def get_planning_prompt_v3(
    game_state_text: str,
    hand_details: str,
    in_play_details: str,
    game_state,
    player_id: str,
) -> str:
    """
    Generate compressed planning prompt with dynamic card guidance.
    
    Args:
        game_state_text: Current game state summary
        hand_details: Hand cards with IDs
        in_play_details: In-play cards with IDs
        game_state: GameState object for dynamic card loading
        player_id: AI player's ID
    """
    # Get player and opponent
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Collect all relevant cards (player hand + in play, opponent in play)
    player_cards = player.hand + player.in_play
    opponent_cards = opponent.in_play
    
    # Generate dynamic effect guidance
    effect_guidance = generate_effect_guidance(player_cards, opponent_cards)
    
    # Load card-specific guidance
    card_guidance = format_card_guidance_compact(game_state, player_id)
    
    prompt = f"""You are a GGLTCG turn planner. Goal: Sleep opponent cards efficiently (≤2.5 CC/card).

---
## CURRENT GAME STATE

{game_state_text}

### YOUR CARDS (with IDs)
**Hand:**
{hand_details}

**In Play:**
{in_play_details}

---

{CORE_RULES}

{THREAT_GUIDE}

{effect_guidance}

{card_guidance}

{SEQUENCE_PLANNING}

{OUTPUT_FORMAT}

Respond with valid JSON only. Validators will check CC math, combat outcomes, and toy counts."""

    return prompt


# =============================================================================
# Card Formatters (Reused from v2)
# =============================================================================

def format_card_for_planning(card, game_engine=None, player=None) -> str:
    """Format a single card with full details for planning."""
    if game_engine and player and card.cost >= 0:
        effective_cost = game_engine.calculate_card_cost(card, player)
    else:
        effective_cost = card.cost
    
    if card.is_toy():
        if game_engine:
            spd = game_engine.get_card_stat(card, "speed")
            str_val = game_engine.get_card_stat(card, "strength")
            cur_sta = game_engine.get_effective_stamina(card)
        else:
            spd = card.get_effective_speed()
            str_val = card.get_effective_strength()
            cur_sta = card.get_effective_stamina()
        
        restriction = " [0 STR-NO ATTACK]" if str_val == 0 else ""
        return f"[ID: {card.id}] {card.name} ({effective_cost}CC, {spd}/{str_val}/{cur_sta} SPD/STR/STA){restriction}"
    else:
        return f"[ID: {card.id}] {card.name} (ACTION, {effective_cost}CC)"


def format_hand_for_planning_v3(hand: list, game_engine=None, player=None) -> str:
    """Format hand cards."""
    if not hand:
        return "EMPTY"
    return "\n".join(f"- {format_card_for_planning(card, game_engine, player)}" for card in hand)


def format_in_play_for_planning_v3(in_play: list, game_engine=None, player=None) -> str:
    """Format in-play cards."""
    if not in_play:
        return "NONE"
    return "\n".join(f"- {format_card_for_planning(card, game_engine, player)}" for card in in_play)


def format_sleep_zone_for_planning_v3(sleep_zone: list, game_engine=None, player=None) -> str:
    """Format sleep zone cards (compact, with IDs)."""
    if not sleep_zone:
        return "EMPTY"
    return "\n".join(f"- {format_card_for_planning(card, game_engine, player)}" for card in sleep_zone)
