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

from typing import List, Optional, Set
from .card_library import CARD_EFFECTS_LIBRARY


# =============================================================================
# Compact Rules Reference (Static)
# =============================================================================

COMPACT_RULES = """## Quick Rules Reference

### Zones & Card Types
| Zone | Purpose |
|------|---------|
| HAND | Cards you can play (hidden) |
| IN PLAY | Toys on battlefield (can attack) |
| SLEEP ZONE | Used/sleeped cards |

- **TOY**: Has SPD/STR/STA stats. Can tussle and direct attack.
- **ACTION**: No stats. Effect triggers, then card goes to YOUR sleep zone. **Cannot attack!**

### Core Actions
| Action | Cost | Requirement |
|--------|------|-------------|
| Play card | Card's cost | Card in hand |
| Tussle | 2 CC | **TOY** in your IN PLAY vs opponent toy |
| Direct Attack | 2 CC | **TOY** in your IN PLAY + opponent has 0 toys (max 2/turn) |
| Activate Ability | Varies | TOY with ability in your IN PLAY (e.g., Archer: 1 CC per use) |

### Combat Resolution (Tussle)
1. **Compare SPD**: Attacker gets +1 SPD bonus
2. **Higher SPD attacks first**: STR reduces opponent's STA
3. **STA ≤ 0 → sleeped** (moved to sleep zone, cannot counter-attack)
4. **Survivor counter-attacks** using their STR
5. **SPD TIE = simultaneous**: Both attack at same time (both can be sleeped!)

**"Win tussle" = opponent's toy sleeped. Knight auto-wins on YOUR turn (0 damage to Knight).**

### CC Math
```
cc_after = cc_before - cc_cost + cc_gained
```
- Surge: +1 CC | Rush: +2 CC (not turn 1)
- Wizard in play: All tussles cost 1 CC
- Raggy: Its own tussles cost 0 CC

### Key Constraints
- Max 7 CC | Turn 1: start with 2 CC | Other turns: +4 CC
- Cannot spend CC you don't have
- **Only TOY cards can tussle/direct attack** (they have stats!)
- Owner vs Controller: triggered effects benefit CONTROLLER
- **Continuous effects**: Active while toy is IN PLAY. Effect ends when toy is sleeped.
  - Example: Violin in play → +2 STR to all toys → Violin sleeped → buff ends
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
  - **Step 0: Play Archer (0 CC) → Archer now in IN PLAY**
  - Each use is a SEPARATE action: action_type: "activate_ability", cc_cost: 1
  - **FINISH what you start!** If target has 1-3 STA, use Archer to sleep it completely!
  - DON'T switch to tussle mid-way (wastes CC on play cost + tussle cost)
  - Example: Knight has 3 STA
    - GOOD: 3x Archer ability (3 CC) → Knight sleeped ✓
    - BAD: 2x Archer (2 CC) + play Umbruh (1 CC) + tussle (2 CC) = 5 CC wasted!""",
    
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
    
    "Knight": """**Knight** (1 CC, 4/4/3): On YOUR turn, wins ALL tussles it enters.
  - Opponent toy auto-sleeped AND Knight takes 0 damage (no counter-attack)
  - **ONLY works on Knight's CONTROLLER's turn!**
  - If OPPONENT has Knight and it's YOUR turn: Knight fights normally (use stats)
  - Don't over-analyze: If you can't win a tussle, skip it and try other options!""",
    
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
    
    "Surge": """**Surge** (ACTION, 0 CC): Gain 1 CC. Net +1 CC.
  - Play FIRST if it enables an attack you couldn't otherwise afford!
  - **FOLLOW THROUGH**: If you play Surge, USE the extra CC to attack!
  - Wasted if: You play Surge then just end turn (could have saved Surge for later)""",
    
    "Rush": """**Rush** (ACTION, 0 CC): Gain 2 CC. Net +2 CC. Cannot play turn 1. Play FIRST!""",
    
    "Drop": """**Drop** (ACTION, 2 CC): Sleep 1 target toy.""",
    
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
    
    "Copy": """**Copy** (ACTION, 0 CC): Becomes exact copy of one of YOUR toys in play.""",
    
    "Beary": """**Beary** (1 CC, 5/3/3): Cannot be targeted by opponent's Action cards.
  - Immune to opponent's Drop, Clean, Twist
  - CAN be affected by YOUR own effects (Monster, etc.)
  - NOT immune to tussle damage (combat is not an "effect")
  - High speed (5 SPD) makes it attack first in most tussles""",
    
    "Monster": """**Monster** (2 CC, 3/1/2): On play: Set ALL toys' STA to 1.
  - Affects ALL toys in play (yours AND opponent's)
  - Toys with max STA = 1 are SLEEPED instead (e.g., Gibbers 1/1/1 → sleeped!)
  - Monster enters at 1 STA too (reduced by its own effect)
  - Board equalizer when behind! Great vs low-STA threats like Gibbers""",
    
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

