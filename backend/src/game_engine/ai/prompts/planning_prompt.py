"""
Turn Planning Prompt for AI v3.

This module contains the 4-phase turn planning framework prompt that guides
the AI to create a complete turn plan with CC budgeting and threat prioritization.

Based on: GGLTCG Turn Planning Strategy Guide
"""

from .card_library import CARD_EFFECTS_LIBRARY


# =============================================================================
# Game Fundamentals (Core Rules)
# =============================================================================

GAME_FUNDAMENTALS = """
## Game Fundamentals

### The 3 Zones Per Player
Each player has exactly 3 card zones:
1. **HAND** - Cards you can play. Hidden from opponent.
2. **IN PLAY** - Toys currently on the battlefield. These can tussle and attack.
3. **SLEEP ZONE** - "Graveyard" for sleeped/used cards. Action cards go here after use.

### Card Types
- **TOY cards**: Have SPD/STR/STA stats. Go to IN PLAY when played. Can tussle and direct attack.
- **ACTION cards**: No stats. When played, effect happens, then card goes to YOUR sleep zone.

### Owner vs Controller
- **Owner**: The player whose deck the card came from. Never changes.
- **Controller**: The player currently controlling the card. Can change (e.g., Twist).
- Effects benefit the CONTROLLER (e.g., Umbruh's "gain 1 CC when sleeped" goes to controller).

### Victory Condition
**You WIN when ALL of opponent's cards are in their Sleep Zone** (none in hand + none in play).

### Core Actions
| Action | Cost | Requirement | Effect |
|--------|------|-------------|--------|
| **Play a card** | Card's CC cost | Card in HAND | Move card from HAND → IN PLAY (toys) or execute effect (actions) |
| **Tussle** | 2 CC | TOY in your IN PLAY | Your toy attacks opponent's toy. Loser goes to sleep zone. |
| **Direct Attack** | 2 CC | TOY in your IN PLAY + opponent has 0 toys | Your toy sleeps a random card from opponent's HAND. Max 2 per turn. |
| **Activate Ability** | Varies | TOY with ability in your IN PLAY | Use a toy's special ability (e.g., Archer) |

### Archer's Activated Ability (IMPORTANT!)
Archer has a unique **activated ability** that can be used REPEATEDLY:
- **Cost**: 1 CC per use
- **Effect**: Remove 1 stamina from ANY opponent toy in play
- **Key Point**: You can use this ability MULTIPLE TIMES per turn!
- **Example**: Opponent has Knight (3 STA). Use Archer ability 3 times (3 CC total) → Knight loses all 3 STA → Knight is sleeped!

**In your plan**, each use is a separate action:
```
action_type: "activate_ability", card_name: "Archer", cc_cost: 1
action_type: "activate_ability", card_name: "Archer", cc_cost: 1  
action_type: "activate_ability", card_name: "Archer", cc_cost: 1
```

### Direct Attack Rules (CRITICAL!)
**Requirements to direct attack:**
1. YOU must have at least 1 TOY in your IN PLAY zone (the toy performs the attack!)
2. Opponent has **ZERO toys in their IN PLAY zone**, OR you have **Paper Plane** in play

**Both conditions must be met!**
- If YOU have no toys in play → you CANNOT direct attack (nothing to attack with!)
- If opponent HAS toys in play → you CANNOT direct attack (unless Paper Plane)
- Only when YOU have toys AND opponent has none → you CAN direct attack

**COMMON MISTAKE:** Planning direct attacks when you have no toys in play. You need a toy to perform the attack!

### Tussle Resolution
1. **Speed Check**: Faster card (higher SPD) attacks first
2. **Damage**: Attacker's STR reduces defender's current STA
3. **Sleep Check**: If STA reaches 0, card is sleeped (moved to sleep zone)
4. **Counter**: If defender survives, they counter-attack the same way

### How Key Action Cards Work
- **Wake** (1 CC): Move 1 card from YOUR sleep zone → YOUR HAND (not into play!)
- **Sun** (3 CC): Move up to 2 cards from YOUR sleep zone → YOUR HAND
- **Drop** (2 CC): Sleep 1 target toy (move from in play → sleep zone)
- **Twist** (3 CC): Take control of opponent's in-play toy (stays in play, you control it)
- **Toynado** (2 CC): Return ALL in-play cards to owners' HANDS
- **Jumpscare** (0 CC): Return 1 in-play card to owner's HAND

### Multi-Step Sequences
Cards recovered with Wake/Sun go to HAND. You must PLAY them to use them!

**Example**: You have 5 CC, Wake in hand, Knight in sleep zone:
1. Play Wake (1 CC) → Knight moves to your HAND → 4 CC remaining
2. Play Knight (1 CC) → Knight moves to IN PLAY → 3 CC remaining  
3. Tussle with Knight (2 CC) → Attack opponent toy → 1 CC remaining

**DO NOT** assume Wake puts cards directly into play - it puts them in your HAND!
"""


