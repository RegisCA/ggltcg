"""
Turn Planning Prompt for AI v3 - COMPACT VERSION.

Based on Gemini 3 Flash analysis with critical mechanics restored:
- Game state at the TOP (most important)
- Combat resolution included (tussle mechanics)
- Mid-turn state changes emphasized
- Card-specific docs only for cards in current game
- Action sequencing guidance

Target: ~60% reduction from original while keeping decision quality
"""

from typing import Set
from .card_library import CARD_EFFECTS_LIBRARY


# =============================================================================
# Compact Rules Reference (Static)
# =============================================================================

COMPACT_RULES = """## Quick Rules Reference

### Zones
| Zone | Purpose |
|------|---------|
| HAND | Cards you can play (hidden from opponent) |
| IN PLAY | Toys on battlefield (can attack/be attacked) |
| SLEEP ZONE | Used/defeated cards (out of game until recovered) |

### Card Types
- **TOY**: Has SPD/STR/STA stats. Can tussle and direct attack **IF STR > 0**.
- **ACTION**: No stats. Effect triggers on play, then goes to YOUR sleep zone. **Cannot attack!**

### Key Constraints
- Max 7 CC | Turn 1: 2 CC | Other turns: +4 CC (capped at 7)
- Owner vs Controller: triggered effects benefit CONTROLLER
- **Continuous effects**: Active while toy is IN PLAY. Ends when sleeped.
"""


# =============================================================================
# Threat Tiers (Compact Table)
# =============================================================================

THREAT_TABLE = """## Threat Priority
| Tier | Cards | Why |
|------|-------|-----|
| CRITICAL | Gibbers, Sock Sorcerer, Wizard | +1 cost tax / blocks removal / cheap tussles |
| HIGH | Belchaletta, Raggy, Knight, Paper Plane | +2 CC/turn, free tussles, auto-win, bypasses defense |
| MEDIUM | Ka, Drum, Violin, Demideca, Ballaber | Stat boosts, strong bodies |
| LOW | Archer, Beary | Cannot attack / defensive only |

**⚠️ GIBBERS RULE**: If opponent has Gibbers in play, ALL costs shown in hand include +1 CC modifier!
"""


# =============================================================================
# Card-Specific Documentation (Generated Per-Game)
# =============================================================================