### Decision Priority (in order)
1. **WIN CHECK**: Can you sleep opponent's LAST cards this turn? → Do it!
2. **DIRECT ATTACK**: You have toy in play + opponent has 0 toys? → Attack! (2 CC each, max 2/turn)
   - **Check this AFTER every tussle!** Sleeping their last toy enables direct attacks!
3. **TUSSLE**: Can you win and sleep their toy? → Tussle! Then check if direct attack available!
4. **REMOVE THREATS**: Use Archer ability, Drop, Monster, tussle on CRITICAL/HIGH threats
   - **Gibbers active?** → Priority target! (1 STA = easy kill, removes +1 cost tax)
   - Monster can board-wipe low-STA threats (Gibbers sleeped, others reduced to 1 STA)
5. **DEFEND**: No toys in play? → Play ONE toy (preferably with good STA)
6. **END TURN**: Can't attack AND already have defense? → Save your cards!

### Action Sequencing (ORDER MATTERS!)
- **Surge/Rush FIRST**: If playing Surge enables an attack, play it and ATTACK!
- **Toys before attacks**: Must play toy to IN PLAY before tussle/direct attack with it
- **Check board after EACH action**: Did opponent just go to 0 toys? → Direct attack now available!
- **Abilities need toy in play**: Can't use Archer ability if Archer isn't in play yet
- **FINISH targets efficiently**: If Archer can sleep a toy in 1-3 more shots, DO IT (don't switch to expensive tussle)

### Critical Checks
- ✅ Every card in plan must be in YOUR HAND or IN PLAY (check IDs!)
- ✅ cc_after >= 0 after EVERY action (never go negative!)
- ✅ Only TOY cards can tussle/direct attack (check for SPD/STR/STA stats!)
- ✅ ACTION cards go to sleep zone after use - they're gone, can't attack with them!
- ✅ **Buff cards (VVAJ) are WASTED if you can't attack THIS TURN!**
- ✅ **FOLLOW THROUGH**: If you play Surge/Rush, USE the CC to attack! Don't end early!
- ✅ **EFFICIENCY**: Archer 3x (3 CC) beats play+tussle (3+ CC) to sleep 3-STA toy

### Turn 1 Traps (2 CC only!)
- **DON'T play VVAJ** if you can't attack this turn (buff expires!)
- **DON'T play Wizard (2 CC)** then try to tussle (0 CC left, need 1 CC!)
- **DO play 1 defensive toy** (Umbruh 1 CC or Beary 1 CC) → blocks direct attacks

### Mid-Turn State Changes (IMPORTANT!)
The board changes as you take actions. Re-evaluate after each action:
- After tussle sleeps opponent's LAST toy → **Direct attack now available!**
- After playing a toy → You can now tussle/attack with it
- After playing Surge → You have more CC for additional actions

### Quick Decision Rules (AVOID OVER-ANALYSIS!)
- **Can't win a tussle?** → Skip it, try other options (Drop, Archer, defend)
- **No good attacks?** → Play a defender and end turn
- **Confused about outcome?** → Pick the safest option and move on
- **Don't repeat the same analysis!** Make a decision and commit.

### Example: Tussle → Direct Attack Combo
Start: 4 CC, your Knight in play, opponent has 1 toy (their Knight)
```
1. tussle with Knight (2 CC) → opponent's Knight sleeped → OPPONENT NOW HAS 0 TOYS!
2. direct_attack (2 CC) → 1 card sleeped from opponent's hand
3. end_turn
Result: 4 CC → 2 cards sleeped = 2.0 CC/card efficiency ✓
```

### Example: Pure Direct Attack
Start: 4 CC, Knight in play, opponent has 0 toys
```
1. direct_attack (4-2=2 CC) → 1 card slept ✓
2. direct_attack (2-2=0 CC) → 2 cards slept ✓
3. end_turn
Result: 4 CC → 2 cards slept = 2.0 CC/card efficiency
```

### Output
Respond with TurnPlan JSON only. Use [ID: xxx] UUIDs for all card references.
Keep plan_reasoning CONCISE (1-3 sentences max). Do NOT repeat analysis.
"""


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
    prompt = f"""You are a GGLTCG turn planner. Maximize CC efficiency (target: ≤2.5 CC per opponent card slept).

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
    """Format a single card with full details for planning."""
    card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
    effect = card_info.get("effect", "")
    
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
            max_sta = game_engine.get_card_stat(card, "stamina")
        else:
            spd = card.get_effective_speed()
            str_val = card.get_effective_strength()
            cur_sta = card.get_effective_stamina()
            max_sta = card.stamina + card.modifications.get("stamina", 0)
        
        return f"[ID: {card.id}] {card.name} (cost {effective_cost}, {spd}/{str_val}/{cur_sta} STA)"
    else:
        return f"[ID: {card.id}] {card.name} (ACTION, cost {effective_cost})"


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