# =============================================================================
# Threat Priority Reference (from Strategy Guide Section 1.3)
# =============================================================================

THREAT_PRIORITIES = """
## Threat Priority Reference (Highest to Lowest)

**CRITICAL** - Must remove first if possible:
- Sock Sorcerer: Blocks ALL effect-based removal (Twist, Clean, Drop, etc.)
- Wizard: Enables multi-sleep turns (tussles cost 1 CC instead of 2)
- Gibbers: Economic disruption (your cards cost +1 CC)

**HIGH** - Remove soon:
- Belchaletta: CC engine (+2 CC per turn)
- Raggy: Free tussles (0 CC per tussle)
- Umbruh: Signals opponent aggression (+1 CC when sleeped)
- Knight: Guaranteed tussle wins on opponent's turn
- Paper Plane: CAN BYPASS DEFENDERS to direct attack opponent's hand (action_type: direct_attack, NOT tussle!)

**MEDIUM** - Remove when convenient:
- Ka: +2 STR to all opponent toys
- Ballaber: Strong stats, free play option
- Dream: Strong late-game stats
- Drum: +2 SPD to all toys
- Violin: +2 STR to all toys
- Demideca: +1/+1/+1 to all toys
- Hind Leg Kicker: CC refund on plays
- Monster: Board equalizer (context-dependent)

**LOW** - Remove last:
- Archer: Cannot tussle, only activated ability
- Beary: Protection but weak offensive threat
- Stand-alone cards with weak stats and no active effects
"""


# =============================================================================
# CC Cost Reference
# =============================================================================

