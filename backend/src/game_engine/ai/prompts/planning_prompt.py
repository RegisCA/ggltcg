"""
Turn Planning Prompt for AI v3.

This module contains the 4-phase turn planning framework prompt that guides
the AI to create a complete turn plan with CC budgeting and threat prioritization.

Based on: GGLTCG Turn Planning Strategy Guide
"""

from typing import List, Optional
from .card_library import CARD_EFFECTS_LIBRARY


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
- Paper Plane: Can direct attack your hand even with defenders

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
- Tussle: 2 CC (or 1 CC with Wizard in play)
- Direct Attack: 2 CC (max 2 per turn)
- Archer ability: 1 CC per stamina removed

**Action Cards:**
- Surge: 0 CC (gain 1 CC)
- Rush: 1 CC (gain 2 CC, net +1, not on turn 1)
- Drop: 1 CC (sleep 1 target)
- Clean: 2 CC (sleep ALL toys)
- Twist: 3 CC (steal 1 opponent toy)
- Wake: 1 CC (recover 1 from sleep zone)
- Sun: 2 CC (recover up to 2 from sleep zone)
- Toynado: 2 CC (return all in-play to hands)
- Jumpscare: 1 CC (return 1 to hand, no sleep trigger)
- Copy: 1 CC (copy your own toy)
- VeryVeryAppleJuice: 1 CC (+1/+1/+1 this turn)
- That was fun: 0 CC (recover action from sleep zone)

**Toy Costs (varies by card):**
- 0 CC: Archer
- 1 CC: Ka, Knight, Wizard, Umbruh, Paper Plane, Raggy, Drum, Violin, Gibbers, Hind Leg Kicker, Monster
- 2 CC: Belchaletta, Beary, Demideca
- 3 CC: Sock Sorcerer
- 4 CC: Dream (reduces by 1 per card in your sleep zone)
- Alternative: Ballaber (2 CC or sleep one of your cards)

**CC Modifiers:**
- Gibbers in opponent's play: Your cards cost +1 CC
- Belchaletta at turn start: +2 CC
- Hind Leg Kicker when you play a card: +1 CC
- Umbruh when sleeped: +1 CC
"""


# =============================================================================
# Main Planning Prompt
# =============================================================================

PLANNING_SYSTEM_PROMPT = """You are an expert GGLTCG strategist. Your task is to create a complete turn plan that maximizes CC efficiency.

## Core Winning Principle
**Minimize the average CC cost of sleeping opponent cards.**
Target: ≤ 2.5 CC per opponent card slept
Every decision should be evaluated against CC efficiency and board control.

## Critical Rules
- You WIN when ALL opponent cards are in their Sleep Zone
- Maximum CC: 7 (cannot exceed)
- Standard turn CC gain: 4 CC (2 CC on turn 1)
- Maximum 2 direct attacks per turn
- Direct attacks only possible when opponent has NO toys in play (or you have Paper Plane)

## Output Format
Respond with a JSON object following the TurnPlan schema exactly.
All card IDs must be extracted from [ID: xxx] brackets - use the UUID, never card names.

{threat_priorities}

{cc_cost_reference}
"""


PLANNING_FRAMEWORK_PROMPT = """## Turn Planning Framework

Execute these 4 phases to create your turn plan:

### Phase 1: Threat Assessment
Evaluate all opponent cards in play:
1. **Immediate Combat Threats**: Which opponent cards can tussle and win against yours?
2. **Effect-Based Threats**: What continuous effects are active? (immunity, cost modifiers, stat boosts)
3. **Prioritize Threats**: Rank from CRITICAL to LOW using the threat priority reference

### Phase 2: Resource Inventory
Survey all your available tools:
1. **Your CC**: Starting CC and any potential CC generation (Surge, Rush, Belchaletta, Umbruh, Hind Leg Kicker)
2. **Action Cards in Hand**: What removal/control options do you have?
3. **Toys in Play**: What can they tussle? What abilities do they have? (Archer stamina removal)
4. **Toys in Hand**: Offensive capabilities, combo potential, alternative costs