# Only include documentation for cards that need special explanation
CARD_SPECIAL_DOCS = {
    "Archer": """**Archer** (0 CC, 0/0/5): CANNOT tussle or direct attack!
  - Ability: Spend 1 CC → Remove 1 STA from target opponent toy **IN PLAY**. **Counts toward efficiency!**
  - ⚠️ **ONLY targets toys IN PLAY RIGHT NOW** - cannot target opponent's hand!
  - ❌ **0 opponent toys in play = CANNOT USE ABILITY** (no valid targets exist!)
  - ❌ **DO NOT plan Archer ability hoping opponent "might play something"** - they won't play during YOUR turn!
  - ✅ If opponent has 0 toys: Just play Archer (0 CC) and end turn - ability unusable!
  - **Step 0: Play Archer (0 CC) → Archer now in IN PLAY**
  - Each use is a SEPARATE action: action_type: "activate_ability", cc_cost: 1
  - **FINISH what you start!** If target has 1-3 STA, use Archer to sleep it completely!
  - When target reaches 0 STA → sleeped! Include in expected_cards_slept!""",
    
    "Paper Plane": """**Paper Plane** (1 CC, 2/2/1): Can direct attack EVEN IF opponent has toys!
  - Use action_type: "direct_attack", NOT tussle
  - Bypasses the normal "opponent must have 0 toys" requirement""",
    
    "Wizard": """**Wizard** (2 CC, 1/3/3): While in YOUR play, all YOUR tussles cost 1 CC instead of 2.
  - Must be in play BEFORE tussle to get discount
  - Turn 1 trap: Play Wizard (2 CC → 0 CC left) → can't tussle (need 1 CC)!
  - Better: Play on turn 2+ when you have CC to spare""",
    
    "Raggy": """**Raggy** (3 CC, 2/3/2): THIS card's tussles cost 0 CC. Cannot tussle turn 1.
  - **FREE TUSSLES = ALWAYS USE THEM!** If Raggy can attack, DO IT!
  - Even if you can't sleep the target, chip damage is free
  - Example: Raggy in play, opponent has damaged toy → tussle for FREE!""",
    
    "Knight": """**Knight** (1 CC, 4/4/3):
  - **Active Effect**: On the CONTROLLER's turn, Knight wins ALL tussles.
  - **Resolution**: Opponent toy sleeped instantly; Knight takes 0 damage.
  - **Constraint**: If NOT the controller's turn, Knight uses normal SPD/STR/STA combat.
  - YOUR Knight on YOUR turn = guaranteed tussle win!
  - OPPONENT's Knight on YOUR turn = fights normally (use stats)""",
    
    "Gibbers": """**Gibbers** (1 CC, 1/1/1): While in OPPONENT's play, YOUR cards cost +1 CC.
  - **CRITICAL PRIORITY**: Remove FIRST to restore normal costs!
  - Affects BOTH toy and action card costs
  - Methods to remove: Drop, Monster, winning tussle (1 STA = easy to sleep)""",
    
    "Umbruh": """**Umbruh** (1 CC, 4/4/4): When sleeped, CONTROLLER gains +1 CC.
  - YOUR Umbruh sleeped = YOU +1 CC (good)
  - OPPONENT's Umbruh sleeped = THEY +1 CC (still sleep it if efficient)""",
    
    "Belchaletta": """**Belchaletta** (1 CC, 3/3/4): Controller gains +2 CC at start of their turn.""",
    
    "Hind Leg Kicker": """**Hind Leg Kicker** (1 CC, 3/3/1): Controller gains +1 CC when playing other cards.
  - Play HLK FIRST, then other cards to maximize CC refund.""",
    
    "Sock Sorcerer": """**Sock Sorcerer** (3 CC, 3/3/5): Blocks ALL opponent effects on your toys.
  - Cannot be targeted by Drop, Clean, Twist, etc.""",
    
    "Dream": """**Dream** (4 CC, 4/5/4): Costs 1 less per card in YOUR sleep zone.
  - Play action cards FIRST to reduce Dream's cost.""",
    
    "Surge": """**Surge** (ACTION, 0 CC): Gain 1 CC.
  - **CC BRIDGE**: Transforms 0 CC into 1 CC for your NEXT action!
  - After Surge → Your CC increases → NOW you can afford more attacks!
  - Play FIRST if it enables an attack you couldn't otherwise afford!
  - ❌ Wasted if: You play Surge then just end turn (save it for later)""",
    
    "Rush": """**Rush** (ACTION, 0 CC): Gain 2 CC. Net +2 CC. Cannot play turn 1. Play FIRST!""",
    
    "Drop": """**Drop** (ACTION, 2 CC): Sleep 1 target toy **IN PLAY**. **Counts toward efficiency!**
  - ⚠️ **REQUIRES VALID TARGET**: Opponent must have ≥1 toy IN PLAY
  - ❌ Turn 1 trap: If opponent has 0 toys in play, Drop is USELESS!
  - Cannot target cards in hand or sleep zone.
  - This IS sleeping an opponent card → include in expected_cards_slept!""",
    
    "Wake": """**Wake** (ACTION, 1 CC): Return 1 card from YOUR sleep zone to YOUR HAND (not play!).
  - Must then PAY CC and PLAY the card to use it.
  - Example: Wake (1 CC) + Play Knight (1 CC) = 2 CC total to get Knight ready.""",
    
    "Twist": """**Twist** (ACTION, 3 CC): Take control of 1 opponent toy (stays in play, you control it).""",
    
    "Clean": """**Clean** (ACTION, 3 CC): Sleep ALL toys in play (yours too!).""",
    
    "VeryVeryAppleJuice": """**VeryVeryAppleJuice** (ACTION, 0 CC): +1/+1/+1 to YOUR toys THIS TURN ONLY.
  - **BUFF EXPIRES AT END OF TURN** - does NOT carry to next turn!
  - ONLY play if you will tussle/attack THIS turn
  - Wasted if: no toys in play, no targets, or no CC to attack
  - Example: Your 3 STR toy vs 4 STA opponent → normally can't sleep
    - VVAJ first → 4 STR vs 4 STA → opponent sleeped! ✓""",
    
    "Copy": """**Copy** (ACTION, 0 CC): Becomes exact copy of one of YOUR toys **IN PLAY**.
  - ⚠️ **CAN ONLY COPY YOUR OWN TOYS** - NOT opponent's!
  - ❌ Cannot copy if YOU have no toys in play
  - Cost becomes the copied toy's original cost.""",
    
    "Beary": """**Beary** (1 CC, 5/3/3): Cannot be targeted by opponent's Action cards.
  - Immune to opponent's Drop, Clean, Twist
  - CAN be affected by YOUR own effects (Monster, etc.)
  - NOT immune to tussle damage (combat is not an "effect")
  - High speed (5 SPD) makes it attack first in most tussles""",
    
    "Monster": """**Monster** (2 CC, 3/1/2): On play: Set ALL toys' STA to 1.
  - Affects ALL toys in play (yours AND opponent's)
  - Toys with max STA = 1 are SLEEPED instead (e.g., Gibbers 1/1/1 → sleeped!) **Counts toward efficiency!**
  - Monster enters at 1 STA too (reduced by its own effect)
  - Board equalizer when behind! Great vs low-STA threats like Gibbers
  - Any opponent toys sleeped by Monster → include in expected_cards_slept!""",
    
    "Ka": """**Ka** (2 CC, 5/9/1): All your OTHER toys get +2 STR (continuous).
  - High offensive stats (9 STR!) but fragile (1 STA)
  - Buff doesn't apply to Ka itself (only "other" toys)
  - Easy to sleep with any damage - protect it!""",
    
    "Violin": """**Violin** (1 CC, 3/1/2): All your toys get +2 STR (continuous).
  - Buff applies while Violin is in play (including Violin itself)
  - Stacks with Ka if both in play (+4 STR total to other toys!)
  - Low stats (1 STR, 2 STA) - mainly for buff support""",
    
    "Sun": """**Sun** (ACTION, 3 CC): Return up to 2 cards from YOUR sleep zone to YOUR HAND.
  - Recovered cards go to HAND, not into play
  - Must PLAY them (pay their cost) to use them
  - Useless if sleep zone is empty!""",
}