CC_COST_REFERENCE = """
## CC Cost Reference

**Standard Costs:**
- Tussle: 2 CC (modified by Wizard or Raggy - see below)
- Direct Attack: 2 CC (max 2 per turn)
- Archer activate_ability: 1 CC per use (removes 1 STA, can use MULTIPLE times!)

**ARCHER ABILITY EXAMPLE:**
Opponent has Knight (3 STA). You have Archer in play and 4 CC:
1. Archer activate_ability (1 CC) → Knight now has 2 STA → 3 CC left
2. Archer activate_ability (1 CC) → Knight now has 1 STA → 2 CC left
3. Archer activate_ability (1 CC) → Knight now has 0 STA → SLEEPED! → 1 CC left
Total: 3 CC to sleep Knight using Archer ability 3 times.

**TUSSLE COST MODIFIERS (check in order):**
1. Is YOUR Raggy doing the tussle? → 0 CC (Raggy's tussles are FREE)
2. Is YOUR Wizard in play? → 1 CC (Wizard's "Magic Word" effect)
3. Otherwise → 2 CC (standard cost)

**CC Generation Cards (calculate cc_after carefully!):**
- Surge: Cost 0 CC, Gain 1 CC → cc_after = cc_before + 1
- Rush: Cost 0 CC, Gain 2 CC → cc_after = cc_before + 2 (not on turn 1!)

Example: You have 3 CC, play Surge → 3 - 0 + 1 = 4 CC after
Example: You have 2 CC, play Rush → 2 - 0 + 2 = 4 CC after

**Passive CC Generation (Benefits YOU):**
- YOUR Belchaletta at turn start: +2 CC (already applied)
- YOUR Umbruh when sleeped: YOU gain +1 CC
- YOUR Hind Leg Kicker in play: +1 CC when you play ANY card (not HLK itself)

**Passive CC Generation (Benefits OPPONENT - be careful!):**
- OPPONENT'S Belchaletta: +2 CC for them at their turn start
- OPPONENT'S Umbruh when sleeped: OPPONENT gains +1 CC (bad for you!)
- OPPONENT'S Hind Leg Kicker: OPPONENT gains +1 CC when you play cards!

**Action Card Costs:**
- Surge: 0 CC (gain 1 CC, net +1)
- Rush: 0 CC (gain 2 CC, net +2, not on turn 1)
- Drop: 2 CC (sleep 1 target toy)
- Clean: 3 CC (sleep ALL toys in play)
- Twist: 3 CC (steal 1 opponent toy)
- Wake: 1 CC (recover 1 from sleep zone)
- Sun: 3 CC (recover up to 2 from sleep zone)
- Toynado: 2 CC (return all in-play to hands)
- Jumpscare: 0 CC (return 1 toy to owner's hand)
- Copy: 0 CC (copy your own toy - special)
- VeryVeryAppleJuice: 0 CC (+1/+1/+1 to YOUR toys THIS TURN only)
- That was fun: 0 CC (recover action from sleep zone)

**Toy Play Costs:**
- 0 CC: Archer
- 1 CC: Ka, Knight, Wizard, Umbruh, Paper Plane, Raggy, Drum, Violin, Gibbers, Hind Leg Kicker, Monster
- 2 CC: Belchaletta, Beary, Demideca
- 3 CC: Sock Sorcerer
- 4 CC: Dream (reduces by 1 per card in YOUR sleep zone)
- Alternative: Ballaber (2 CC or sleep one of your cards)

**Cost Modifiers:**
- Gibbers in OPPONENT's play: Your cards cost +1 CC
- CANNOT go below 0 CC - if math shows negative, that sequence is IMPOSSIBLE

## ACTION ORDER OPTIMIZATION (Critical for CC Efficiency!)

**ORDER MATTERS! Always check these combos:**

### 1. Hind Leg Kicker Combo (Play HLK FIRST!)
If you have Hind Leg Kicker in hand and plan to play multiple cards:
- Play HLK first (costs 1 CC)
- Every subsequent card play triggers HLK: +1 CC back!
- Example with 4 CC:
  - Play HLK (1 CC) → 3 CC
  - Play Surge (0 CC) + HLK trigger (+1 CC) → 4 CC!  (net +1 CC)
  - Play Knight (1 CC) + HLK trigger (+1 CC) → 4 CC! (net 0 CC)
  - You played 3 cards and still have 4 CC!

### 2. VeryVeryAppleJuice Combo (Play VVAJ BEFORE tussle!)
If you need the +1 STR to win a tussle:
- Play VeryVeryAppleJuice FIRST (0 CC, gives +1/+1/+1 THIS TURN)
- THEN tussle with the boosted stats
- Example: Your Knight (4 STR) vs opponent's 5 STA toy
  - Without VVAJ: Knight can't sleep it (4 STR < 5 STA)
  - With VVAJ first: Knight has 5 STR → wins the tussle!

### 3. Dream Cost Reduction (Play action cards FIRST!)
Dream costs 4 CC minus 1 per card in YOUR sleep zone.
Action cards go to sleep zone when played!
- Example with 4 CC and empty sleep zone:
  - Dream costs 4 CC (too expensive!)
  - Play Clean (2 CC) → Clean goes to your sleep zone → Dream now costs 3 CC
  - Play Surge (0 CC, +1 CC) → Surge goes to sleep zone → Dream now costs 2 CC
  - You now have 3 CC and Dream costs 2 CC → you can play Dream!

### 4. Surge/Rush for Extra Actions
Always consider: does playing Surge/Rush FIRST enable more actions?
- 3 CC available, want 2 direct attacks (4 CC needed):
  - Without Surge: Can only do 1 attack (2 CC)
  - Play Surge first: 3 + 1 = 4 CC → Now can do 2 attacks!
"""


# =============================================================================
# Main Planning Prompt
# =============================================================================