### Phase 3: Calculate Action Sequences
For each threat, calculate the TOP 3-5 most promising removal paths:
- **Tussle path**: Play cost + tussle cost (usually 2 CC, or 1 with Wizard)
- **Archer path**: 0 CC to play + 1 CC per stamina to remove
- **Action card path**: Drop (1 CC), Clean (2 CC, all toys), etc.
- **Combo paths**: Multiple cards working together (e.g., VeryVeryAppleJuice + tussle)

**Limit sequences_considered to 3-5 distinct options** - don't list every permutation.

**For each sequence, track:**
- Total CC cost
- Cards slept
- CC efficiency (total CC ÷ cards slept)
- Board state after sequence

### Phase 4: Select Best Sequence & Plan Offensive
1. **Compare sequences**: Select the one with best CC efficiency that removes highest-priority threats
2. **Use remaining CC**: Direct attacks if board is clear, or setup for next turn
3. **Create action sequence**: Ordered list of actions with CC tracking

## Decision Criteria (in priority order)
1. Can you WIN this turn? (sleep opponent's last cards) → DO IT
2. Can you remove CRITICAL threats efficiently? → Remove them
3. Can you remove HIGH threats with good CC efficiency? → Remove them
4. Can you make favorable trades? (spend less CC than opponent would to recover)
5. Can you set up for next turn? (CC generation, positioning)

## Example Sequence Calculation

**Scenario**: 4 CC available, opponent has Knight (4/4/3) and Paper Plane (2/2/1)

**Option A - Tussle Path**:
- Play my Knight (1 CC) → 3 CC left
- Tussle opponent Knight (2 CC) → 1 CC left
- Cannot remove Paper Plane (need 2 CC for tussle)
- Result: 3 CC spent, 1 card slept = 3.0 CC per card ❌

**Option B - Archer Path**:
- Play Archer (0 CC) → 4 CC left
- Remove Paper Plane 1 stamina (1 CC) → 3 CC left, Paper Plane SLEPT
- Remove Knight 3 stamina (3 CC) → 0 CC left, Knight SLEPT
- Result: 4 CC spent, 2 cards slept = 2.0 CC per card ✓

**Select**: Option B (better CC efficiency)

## IMPORTANT REMINDERS
- Always track CC remaining after EACH action
- Account for CC generation during the sequence (Surge, Umbruh triggers)
- Plan must end with "end_turn" action
- If you cannot do anything useful, plan should just be "end_turn"
- Use card IDs (from [ID: xxx]) for all card references, not names
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

def format_card_for_planning(card, game_engine=None, is_opponent: bool = False) -> str:
    """
    Format a single card with full details for planning.
    
    Args:
        card: Card object
        game_engine: Optional GameEngine for effective stats
        is_opponent: Whether this is an opponent's card
        
    Returns:
        Formatted string with card ID, name, stats, and effect
    """
    card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
    effect = card_info.get("effect", "Unknown effect")
    threat = card_info.get("threat_level", "UNKNOWN")
    
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
        
        if is_opponent:
            return f"[ID: {card.id}] {card.name} {stats_str} - {effect} | THREAT: {threat}"
        else:
            return f"[ID: {card.id}] {card.name} {stats_str} - {effect}"
    else:
        # Action card
        return f"[ID: {card.id}] {card.name} (cost {card.cost}) - {effect}"


def format_hand_for_planning(hand: list, game_engine=None) -> str:
    """Format all cards in hand for planning prompt."""
    if not hand:
        return "EMPTY"
    
    lines = []
    for card in hand:
        lines.append(f"  - {format_card_for_planning(card, game_engine, is_opponent=False)}")
    return "\n".join(lines)


def format_in_play_for_planning(in_play: list, game_engine=None, is_opponent: bool = False) -> str:
    """Format all cards in play for planning prompt."""
    if not in_play:
        return "NONE"
    
    lines = []
    for card in in_play:
        lines.append(f"  - {format_card_for_planning(card, game_engine, is_opponent=is_opponent)}")
    return "\n".join(lines)


def format_sleep_zone_for_planning(sleep_zone: list) -> str:
    """Format sleep zone cards (just names and IDs)."""
    if not sleep_zone:
        return "EMPTY"
    
    lines = []
    for card in sleep_zone:
        lines.append(f"  - [ID: {card.id}] {card.name}")
    return "\n".join(lines)