def get_relevant_card_docs(card_names: Set[str]) -> str:
    """Generate documentation only for cards in the current game."""
    docs = []
    for name in sorted(card_names):
        if name in CARD_SPECIAL_DOCS:
            docs.append(CARD_SPECIAL_DOCS[name])
    
    if not docs:
        return ""
    
    return "## Cards in This Game\n" + "\n\n".join(docs)


# =============================================================================
# Compact Planning Instructions (with decision framework)
# =============================================================================

PLANNING_INSTRUCTIONS = """## Your Task: Create Turn Plan

You are an AGGRESSIVE BOARD MAXIMIZER. Goal: SLEEP AS MANY OPPONENT CARDS AS POSSIBLE each turn.

---
## ACTION REGISTRY (Costs are FIXED!)

| Action | Cost | Attacker Requirement |
|--------|------|---------------------|
| play_card | Card's cost | Card in YOUR HAND |
| tussle | 2 CC | TOY in YOUR IN PLAY with STR > 0 and NO [NO TUSSLE] tag |
| direct_attack | 2 CC | TOY in YOUR IN PLAY with STR > 0, opponent has 0 toys (max 2/turn, NO target) |
| activate_ability | Varies | TOY in YOUR IN PLAY with ability (e.g., Archer: 1 CC) |
| end_turn | 0 CC | Always valid |

**If a card has [NO TUSSLE] tag or STR = 0, it CANNOT be the attacker for tussle/direct_attack!**

---
## PRE-ACTION CHECKLIST (Run for EVERY action!)

**1. PERMISSION CHECK**:
- Is the card in the correct zone? (Hand for play_card, In Play for tussle/ability)
- Does the card have a [NO TUSSLE] tag? → Cannot tussle/direct_attack with it!
- Is STR > 0? → If STR = 0, cannot tussle/direct_attack!

**2. RESOURCE CHECK**:
- Do I have enough CC? (Tussle/Direct = 2 CC, Ability = varies)
- cc_after = cc_before - cost + gains. **Must be >= 0!**

**3. TARGET CHECK**:
- Is the target currently IN PLAY? (Not in hand, not in sleep zone!)
- Did I already sleep this target earlier in my plan? → It's GONE, pick another!
- For direct_attack: opponent must have **exactly 0 toys** in play. NO target_ids!

---
## EXECUTION PROTOCOL

**STEP 1: Calculate MAXIMUM POTENTIAL CC**
- Starting CC + Surge (+1) + Rush (+2, not turn 1) + HLK (+1 per other card played)

**STEP 2: Generate Actions (EXHAUSTIVE LOOP)**
Repeat until BOTH true:
1. CC < 2 (or < 1 with Wizard, or 0 with Raggy)
2. No valid attackers OR no valid targets

**Priority Order**:
1. WIN CHECK → Sleep opponent's last cards?
2. TUSSLE → Opponent has toys? Attack with your strongest STR > 0 toy!
3. DIRECT ATTACK → Opponent has 0 toys? Attack their hand! (no target needed)
4. ABILITIES → Archer ability (1 CC) to chip damage
5. DEFEND → No toys? Play one.
6. END TURN → Nothing else possible.

**STEP 3: Post-Action Audit**
After each action, update:
- CC remaining (subtract cost, add gains)
- Board state (sleeped cards are GONE from play!)
- One toy can attack MULTIPLE times per turn!

---
## TUSSLE COMBAT MATH

```
Damage dealt = Attacker's STR
Target sleeped when: Target's STA - Damage <= 0
```

**Example**: Umbruh (4 STR) vs Archer (5 STA) → 5 - 4 = 1 STA left → NOT sleeped!

- Higher SPD (attacker +1 bonus) attacks first
- Survivor counter-attacks
- SPD tie = simultaneous damage
- Knight on YOUR turn = auto-win (opponent sleeped, 0 damage to Knight)

---
## CC MATH (CRITICAL - Calculate BEFORE writing each action!)

**⚠️ STOP AND VERIFY**: Before writing ANY action, mentally compute:
```
cc_after = cc_before - cc_cost + cc_gained
```
**If cc_after < 0, you CANNOT afford this action! Pick something cheaper or end turn.**

**Fixed Costs (memorize!):**
- Tussle: **2 CC** (always, unless Wizard in play: 1 CC, or Raggy self: 0 CC)
- Direct Attack: **2 CC** (always)
- Surge: 0 cost, **ADDS +1** → cc_after = cc_before + 1
- Rush: 0 cost, **ADDS +2** → cc_after = cc_before + 2

**Step-by-step verification example:**
```
Start: 2 CC
→ Action 1: Play Surge. Cost 0, Gain +1. NEW CC: 2 - 0 + 1 = 3 ✓
→ Action 2: Play Knight. Cost 1, Gain 0. NEW CC: 3 - 1 + 0 = 2 ✓
→ Action 3: Direct Attack. Cost 2, Gain 0. NEW CC: 2 - 2 + 0 = 0 ✓
```
**Each action's cc_after becomes the next action's cc_before!**

---
## HARD CONSTRAINTS (Violations = Invalid Plan!)

1. **[NO TUSSLE] tag** → Card CANNOT be attacker for tussle/direct_attack
2. **STR = 0** → Card CANNOT be attacker (no damage dealt!)
3. **cc_after < 0** → ILLEGAL! You don't have enough CC!
4. **Costs are FIXED** → Tussle/Direct always 2 CC (exceptions: Wizard -1, Raggy free)
5. **Target not in play** → ILLEGAL! Sleeped/hand cards can't be targeted!
6. **Direct attack with target_ids** → ILLEGAL! Direct attack has NO target!
7. **Direct attack when opponent has toys** → ILLEGAL! Use tussle instead!
8. **Drop/Archer ability with 0 opponent toys** → ILLEGAL! No valid targets!
9. **Copy on opponent's toy** → ILLEGAL! Copy only YOUR toys!
10. **play_card from SLEEP ZONE** → ILLEGAL! Sleep zone cards are NOT in your hand!
    - ⚠️ **WAKE REQUIRED**: To use a sleeped card: Wake (1 CC) → card goes to HAND → then play_card (pay cost)
    - Check the **Hand:** section for valid play_card targets, NOT Sleep Zone!

---
## EXAMPLES

**Turn 1 with Surge**:
```
Start: 2 CC, Hand: [Surge, Knight], Opponent: 0 toys
1. play_card Surge (0 CC, +1 gain) → cc_after = 2-0+1 = 3
2. play_card Knight (1 CC) → cc_after = 3-1 = 2
3. direct_attack Knight (2 CC, NO target) → cc_after = 2-2 = 0 → 1 card slept!
4. end_turn
Result: 3 CC used → 1 card slept
```

**Multi-Tussle with One Toy**:
```
Start: 6 CC, Your Umbruh in play, Opponent: Paper Plane, Knight
1. tussle Umbruh→Paper Plane (2 CC) → cc_after=4, Paper Plane sleeped
2. tussle Umbruh→Knight (2 CC) → cc_after=2, Knight sleeped → 0 toys left!
3. direct_attack Umbruh (2 CC, NO target) → cc_after=0 → 1 hand card slept
4. end_turn
Result: 6 CC → 3 cards slept (same toy tussled twice!)
```

**Recovering a Sleeped Card with Wake**:
```
Start: 6 CC, Hand: [Wake, Surge], Sleep Zone: [Knight], Opponent: Knight in play
1. play_card Wake (1 CC) → cc_after=5, Knight returns to HAND (not play!)
2. play_card Knight (1 CC) → cc_after=4, Knight now IN PLAY
3. tussle Knight→Opponent Knight (2 CC) → cc_after=2, Opponent Knight sleeped
4. direct_attack Knight (2 CC) → cc_after=0 → 1 card slept from hand
5. end_turn
Result: 6 CC → 2 cards slept
⚠️ WRONG: Trying to play_card Knight directly from sleep zone WITHOUT Wake first!
```

---
## ZERO-ACTION AUDIT

If ending with CC >= 2, you MUST provide `residual_cc_justification`:
- "All my toys have [NO TUSSLE] tag" → Valid (cite card ID)
- "All my toys have 0 STR" → Valid (cite card ID)  
- "No valid targets remain" → Valid
- "I have CC and attackers but ended anyway" → INVALID PLAN!

---
## OUTPUT
Respond with TurnPlan JSON only. Use [ID: xxx] UUIDs for all card references.
Keep plan_reasoning CONCISE (1-3 sentences). Do NOT repeat analysis.

**cc_cost MUST be EXACT**:
- play_card: Use the card's actual cost from hand (shown in parentheses)
- tussle: Always 2 (or 1 with Wizard, 0 for Raggy)
- direct_attack: Always 2
- activate_ability: Use ability cost (e.g., Archer: 1)

**ZONE CHECK for card_id**:
- play_card: card_id MUST be from **Hand:** section
- tussle/direct_attack/activate_ability: card_id MUST be from **Your Toys:** (In Play) section
- Sleep Zone cards CANNOT be used until recovered with Wake!"""