PLANNING_SYSTEM_PROMPT = """You are an expert GGLTCG strategist. Your task is to create a complete turn plan that maximizes CC efficiency.

{game_fundamentals}

## Core Winning Principle
**Minimize the average CC cost of sleeping opponent cards.**
Target: ≤ 2.5 CC per opponent card slept
Every decision should be evaluated against CC efficiency and board control.

## CRITICAL: Card Ownership Rules
**Each card has an OWNER and CONTROLLER.** When effects trigger, they benefit the CONTROLLER:
- "YOUR Umbruh" = You control it. When sleeped, YOU gain +1 CC.
- "OPPONENT'S Umbruh" = Opponent controls it. When sleeped, OPPONENT gains +1 CC (bad for you!).
- Same card name can appear in both players' hands - they are NOT equivalent!
- Always check who CONTROLS a card before planning around its triggered effects.

## Additional Game Rules
- Maximum CC: 7 (cannot exceed)
- Standard turn CC gain: 4 CC (2 CC on turn 1)
- Maximum 2 direct attacks per turn

## CRITICAL: Card Type Restrictions (TOY vs ACTION)
**ONLY TOY CARDS CAN ATTACK!**
- TOY cards have SPD/STR/STA stats - they CAN tussle and direct attack
- ACTION cards (Drop, Clean, Twist, Surge, etc.) are played for their effect, then go to YOUR sleep zone
- ACTION cards CANNOT tussle, CANNOT direct attack - they have no stats!
- After playing an action card, it's in your sleep zone - you don't "have it" to attack with

**TOY-SPECIFIC RESTRICTIONS:**
- **Archer**: CANNOT tussle, CANNOT direct attack! Only has activated ability (1 CC: remove 1 stamina)
- Other toys CAN tussle and direct attack normally

**COMMON MISTAKE:** Playing Surge then trying to "tussle with Surge" - Surge is an ACTION CARD with no stats!

## STOP CONDITIONS (Check these FIRST before any planning)
**STOP CONDITION 1: Zero CC**
- If you have 0 CC: END TURN immediately
- Exception: You can play Surge (0 CC, gain 1 CC) only if you can then DO something useful with that 1 CC
- Playing cards "for next turn" with 0 CC is wasteful - those cards go to sleep zone when the action resolves

**STOP CONDITION 2: Already Have Defense**
- If you have 1+ toys in play and cannot attack: END TURN
- Don't play more toys just to "build a board" - save cards for when you can use them

## Output Format
Respond with a JSON object following the TurnPlan schema exactly.
All card IDs must be extracted from [ID: xxx] brackets - use the UUID, never card names.

{threat_priorities}

{cc_cost_reference}
"""


