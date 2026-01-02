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
- **DEFENSE**: ALL toys (even 0 STR like Archer) block opponent direct attacks!
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
  - **DEFENDER**: Still counts as a toy! Blocks opponent direct attacks.
  - Ability: 1 CC → Remove 1 STA from target opponent toy **IN PLAY**
  - ⚠️ REQUIRES TARGET ID: You MUST specify which opponent toy to target (target_ids=["card_id"]).
  - ⚠️ ONLY targets toys IN PLAY - cannot target hand!
  - ❌ 0 opponent toys = CANNOT USE ABILITY (no valid target!)
  - ❌ DO NOT plan Archer ability if opponent has 0 toys!""",
    
    "Paper Plane": """**Paper Plane** (1 CC, 2/2/1): Can direct attack EVEN IF opponent has toys!
  - Use action_type: "direct_attack" (COST: 2 CC)
  - Bypasses the normal "opponent must have 0 toys" requirement
  - STILL COSTS 2 CC!""",
    
    "Wizard": """**Wizard** (2 CC, 1/3/3): While in YOUR play, all YOUR tussles cost 1 CC instead of 2.
  - Must be in play BEFORE tussle to get discount
  - Turn 1 trap: Play Wizard (2 CC → 0 CC left) → can't tussle (need 1 CC)!
  - Better: Play on turn 2+ when you have CC to spare""",
    
    "Raggy": """**Raggy** (3 CC, 2/3/2): THIS card's tussles cost 0 CC. Cannot tussle turn 1.
  - **FREE TUSSLES = ALWAYS USE THEM!** If Raggy can attack, DO IT!
  - Even if you can't sleep the target, chip damage is free
  - Example: Raggy in play, opponent has damaged toy → tussle for FREE!""",
    
    "Knight": """**Knight** (1 CC, 4/4/3): On YOUR turn, Knight auto-wins ALL tussles.
  - Opponent toy ALWAYS sleeped, Knight takes 0 damage
  - ✅ No need to reduce target STA first - Knight wins regardless!
  - ⚠️ Only works on Knight's CONTROLLER's turn
  - ⚠️ REQUIRES TARGET: You CANNOT tussle if opponent has 0 toys!
  - If OPPONENT has Knight and it's YOUR turn: Knight fights normally""",
    
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
  - **COMBO ENABLER**: If you have 4 CC, Surge gives you 5 CC.
    - 4 CC = Knight(1) + Tussle(2) = 3 CC used (1 wasted).
    - 5 CC = Knight(1) + Tussle(2) + Direct Attack(2) = 5 CC used (PERFECT!).
  - ALWAYS play Surge if it allows you to fit ONE MORE ACTION into your turn!""",
    
    "Rush": """**Rush** (ACTION, 0 CC): Gain 2 CC. Net +2 CC. Cannot play turn 1. Play FIRST!""",
    
    "Drop": """**Drop** (ACTION, 2 CC): Sleep 1 target toy IN PLAY.
⚠️ REQUIRES TARGET ID: You MUST specify which opponent toy to sleep (target_ids=["card_id"]).
⚠️ REQUIRES TARGET IN PLAY: Opponent must have 1+ toys NOW!
❌ 0 opponent toys = Drop is USELESS (no valid target!)
❌ Turn 1 trap: As Player 1, opponent has 0 toys - DON'T play Drop!""",
    
    "Wake": """**Wake** (ACTION, 1 CC): Return 1 card from YOUR sleep zone to YOUR HAND (not play!).
  - ⚠️ REQUIRES TARGET ID: You MUST specify which card to wake (target_ids=["card_id"]).
  - ❌ target_ids: null is ILLEGAL!
  - Must then PAY CC and PLAY the card to use it.
  - Example: Wake (1 CC) + Play Knight (1 CC) = 2 CC total to get Knight ready.""",
    
    "Twist": """**Twist** (ACTION, 3 CC): Take control of 1 opponent toy (stays in play, you control it).
  - ⚠️ REQUIRES TARGET ID: You MUST specify which opponent toy to steal (target_ids=["card_id"]).
  - ❌ 0 opponent toys = Twist is USELESS!""",
    
    "Clean": """**Clean** (ACTION, 3 CC): Sleep ALL toys in play (yours too!).
  - NO TARGET ID NEEDED (affects board).""",
    
    "VeryVeryAppleJuice": """**VeryVeryAppleJuice** (ACTION, 0 CC): +1/+1/+1 to YOUR toys THIS TURN ONLY.
  - NO TARGET ID NEEDED (affects all your toys).
  - **BUFF EXPIRES AT END OF TURN** - does NOT carry to next turn!
  - ONLY play if you will tussle/attack THIS turn
  - Wasted if: no toys in play, no targets, or no CC to attack
  - Example: Your 3 STR toy vs 4 STA opponent → normally can't sleep
    - VVAJ first → 4 STR vs 4 STA → opponent sleeped! ✓""",
    
    "Copy": """**Copy** (ACTION, 0 CC): Create exact copy of one of YOUR toys in play.
⚠️ REQUIRES TARGET ID: You MUST specify which of YOUR toys to copy (target_ids=["card_id"]).
⚠️ Can ONLY target YOUR toys - NOT opponent's!
❌ Copy on opponent's toy → ILLEGAL!
Cost to play = cost of the toy being copied.""",
    
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
  - ⚠️ REQUIRES TARGET IDs: You MUST specify 1 or 2 cards to return (target_ids=["id1", "id2"]).
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