# =============================================================================
# Main Prompt Generator
# =============================================================================

def get_planning_prompt_v2(
    game_state_text: str,
    hand_details: str,
    in_play_details: str,
    card_names_in_game: Set[str],
) -> str:
    """
    Generate compact planning prompt.
    
    Args:
        game_state_text: Current game state
        hand_details: Hand cards with IDs
        in_play_details: In-play cards with IDs
        card_names_in_game: Set of all card names visible in this game
    """
    card_docs = get_relevant_card_docs(card_names_in_game)
    
    # Game state FIRST (most important for decision-making)
    prompt = f"""You are a GGLTCG turn planner. Maximize CC efficiency (target: <=2.5 CC per opponent card slept).

---
## CURRENT GAME STATE

{game_state_text}

### YOUR CARDS (with IDs)
**Hand:**
{hand_details}

**In Play:**
{in_play_details}

---

{COMPACT_RULES}

{THREAT_TABLE}

{card_docs}

{PLANNING_INSTRUCTIONS}"""

    return prompt


# =============================================================================
# Card Formatters (Reused from original)
# =============================================================================

def format_card_for_planning(card, game_engine=None, player=None, is_opponent: bool = False) -> str:
    """Format a single card with full details for planning, including restriction tags."""
    # Calculate effective cost
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
        
        # Add restriction tag for toys that cannot tussle/direct attack
        restriction = ""
        if str_val == 0:
            restriction = " [NO TUSSLE - 0 STR]"
        
        return f"[ID: {card.id}] {card.name} (cost {effective_cost}, {spd}/{str_val}/{cur_sta} SPD/STR/STA){restriction}"
    else:
        return f"[ID: {card.id}] {card.name} (ACTION, cost {effective_cost}) [NO TUSSLE - Action cards cannot attack]"