PLANNING_FRAMEWORK_PROMPT = """## Turn Planning Framework

Execute these 4 phases to create your turn plan:

### Phase 1: Threat Assessment
Evaluate all OPPONENT cards in play:
1. **Immediate Combat Threats**: Which opponent cards can tussle and win against yours?
2. **Effect-Based Threats**: What continuous effects are active? (immunity, cost modifiers, stat boosts)
3. **Prioritize Threats**: Rank from CRITICAL to LOW using the threat priority reference

**Remember**: Effects like "gain CC when sleeped" benefit the CONTROLLER. Sleeping OPPONENT'S Umbruh gives THEM +1 CC!

### Phase 2: Resource Inventory
Survey YOUR available tools:
1. **Your CC (Starting Budget)**: How much CC do you have RIGHT NOW?
2. **CC Generation in YOUR HAND**: Surge (+1 CC), Rush (+2 CC, not turn 1) - these INCREASE your budget!
3. **Action Cards in YOUR Hand**: What removal/control options?
4. **YOUR Toys in Play**: What can they tussle? Abilities? (Archer stamina removal)
5. **Toys in YOUR Hand**: Stats, abilities, costs

**⚠️ CRITICAL: You can ONLY play cards that are in YOUR HAND!**
- Look at the "YOUR CARDS - Hand" section below
- If a card is NOT listed there, you CANNOT play it!
- Do NOT assume you have Surge, Rush, or any other card - CHECK THE HAND LIST!
- Every card in your plan must have a matching [ID: xxx] from your hand or in-play list

### Phase 3: Calculate Action Sequences
For each viable path, calculate CC step-by-step:

**⚠️ THE ONE RULE: Before EACH action, check: "Do I have enough CC for this?"**
- If cc_before < cc_cost → ❌ CANNOT do this action!
- Plan your sequence so CC never goes negative at any step

**CC TRACKING (do this for EVERY action):**
```
cc_after = cc_before - cc_cost + cc_gained
```
- **Surge: cc_cost = 0, cc_gained = 1** → cc_after = cc_before + 1
- **Rush: cc_cost = 0, cc_gained = 2** → cc_after = cc_before + 2 (not turn 1!)
- Raggy tussle: 0 CC cost (FREE!)
- Wizard in play: All your tussles cost 1 CC instead of 2 CC

**THINK AHEAD: How does the board change after each action?**
After each action, ask: "What NEW options become available?"
- After tussle sleeps opponent's LAST toy → opponent has 0 toys → DIRECT ATTACK NOW AVAILABLE!
- After playing a toy → you now have a toy that can tussle or direct attack!

**CRITICAL COMBO: Tussle → Direct Attack**
If opponent has exactly 1 toy and you can win the tussle:
1. Tussle their toy (2 CC) → their toy is sleeped → opponent now has 0 toys!
2. **Direct attack is now available!** If you have 2+ CC left, ATTACK!
3. Continue attacking until CC runs out

Example:
- Start: 5 CC, opponent has Knight (their only toy)
- Play your Knight (1 CC) → 4 CC
- Tussle their Knight (2 CC) → 2 CC, their Knight sleeped, **opponent now has 0 toys!**
- Direct attack (2 CC) → 0 CC, 1 more card slept from opponent's hand!
- Result: 5 CC spent, 2 cards slept = 2.5 CC per card ✓

**CC_AFTER Calculation - MUST FOLLOW THESE EXACTLY:**
| Action | cc_before | cc_cost | cc_gained | cc_after |
|--------|-----------|---------|-----------|----------|
| Play Knight | 4 | 1 | 0 | 3 |
| Play Surge | 3 | 0 | 1 | **4** |
| Play Rush | 2 | 0 | 2 | **4** |
| Raggy tussle | 3 | 0 | 0 | 3 |
| Tussle (standard) | 4 | 2 | 0 | 2 |
| Tussle (Wizard in play) | 3 | 1 | 0 | 2 |
| Direct attack | 4 | 2 | 0 | 2 |
| Direct attack | 2 | 2 | 0 | **0** |

**DIRECT ATTACK COSTS 2 CC!** Example:
- You have 4 CC, Knight in play, opponent has no toys
- Direct attack #1 (2 CC) → 2 CC left, 1 opponent card slept
- Direct attack #2 (2 CC) → 0 CC left, 2 opponent cards slept
- Total: 4 CC spent for 2 cards = 2.0 CC efficiency ✓

**ALWAYS CHECK: Can I direct attack?**
If you have a toy in play AND opponent has no toys → DIRECT ATTACK IS AVAILABLE!
Each direct attack costs 2 CC. With 2+ CC and a toy, you should attack!

**CRITICAL: Surge and Rush INCREASE your CC!**
- Before Surge: 3 CC → After Surge: **4 CC** (not 3!)
- Before Rush: 2 CC → After Rush: **4 CC** (not 2!)

**Limit to 3-5 best sequences.** For each:
- Step-by-step CC math with cc_after for EACH action
- Total CC spent on offensive actions (attacks, removal)
- Cards slept (only count OPPONENT cards)
- CC efficiency = CC spent ÷ opponent cards slept

### Phase 4: Select Best Sequence & Execute

## DECISION PRIORITY (Follow in Order!)

**Priority 1: WIN CHECK**
Can you sleep opponent's LAST remaining cards this turn? → DO IT NOW!

**Priority 2: DIRECT ATTACK OPPORTUNITY**
Do you have a TOY in play AND opponent has ZERO toys in play? (Or you have Paper Plane?)
→ **YOU CAN DIRECT ATTACK!** Each costs 2 CC, sleeps random card from opponent's hand.
→ With 2 CC: Do 1 direct attack (2 CC → 0 CC)
→ With 4+ CC: Do 2 direct attacks (4 CC → 0 CC) - this is MAX per turn
→ **DO NOT skip direct attacks when available!** This is your best CC efficiency.

**Priority 3: WINNING TUSSLES**
Can you tussle and WIN? (Your STR >= their current STA, and you're faster or tied)
→ TUSSLE NOW! This removes opponent's card.

**Priority 4: REMOVE HIGH-PRIORITY THREATS**
Use Archer ability, Drop, Clean, or other removal on CRITICAL/HIGH threats.
Calculate CC efficiency for each option.

**Priority 5: SETUP DEFENSE (Only if needed)**
Do you have ZERO toys in play?
→ Play ONE defensive toy (high STA or high SPD) to block direct attacks.
→ ONE toy is enough for defense. Don't play more unless you can attack.

**Priority 6: END TURN**
If you can't attack and already have defense → END TURN. Save your cards!

## COMMON MISTAKES TO AVOID
- ❌ **Planning to play cards that are NOT in your hand!** (Check the hand list!)
- ❌ **Planning an action when you don't have enough CC for it!** (Check cc_before >= cc_cost)
- ❌ Playing multiple toys "to build a board" when you can't attack
- ❌ Sleeping opponent's Umbruh without accounting for THEIR +1 CC gain
- ❌ **Skipping direct attacks when you have toys in play and opponent has none!**
- ❌ **Ending turn with 2+ CC when direct attack is available!**
- ❌ Playing a second toy when you already have defense and can't attack
- ❌ **Thinking direct attack costs 1 CC - it costs 2 CC!**
- ❌ **Not planning direct attacks AFTER a tussle that clears opponent's board!**
- ❌ **Playing Surge/Rush at end of turn instead of direct attacking!**
- ❌ **Assuming you have Rush or Surge when they're not in your hand!**

## Example: Correct CC Tracking

**Scenario**: 4 CC available, opponent has no toys, you have Knight in play

**CORRECT Plan**:
- Start: 4 CC
- Direct attack (2 CC) → 2 CC left, 1 opponent card slept ✓
- Direct attack (2 CC) → 0 CC left, 2 opponent cards slept ✓
- End turn
- Result: 4 CC spent, 2 cards slept = 2.0 CC per card

**Scenario 2**: 2 CC available, opponent has no toys, you have Knight in play

**CORRECT Plan**:
- Start: 2 CC
- Direct attack (2 CC) → **0 CC left**, 1 opponent card slept ✓
- End turn
- **DO NOT end turn without attacking!**

**Scenario 3**: 2 CC available, no toys in play, Paper Plane in hand

**Step-by-step check**:
- Start: 2 CC
- Play Paper Plane (1 CC) → 1 CC left ✓
- Direct attack costs 2 CC. Do I have 2 CC? NO, only 1 CC. → ❌ Cannot attack
- End turn with 1 CC remaining

**Scenario 4**: 2 CC available, no toys in play, Surge AND Paper Plane in hand

**Step-by-step check**:
- Start: 2 CC
- Play Surge (0 CC, +1 CC) → 3 CC now! ✓
- Play Paper Plane (1 CC) → 2 CC left ✓
- Direct attack costs 2 CC. Do I have 2 CC? YES! → Direct attack (2 CC) → 0 CC ✓
- Result: 1 card slept!

**WRONG Plan** (don't do this):
- Start: 4 CC  
- Play Knight (1 CC) → 3 CC left, 0 cards slept
- Play Ka (1 CC) → 2 CC left, 0 cards slept
- Direct attack (2 CC) → 0 CC left, 1 card slept
- Result: 4 CC spent, 1 card slept = 4.0 CC per card ❌

The correct plan attacks FIRST, then only plays cards if needed for defense.
"""


