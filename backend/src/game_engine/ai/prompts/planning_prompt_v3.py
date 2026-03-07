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

Zones: HAND (play from) | IN PLAY (attack/activate) | SLEEP (locked until recovered)
Turn economy: +4 CC/turn (max 7) | Turn 1 P1 starts at 2 CC
Win: sleep all 6 opponent cards

Action costs:
- play_card: printed card cost
- tussle: 2 CC, requires STR > 0
- direct_attack: 2 CC, requires STR > 0 and 0 opponent toys unless a card effect bypasses it
- activate_ability: usually 1 CC unless card text says otherwise
- pass/end_turn: 0 CC

Combat:
- attacker gets +1 SPD
- faster toy strikes first; 0 STA sleeps immediately and cannot strike back
- tied SPD means simultaneous strikes
- equal-stat mirrors favor the attacker because of the +1 SPD bonus
- Knight auto-wins tussles on your turn

Key rules:
- play only from HAND
- Wake returns a slept card to HAND; you still pay to replay it
- cards that change zones reset damage and temporary modifiers
- 0 STR toys cannot tussle or direct_attack, but they still block direct attacks
- activated abilities can be used multiple times per turn if you can pay"""


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

Framework:
1. Count opponent toys in play. Direct attack is legal only at 0 toys unless a card effect says otherwise.
2. Compute total budget: starting CC plus cards that add CC when played.
3. Spend setup cards first: Surge/Rush/HLK before other actions, Wake before replaying a slept card, buffs before combat.
4. Prefer lines that sleep cards now instead of only developing board.

Turn 1 guidance:
- P1 turn 1 starts at 2 CC. If opponent has 0 toys, direct attack is already available.
- Surge often turns 2 CC into a 3 CC line like Surge -> 1-cost toy -> direct_attack.
- P2 turn 1 usually must remove blockers first because opponent has toys in play.

Priority order:
1. Lethal if possible.
2. Remove high-value threats.
3. Use efficient abilities or favorable tussles.
4. Direct attack once blockers are gone.
5. Add board only when no better sleep line exists.

Checks before finalizing:
- Use correct costs: tussle=2, direct_attack=2, activate usually 1.
- Never let cc_after go negative.
- Recount opponent toys after each sleep effect.
- Do not play from sleep without Wake first.
- Do not target cards that already slept.

Card-specific reminders:
- Knight auto-wins tussles on your turn.
- Archer can remove low-STA toys efficiently even though it cannot attack.
- Paper Plane may bypass blockers for direct attacks.
- Wizard, Raggy, and Gibbers can modify action costs; respect the board state.

CC economy note: Unspent CC carries over to your next turn (max 7, excess lost).
You gain 4 CC per turn (2 on turn 1), so banking more than ~2 CC rarely pays off
because you'll likely hit the cap anyway. If you can remove a threat or deal direct
damage now, do it — live opponent toys grow more dangerous each turn.
Only bank CC if you have a concrete plan that requires more CC next turn than you'd
otherwise have (e.g., a 5-CC play when you'll have exactly 5 next turn).

Efficiency target: aim for ≤2.5 CC per opponent card slept when practical."""


# =============================================================================
# Output Format
# =============================================================================

OUTPUT_FORMAT = """# OUTPUT FORMAT

Return valid JSON only.

Required fields:
- plan_reasoning: brief summary of opponent board and chosen line
- action_sequence: ordered actions, one action per object
- expected_cards_slept
- residual_cc_justification when ending with CC >= 2

Action rules:
- Use [ID: uuid] values for card_id and target_ids
- cc_start: set this to the exact "Your CC:" value shown in the game state above
- cc_after per action: cc_before_action - cc_cost + cc_gained (Surge +1, Rush +2, HLK +1); must stay >= 0; cc_before_action for the first step equals cc_start, and for each subsequent step it equals the previous step's cc_after
- direct_attack costs exactly 2 CC (NOT 1); has no target_ids
- tussle costs exactly 2 CC; card_id MUST come from **Your Toys In Play** (toys in your hand cannot tussle — play them first); target_ids[0] MUST come from **Opponent's Toys In Play** (never use your own card's ID as a tussle target, even if both players have a card with the same name — they have different IDs)
- play_card: card_id comes from Your Hand; do NOT reuse that card's ID as a tussle target in the same plan
- do not emit a sequence you know is invalid"""


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