def format_hand_for_planning_v2(hand: list, game_engine=None, player=None) -> str:
    """Format all cards in hand for planning prompt."""
    if not hand:
        return "EMPTY"
    return "\n".join(f"- {format_card_for_planning(card, game_engine, player)}" for card in hand)


def format_in_play_for_planning_v2(in_play: list, game_engine=None, player=None) -> str:
    """Format all cards in play for planning prompt."""
    if not in_play:
        return "NONE"
    return "\n".join(f"- {format_card_for_planning(card, game_engine, player)}" for card in in_play)


def collect_card_names(player_hand, player_in_play, opponent_in_play, opponent_sleep=None) -> Set[str]:
    """Collect all unique card names visible in the game."""
    names = set()
    for card in player_hand:
        names.add(card.name)
    for card in player_in_play:
        names.add(card.name)
    for card in opponent_in_play:
        names.add(card.name)
    if opponent_sleep:
        for card in opponent_sleep:
            names.add(card.name)
    return names


# =============================================================================
# Legacy API Compatibility
# =============================================================================

# Keep old function signature working for now
def get_planning_prompt(
    game_state_text: str,
    hand_details: str,
    in_play_details: str,
) -> str:
    """
    Legacy function - redirects to v2 with default card set.
    
    For full optimization, use get_planning_prompt_v2 with card_names_in_game.
    """
    # Default to including all special cards (less optimal but compatible)
    all_cards = set(CARD_SPECIAL_DOCS.keys())
    return get_planning_prompt_v2(game_state_text, hand_details, in_play_details, all_cards)
