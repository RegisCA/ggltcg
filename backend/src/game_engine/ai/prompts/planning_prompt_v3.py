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

from .card_loader import format_card_guidance_compact, generate_threat_priorities


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


# =============================================================================
# Sequence Planning Rules (Multi-Step Logic)
# =============================================================================

SEQUENCE_PLANNING = """# SEQUENCE PLANNING (Validator handles CC/combat math)

Framework:
1. Count opponent toys in play. Direct attack is legal only at 0 toys unless a card effect says otherwise.
2. Compute total budget: starting CC plus cards that add CC when played.
3. Spend setup cards first: Surge/Rush/HLK before other actions, Wake before replaying a slept card, buffs before combat.
4. Prefer lines that sleep cards now instead of only developing board.

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

CC economy: Unspent CC carries over (max 7, excess lost). You gain 4 CC per turn (2 on turn 1).
If you can remove a threat or deal direct damage now, do it — live opponent toys grow more dangerous each turn.
Only bank CC if you have a concrete plan that requires more CC next turn than you'd otherwise have."""

def _generate_context_notes(game_state, player_id: str) -> str:
    """
    Generate turn-specific and board-specific warnings.
    Shown on any turn where relevant cards are in hand with no valid targets,
    or on turns with special play restrictions.
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    hand_names = {c.name for c in player.hand}
    total_in_play = len(player.in_play) + len(opponent.in_play)
    opp_in_play_count = len(opponent.in_play)

    notes = []

    if game_state.turn_number == 1:
        notes.append("P1 turn 1: 2 CC only. Direct attack is legal (opponent has 0 toys), but requires a toy IN PLAY.")
        notes.append("Surge turns 2 CC into 3: play Surge → play 1-cost toy → direct_attack with that toy.")
        if "Rush" in hand_names:
            notes.append("⛔ RUSH IS BANNED ON TURN 1. Rush cannot be played on the first turn of the game. Omit it from every sequence.")
    elif game_state.turn_number == 2:
        notes.append("P2 first turn (game turn 2): opponent likely has toys in play. Priority: remove threats before developing board.")

    # Board-dependent card warnings (apply any turn)
    if "Clean" in hand_names and total_in_play == 0:
        notes.append("⛔ CLEAN IS USELESS NOW: No toys in play on either side. Clean would sleep nothing and waste 3 CC. Do NOT include Clean.")
    if "Twist" in hand_names and opp_in_play_count == 0:
        notes.append("⛔ TWIST HAS NO TARGET: Opponent has no toys in play. Twist requires an opponent toy to steal. Do NOT include Twist.")
    if "Drop" in hand_names and opp_in_play_count == 0:
        notes.append("⛔ DROP HAS NO TARGET: Opponent has no toys in play. Drop requires an opponent toy to sleep. Do NOT include Drop.")

    if not notes:
        return ""
    return "\nTurn context:\n" + "\n".join(f"- {n}" for n in notes) + "\n"



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
- direct_attack costs exactly 2 CC (NOT 1); has no target_ids; card_id MUST be a toy from **Your Toys In Play** with STR > 0 — action cards like Rush/Surge/HLK do NOT go into play as toys and CANNOT perform a direct attack; you need a toy already in play OR play a toy card first
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
    
    # Generate dynamic threat priorities (only lists cards actually in this game)
    threat_priorities = generate_threat_priorities(game_state, player_id)
    
    # Load card-specific guidance (traps + reminders for cards in current game only)
    card_guidance = format_card_guidance_compact(game_state, player_id)

    # Dynamic context notes: turn restrictions + board-dependent action warnings
    turn_1_section = _generate_context_notes(game_state, player_id)
    
    prompt = f"""You are a GGLTCG turn planner.

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

{threat_priorities}

{card_guidance}

{SEQUENCE_PLANNING}
{turn_1_section}
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