def get_planning_prompt(
    game_state_text: str,
    hand_details: str,
    in_play_details: str,
) -> str:
    """
    Generate the complete planning prompt for the AI.
    
    Args:
        game_state_text: Formatted game state (from format_game_state_for_ai)
        hand_details: Detailed list of cards in hand with IDs
        in_play_details: Detailed list of cards in play with IDs
        
    Returns:
        Complete planning prompt string
    """
    system = PLANNING_SYSTEM_PROMPT.format(
        game_fundamentals=GAME_FUNDAMENTALS,
        threat_priorities=THREAT_PRIORITIES,
        cc_cost_reference=CC_COST_REFERENCE,
    )
    
    prompt = f"""{system}

{PLANNING_FRAMEWORK_PROMPT}

---

{game_state_text}

## YOUR CARDS (with IDs for planning)

### Hand:
{hand_details}

### In Play:
{in_play_details}

---

Create your turn plan now. Think through each phase carefully, then output your TurnPlan JSON."""

    return prompt


# =============================================================================
# Card Details Formatter (for planning prompt)
# =============================================================================

def format_card_for_planning(card, game_engine=None, player=None, is_opponent: bool = False) -> str:
    """
    Format a single card with full details for planning.
    
    Args:
        card: Card object
        game_engine: Optional GameEngine for effective stats/costs
        player: Optional Player who owns the card (needed for effective cost calculation)
        is_opponent: Whether this is an opponent's card
        
    Returns:
        Formatted string with card ID, name, stats, and effect
    """
    card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
    effect = card_info.get("effect", "Unknown effect")
    threat = card_info.get("threat_level", "UNKNOWN")
    
    # Calculate effective cost (accounts for Gibbers, Dream, etc.)
    if game_engine and player and card.cost >= 0:  # Skip Copy card (cost -1)
        effective_cost = game_engine.calculate_card_cost(card, player)
    else:
        effective_cost = card.cost
    
    if card.is_toy():
        if game_engine:
            spd = game_engine.get_card_stat(card, "speed")
            str_val = game_engine.get_card_stat(card, "strength")
            cur_sta = game_engine.get_effective_stamina(card)
            max_sta = game_engine.get_card_stat(card, "stamina")
        else:
            spd = card.get_effective_speed()
            str_val = card.get_effective_strength()
            cur_sta = card.get_effective_stamina()
            max_sta = card.stamina + card.modifications.get("stamina", 0)
        
        stats_str = f"({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA)"
        cost_str = f"cost {effective_cost}"
        
        # Special ability labels for toy cards
        if card.name == "Archer":
            ability_label = "⚠️ CANNOT TUSSLE - ability only: 1 CC removes 1 STA"
        elif card.name == "Paper Plane":
            ability_label = "✈️ Can direct_attack bypassing defenders"
        else:
            ability_label = ""
        
        if is_opponent:
            base = f"[ID: {card.id}] {card.name} {cost_str} {stats_str} - {effect} | THREAT: {threat}"
        else:
            base = f"[ID: {card.id}] {card.name} {cost_str} {stats_str} - {effect}"
        
        if ability_label:
            base += f" | {ability_label}"
        return base
    else:
        # Action card - clearly label it cannot attack
        return f"[ID: {card.id}] {card.name} (ACTION CARD, cost {effective_cost}) - {effect} | ⚠️ Cannot tussle/attack"


def format_hand_for_planning(hand: list, game_engine=None, player=None) -> str:
    """Format all cards in hand for planning prompt."""
    if not hand:
        return "EMPTY"
    
    lines = []
    for card in hand:
        lines.append(f"  - {format_card_for_planning(card, game_engine, player, is_opponent=False)}")
    return "\n".join(lines)


def format_in_play_for_planning(in_play: list, game_engine=None, player=None, is_opponent: bool = False) -> str:
    """Format all cards in play for planning prompt."""
    if not in_play:
        return "NONE"
    
    lines = []
    for card in in_play:
        lines.append(f"  - {format_card_for_planning(card, game_engine, player, is_opponent=is_opponent)}")
    return "\n".join(lines)


def format_sleep_zone_for_planning(sleep_zone: list) -> str:
    """Format sleep zone cards (just names and IDs)."""
    if not sleep_zone:
        return "EMPTY"
    
    lines = []
    for card in sleep_zone:
        lines.append(f"  - [ID: {card.id}] {card.name}")
    return "\n".join(lines)