PLANNING_INSTRUCTIONS = """## EXECUTION PROTOCOL: AGGRESSIVE BOARD MAXIMIZER

### I. Resource Calculation (Mandatory Pre-Check)
1. **Calculate Budget**: Start_CC + Potential_Gains (Surge=+1, Rush=+2).
2. **Hard Limit**: You CANNOT spend more than this Budget.
3. **Negative CC Ban**: If `cc_after` < 0 at ANY step, the plan is INVALID.
   - Example: 2 CC available. Plan: Knight(1) + Tussle(2) = 3 CC. **INVALID**.
   - **STOP**. Do not output this plan.

### II. The "Archer/Toy" Logic Gate (Direct Attack Rules)
- **Rule**: Direct Attack is ONLY valid if opponent has **EXACTLY 0 TOYS** in play.
- **COUNTING RULE**:
  - Count ALL opponent cards in "In Play".
  - Archer counts as 1.
  - 0-Strength toys count as 1.
  - 0-Stamina toys (if awake) count as 1.
- **CONSTRAINT**: If Count > 0, `direct_attack` is **FORBIDDEN**.
  - You CANNOT ignore Archer.
  - You CANNOT ignore 0-Strength toys.
  - You MUST sleep them first (using Tussle or Abilities).

### III. Combat Simulation Protocol (Suicide Prevention)
- **Step 1**: Calculate effective SPD: (Attacker_SPD + 1) vs Defender_SPD.
- **Step 2**: The faster card deals damage FIRST.
- **Step 3**: **DEATH CHECK**: If the first hit reduces target STA to <= 0, the target DIES (Sleeps).
- **Step 4**: **DEAD TOYS DEAL 0 DAMAGE**.
  - If you attack a faster, stronger enemy: You die. You deal 0 damage. You waste 2 CC.
  - **RESULT**: Opponent cards slept = 0. Your cards slept = 1.
  - **VERDICT**: This is a **NET LOSS**. DO NOT DO IT.
  - **EXCEPTION**: If speeds are TIED, both deal damage.

### IV. Zone Discipline (Sleep Zone Trap)
- **HAND**: Cards you can `play_card`.
- **IN PLAY**: Toys you can `tussle` or `activate_ability`.
- **SLEEP ZONE**: **LOCKED**.
  - You CANNOT `play_card` from Sleep Zone.
  - You CANNOT `tussle` with Sleep Zone cards.
  - **ONLY WAY OUT**: Use `Wake` action first.
  - **Sequence**: `play_card` (Wake) -> `play_card` (Recovered Card).

---
## ACTION REGISTRY (Costs are FIXED!)

| Action | Cost | Attacker Requirement |
|--------|------|---------------------|
| play_card | Card's cost | Card in YOUR HAND (NOT Sleep Zone!) |
| tussle | 2 CC | TOY in YOUR IN PLAY with STR > 0 and NO [NO TUSSLE] tag. **OPPONENT MUST HAVE 1+ TOYS** |
| direct_attack | 2 CC | TOY in YOUR IN PLAY with STR > 0, opponent has 0 toys (max 2/turn, NO target). **BLOCKED BY ANY OPPONENT TOY (even 0 STR ones like Archer!)** |
| activate_ability | Varies | TOY in YOUR IN PLAY with ability (e.g., Archer: 1 CC) |
| end_turn | 0 CC | Always valid |

**If a card has [NO TUSSLE] tag or STR = 0, it CANNOT be the attacker for tussle/direct_attack!**

---
## PRE-ACTION CHECKLIST (Run for EVERY action!)

**1. PERMISSION CHECK**:
- Is the card in the correct zone? (Hand for play_card, In Play for tussle/ability)
- **SLEEP ZONE TRAP**: You CANNOT `play_card` from the Sleep Zone! You MUST use `Wake` first to return it to hand.
- **WAKE CHECK**: Does Wake have a target_id? Is that target in the Sleep Zone?
- **WAKE SEQUENCE**: Wake (1 CC) -> Play Card (Cost) -> Use Card. You cannot skip the "Play Card" step!
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
## JSON OUTPUT RULES (STRICT)

1. **NO IMPLICIT ACTIONS**: Every step must be EXPLICITLY listed in the `action_sequence`.
   - **BAD**: "Wake Umbruh" (implies playing Wake AND playing Umbruh)
   - **GOOD**: 
     1. `play_card`: Wake (target: Umbruh)
     2. `play_card`: Umbruh
     3. `tussle`: Umbruh
   - **BAD**: "Surge then Knight" (implies playing Surge AND playing Knight)
   - **GOOD**:
     1. `play_card`: Surge
     2. `play_card`: Knight

2. **SETUP CARDS FIRST**: If you use Surge/Wake, they must be the FIRST actions in the sequence.
   - You cannot use the CC from Surge if you haven't played it yet!
   - You cannot play a card from Sleep Zone if you haven't played Wake yet!

3. **ONE ACTION PER STEP**: Do not combine actions.

4. **CONCISENESS**: `plan_reasoning` must be < 500 characters. Be brief.

---
## EXECUTION PROTOCOL

**STEP 1: Calculate AVAILABLE CC (HARD LIMIT)**
- Starting CC + Surge (+1) + Rush (+2, not turn 1) + HLK (+1 per other card played)
- **THIS IS YOUR BUDGET.** You cannot spend more than this!
- If you have Surge in hand, assume you have +1 CC available for your sequence.
- **EXAMPLE**: 4 CC + Surge = 5 CC. You can play Knight(1) + Tussle(2) + Direct Attack(2) = 5 CC.
- **WITHOUT SURGE**: 4 CC. Knight(1) + Tussle(2) = 3 CC. 1 CC wasted.
- **CONCLUSION**: Playing Surge enables the extra attack. PLAY SURGE!
- **CRITICAL**: If your plan relies on Surge CC, you MUST play Surge FIRST!
- **CRITICAL**: Surge costs 0 CC. It does NOT cost 1 CC. It GIVES 1 CC.

**STEP 2: BUDGET CHECK (CRITICAL)**
- Before finalizing any sequence, sum the costs: Cost1 + Cost2 + ...
- If Sum > Available CC: **ABORT SEQUENCE**.
- You CANNOT spend 3 CC if you only have 2 CC.
- Example: 2 CC available. Play Knight (1) + Direct Attack (2) = 3 CC. **IMPOSSIBLE**.
- **NEGATIVE CC IS BANNED**: If `cc_after` < 0 at any step, the plan is INVALID.
- **MATH CHECK**: 0 - 2 = -2. THIS IS ILLEGAL. STOP.

**STEP 3: VERIFY OPPONENT BOARD (Dynamic Tracking)**
- **START**: Count opponent toys IN PLAY (N).
- **CRITICAL**: 0 STR toys (like Archer) COUNT AS TOYS!
- **ACTION**: If you sleep a toy, N = N - 1.
- **RULE**: You CANNOT `direct_attack` unless N = 0.
- **EXAMPLE**: Opponent has 2 toys. You sleep 1. Remaining = 1. Direct Attack = **ILLEGAL**.
- **EXAMPLE**: Opponent has Archer (0 STR). Remaining = 1. Direct Attack = **ILLEGAL**.
- **HALLUCINATION CHECK**: Did you forget Archer? Archer is a toy. If Archer is present, N >= 1.

**STEP 4: Generate Actions (EXHAUSTIVE LOOP)**
Repeat until BOTH true:
1. CC < 2 (CHECK SURGE! If CC=1 and you have Surge, play it to get 2 CC!)
2. No valid attackers OR no valid targets

**Priority Order**:
1. WIN CHECK → Sleep opponent's last cards?
2. SURGE/RUSH → **ALWAYS PLAY FIRST** if you have them! They are free CC!
   - Exception: Don't play Rush on Turn 1.
   - Exception: Don't play if you have 0 cards to spend the CC on.
3. TUSSLE → Opponent has toys? Attack with your strongest STR > 0 toy!
   - **REQUIREMENT**: Opponent MUST have at least 1 toy in play.
   - **SUICIDE CHECK**: Before attacking, check speeds!
     - If Defender SPD > (Attacker SPD + 1) AND Defender STR >= Attacker STA:
     - **STOP!** This is SUICIDE. You die. You deal 0 damage.
     - **RESULT**: 0 Opponent cards slept. 1 Your card slept.
     - **DECISION**: DO NOT ATTACK. End Turn is better.
   - **MANDATORY**: If opponent has toys and it is NOT suicide, you MUST TUSSLE.
   - **BANNED**: You CANNOT use `direct_attack` if opponent has toys!
4. DIRECT ATTACK → Opponent has 0 toys? Attack their hand! (no target_ids needed)
   - **CONDITION**: Only valid if opponent has EXACTLY 0 toys in play.
   - **ARCHER CHECK**: If Archer is in play, Count is 1. You CANNOT direct attack.
   - **COUNT CHECK**: If you started with 2 toys and slept 1, you have 1 left. NO DIRECT ATTACK.
5. ABILITIES → Archer ability (1 CC) to chip damage
6. DEFEND → No toys? Play one.
7. END TURN → Nothing else possible.

**MULTI-STEP PLANNING**:
- **NEVER STOP** after just one action if you have CC left!
- **EXAMPLE**: Tussle (2 CC) -> Sleep Opponent -> Still have 2 CC? -> Tussle AGAIN!
- **EXAMPLE**: Tussle (2 CC) -> Sleep Opponent -> 0 Toys left? -> Direct Attack (2 CC)!
- **MAXIMIZE**: Use EVERY point of CC to sleep cards.

**STEP 5: Post-Action Audit (MATH CHECK)**
After each action, you MUST calculate:
1. **CC Math**: `cc_after = cc_before - cost`.
   - If `cc_after` < 0, the action is **IMPOSSIBLE**. DELETE IT.
   - **Example**: 0 CC - 2 CC = -2. **STOP**.
2. **Toy Math**: `toys_remaining = toys_before - slept`.
   - If `toys_remaining` > 0, `direct_attack` is **IMPOSSIBLE**. DELETE IT.
   - **Example**: 2 toys - 1 slept = 1 remaining. Direct Attack = **ILLEGAL**.
3. **Sleep Zone Check**: Did you play a card from Sleep Zone?
   - **ILLEGAL**: You MUST use Wake first.
   - **CHECK**: Is the card in "Your Sleep Zone"? If yes, you need Wake.

---
## TUSSLE COMBAT MATH (Step-by-Step)

**STEP 1: Who hits first?**
- Attacker Speed = Card SPD + 1
- Defender Speed = Card SPD
- **WINNER**: Whichever number is HIGHER.
- **TIE**: Both hit at same time.

**DAMAGE TABLE (Who deals damage?)**
| Winner (Faster) | Loser (Slower) | Result |
|-----------------|----------------|--------|
| YOU             | Opponent       | You deal damage. Opponent deals damage ONLY if they survive. |
| OPPONENT        | YOU            | Opponent deals damage. **YOU DEAL 0 DAMAGE** (because you are dead). |

**STEP 2: Damage Resolution**
- **Scenario A: Attacker is Faster**
  1. Attacker deals damage (STR).
  2. If Defender dies (STA <= 0) → Defender deals **0 DAMAGE** back.
  3. If Defender survives → Defender deals damage back.

- **Scenario B: Defender is Faster (DANGER!)**
  1. Defender deals damage (STR).
  2. If Attacker dies (STA <= 0) → Attacker deals **0 DAMAGE**.
  3. **RESULT**: You wasted 2 CC and your toy died for nothing. **DO NOT DO THIS.**

**STEP 3: Suicide Check**
- Is Defender SPD > (Your SPD + 1)?
- Is Defender STR >= Your STA?
- If YES to both → **STOP!** You will die without dealing damage.

**HALLUCINATION CHECK**:
- Did you say "Both cards sleeped"?
- CHECK SPEEDS!
- If speeds are different, ONE card hits first.
- If that hit kills, the other card DOES NOT HIT BACK.
- **THERE IS NO MUTUAL DESTRUCTION UNLESS SPEEDS ARE TIED.**
- **Example**: 3 vs 4. 4 hits first. If 4 kills 3, then 3 deals **0 DAMAGE**.
- **MYTH**: "I deal damage even if I die." -> **FALSE**. Dead toys deal 0 damage.
- **FACT**: If you die first, the opponent takes **0 DAMAGE**.

**Example - Attacker Wins Clean**:
Your Umbruh (4/4/4) attacks Opponent's Umbruh (4/4/4)
- Your SPD: 4+1 = 5 (attacker bonus)
- Opponent SPD: 4
- You attack first: 4 STR vs 4 STA → Opponent SLEEPED
- Opponent cannot counter-attack (already sleeped!)
- Result: 1 opponent card sleeped, your Umbruh takes 0 damage

---
## CC MATH (Calculate after EVERY action!)

```
cc_after = cc_before - cc_cost + cc_gained
```

**CRITICAL RULE**: If `cc_after` becomes 0, you CANNOT take any more actions that cost CC!
**STOP IMMEDIATELY** if you run out of CC. Do not hallucinate extra CC.
**VERIFY**: 1 - 2 = -1 (ILLEGAL). 0 - 2 = -2 (ILLEGAL).
**NEVER** output a plan with negative CC.

**Surge**: costs 0, ADDS +1 → cc_after = cc_before + 1
**Rush**: costs 0, ADDS +2 → cc_after = cc_before + 2

**Example**: 2 CC → Play Surge → 2 - 0 + 1 = **3 CC** (not 2!)

---
## HARD CONSTRAINTS (Violations = Invalid Plan!)

1. **[NO TUSSLE] tag** → Card CANNOT be attacker for tussle/direct_attack
2. **STR = 0** → Card CANNOT be attacker (no damage dealt!)
3. **cc_after < 0** → ILLEGAL! You don't have enough CC! STOP PLANNING!
4. **Costs are FIXED** → Tussle/Direct always 2 CC (exceptions: Wizard -1, Raggy free)
5. **Target not in play** → ILLEGAL! Sleeped/hand cards can't be targeted!
6. **Direct attack with target_ids** → ILLEGAL! Direct attack has NO target!
7. **Direct attack when opponent has toys** → ILLEGAL! Use tussle instead!
8. **Tussle when opponent has NO toys** → ILLEGAL! Use direct_attack instead!
9. **Drop/Archer ability with 0 opponent toys** → ILLEGAL! No valid targets!
10. **Copy on opponent's toy** → ILLEGAL! Copy only YOUR toys!
11. **play_card from SLEEP ZONE** → ILLEGAL! Use Wake first to return card to hand.
12. **Wake without target** → ILLEGAL! Must specify target_id from Sleep Zone!

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

**Surge for Combo (Lethal)**:
```
Start: 4 CC, Hand: [Surge, Knight], Opponent: 1 toy (Umbruh)
1. play_card Surge (0 CC, +1 gain) → cc_after = 4+1 = 5
2. play_card Knight (1 CC) → cc_after = 5-1 = 4
3. tussle Knight→Umbruh (2 CC) → cc_after = 4-2 = 2 (Umbruh sleeped!)
4. direct_attack Knight (2 CC) → cc_after = 2-2 = 0 (Hit hand!)
Result: 5 CC used → 2 cards slept! (Without Surge, only 1 card slept)
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

---
## ZERO-ACTION AUDIT

If ending with CC >= 2, you MUST provide `residual_cc_justification`:
- "All my toys have [NO TUSSLE] tag" → Valid (cite card ID)
- "All my toys have 0 STR" → Valid (cite card ID)  
- "No valid targets remain" → Valid
- "All possible attacks are SUICIDE (Attacker dies, deals 0 damage)" → Valid (cite math)
- "I have CC and valid attacks but ended anyway" → INVALID PLAN!

---
## OUTPUT
Respond with TurnPlan JSON only. Use [ID: xxx] UUIDs for all card references.

**REASONING TEMPLATE (STRICT)**:
You MUST start your `plan_reasoning` with this exact format:
"Opp Board: [List ALL Toys]. Count: N. Strategy: ..."

**MANDATORY CHECKS**:
1. **Opp Board**: List EVERY opponent toy (e.g. "Archer, Umbruh").
2. **Count**: Total number of opponent toys.
3. **Direct Attack**: ONLY valid if Count is 0.
   - If Count > 0, you CANNOT direct attack.
   - **Archer counts as a toy!** You cannot direct attack past Archer.

**CRITICAL**: If your reasoning shows a step leads to negative CC, **DELETE THAT STEP**.
**CRITICAL**: If your reasoning shows a step is SUICIDE, **DELETE THAT STEP**.
**CRITICAL**: If Tussle target is missing, **DELETE THAT STEP**.
**WAKE WARNING**: Wake -> Play -> Use.
**NEVER** output an action sequence that contradicts your own math.

Example: "Opp Board: Archer, Umbruh. Count: 2. Strategy: Surge(+1), Knight tussle Umbruh. Cannot direct attack (Archer remains)."
Do NOT repeat analysis."""


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
    prompt = f"""You are a GGLTCG turn planner.
CC EFFICIENCY = CC spent / OPPONENT cards sleeped (your own cards don't count!)
Target: <=2.5 CC per opponent card slept.

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
