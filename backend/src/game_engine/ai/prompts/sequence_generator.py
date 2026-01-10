"""
Sequence Generator for AI V4 (Request 1).

Generates LEGAL action sequences with diversity. This is the first request
in the dual-request architecture:
- Temperature: 0.2 (deterministic, rule-following)
- Focus: Generate 5-10 LEGAL sequences as string descriptions
- Output: JSON with sequences as strings (avoids Gemini nesting limits)

The generator focuses purely on mechanics, leaving strategy to Request 2.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState


# JSON Schema for sequence generator output - FLAT structure to avoid nesting limits
# Sequences are strings like V3.0's sequences_considered
SEQUENCE_GENERATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "available_cc": {
            "type": "integer",
            "description": "Starting CC plus any CC modifiers from cards like Surge/Rush"
        },
        "can_direct_attack": {
            "type": "boolean",
            "description": "True ONLY if opponent has 0 toys in play"
        },
        "sequences": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 10,
            "description": "Legal action sequences as formatted strings"
        }
    },
    "required": ["available_cc", "can_direct_attack", "sequences"]
}


def generate_sequence_prompt(
    game_state: "GameState",
    player_id: str,
    game_engine=None
) -> str:
    """
    Generate the Request 1 prompt for sequence generation.
    
    This prompt is ~4k chars and focuses ONLY on generating legal sequences.
    NO strategy, NO examples - just mechanics.
    
    Args:
        game_state: Current GameState object
        player_id: ID of the AI player
        game_engine: Optional GameEngine for calculating effective stats
        
    Returns:
        Prompt string (~4k chars target)
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Get cards in each zone
    hand = player.hand
    in_play = player.in_play
    opp_in_play = opponent.in_play
    opp_sleep = opponent.sleep_zone

    def _format_effects(card) -> str:
        effects = getattr(card, "effect_definitions", None)
        if not effects:
            return "none"
        return ";".join(p.strip() for p in effects.split(";") if p.strip())

    def _get_effective_cost(card) -> int:
        if not game_engine or card.cost is None or card.cost < 0:
            return card.cost
        return game_engine.calculate_card_cost(card, player)

    def _format_card_line(card, zone: str) -> str:
        # Stable, computer-friendly fields:
        # id, name, effective cost, effective stats, relevant effects
        eff_cost = _get_effective_cost(card)
        effects = _format_effects(card)

        if card.is_toy():
            if zone == "in_play" and game_engine:
                spd = game_engine.get_card_stat(card, "speed")
                str_val = game_engine.get_card_stat(card, "strength")
                sta_val = game_engine.get_effective_stamina(card)
            else:
                spd = card.speed or 0
                str_val = card.strength or 0
                # In non-in-play zones, treat STA as the card's printed/reset stamina.
                sta_val = card.stamina or 0

            return (
                f"- [ID: {card.id}] {card.name} | type=Toy | cost={card.cost} | eff_cost={eff_cost} | "
                f"SPD/STR/STA={spd}/{str_val}/{sta_val} | effects={effects}"
            )

        return (
            f"- [ID: {card.id}] {card.name} | type=Action | cost={card.cost} | eff_cost={eff_cost} | "
            f"SPD/STR/STA=-/-/- | effects={effects}"
        )

    hand_text = "\n".join(_format_card_line(card, zone="hand") for card in hand) if hand else "(empty)"
    toys_text = "\n".join(_format_card_line(card, zone="in_play") for card in in_play) if in_play else "(none)"
    opp_toys_text = "\n".join(_format_card_line(card, zone="in_play") for card in opp_in_play) if opp_in_play else "(none)"

    # Sleep zone info for Wake targeting (include actionable info, keep compact)
    sleep_zone_text = "\n".join(_format_card_line(card, zone="sleep") for card in player.sleep_zone) if player.sleep_zone else "(empty)"
    
    # Direct attack availability
    can_direct = len(opp_in_play) == 0
    direct_msg = (
        "YES - opponent has 0 Toys In Play"
        if can_direct
        else f"NO - opponent has {len(opp_in_play)} Toys In Play"
    )
    
    # Calculate max CC (including potential Surge/Rush)
    cc_available = player.cc
    potential_cc = cc_available
    modifiers = []
    for card in hand:
        if card.name == "Surge":
            potential_cc += 1
            modifiers.append("Surge +1")
        elif card.name == "Rush":
            potential_cc += 2
            modifiers.append("Rush +2")
    
    cc_header = f"## CC: {cc_available}"
    if potential_cc > cc_available:
        cc_header += f" (Max potential: {potential_cc} via {', '.join(modifiers)})"

    prompt = f"""You are an expert GGLTCG player planning your turn.
Win condition: Put all opponent's cards into their Sleep Zone

Generate LEGAL action sequences that maximize your progress toward this goal.

{cc_header}

## CARD TYPES

| Type | Behavior |
|------|----------|
| **Toy** | Has Speed/Strength/Stamina stats. Stays In Play until sleeped. Can tussle. |
| **Action** | No stats. Effect resolves immediately, then card goes to your Sleep Zone. |

## ACTIONS & COSTS

| Action | Cost | Notes |
|--------|------|-------|
| **Play a card** | Card's printed cost | Pay CC, card enters In Play (Toy) or resolves (Action) |
| **Tussle** | 2 CC (default) | Your Toy vs opponent's Toy. Can be modified by card effects. |
| **Direct Attack** | 2 CC (default) | Only when opponent has no Toys In Play. Max 2 per turn. Random card from opponent's Hand → Sleep Zone. |
| **Activate** | 1 CC | Trigger an activated ability (e.g., Archer) |

## TUSSLE RESOLUTION

1. Compare Speed (active player's Toy gets +1 Speed bonus)
2. Higher Speed strikes first
3. Strike deals Strength as damage to opponent's Stamina
4. Stamina ≤ 0 → card is sleeped
5. If speeds tied, both strike simultaneously

Key rule: Toys can tussle the same turn they are played.

## CC EFFICIENCY
- Ending with 0-1 CC: Optimal (maximized usage)
- Ending with 2-3 CC: Acceptable if strategic
- Ending with 4+ CC: WASTEFUL (you cap at 7 CC next turn, losing gain)
- If you have 4+ CC remaining, look for more plays!

## RESOURCE PRIORITY
IF you have cards that **give +CC when played**, play them FIRST to maximize available CC!
Look for card descriptions like "(+1 CC when played)" or "(+2 CC when played)" in YOUR HAND below.

## LEGALITY CONSTRAINTS
1. direct_attack legality right now: {direct_msg}
2. STR > 0 required for tussle/direct_attack (STR=0 toys CANNOT attack)

## ZONE CHANGES & STATE CHANGES (CRITICAL!)
When a card moves between zones, all modifications reset (stat changes, damage, temporary effects). Card enters new zone with original printed values.

- Tussle that sleeps opponent's LAST Toy In Play → direct_attack becomes legal
- Wake moves card to HAND (must pay cost to play it again) → then it can tussle immediately
- Example: Surge→Knight→tussle(sleeps last toy)→direct_attack→end_turn

## CC MATH (CRITICAL!)
- Cards with (+X CC when played): ADD the bonus AFTER subtracting the cost
- Example: Start 4 CC → play card [cost 0, +1 CC] → 4 - 0 + 1 = 5 CC
- Example: Start 5 CC → play toy [cost 1] → 5 - 1 = 4 CC → tussle [cost 2] → 4 - 2 = 2 CC
- Action costs: tussle=2, direct_attack=2, activate=1
- **CRITICAL: Include CC bonuses in your "CC: X/Y spent" calculation!**

## EXAMPLES
Example 1 (with CC-gain card): Start 4 CC → play card [cost 0, +1 CC] → 5 CC → play toy [cost 1] → 4 CC → tussle [cost 2] → 2 CC → direct_attack [cost 2] → 0 CC | CC: 5/5 spent | Sleeps: 2
Example 2 (no attacks): Start 4 CC → play toy [cost 1] → 3 CC → play toy [cost 1] → 2 CC → end_turn | CC: 2/4 spent | Sleeps: 0
  (No tussles = no sleeps! Just played 2 toys.)

## YOUR HAND (Hand)
{hand_text}

## YOUR TOYS IN PLAY (In Play)
{toys_text}

## YOUR SLEEP ZONE (Sleep Zone)
{sleep_zone_text}

## OPPONENT HAND (Hand): {len(opponent.hand)} cards (hidden)

## OPPONENT TOYS IN PLAY (In Play)
{opp_toys_text}

## OPPONENT SLEEP ZONE (Sleep Zone): {len(opp_sleep)}/6 cards

## FORMAT
"[actions] -> end_turn | CC: X/Y spent | Sleeps: Z"
"Sleeps: Z" = opponent cards YOU put into opponent Sleep Zone this turn (tussle, direct_attack, effects)
Use card IDs from listings. Format: play NAME [ID], tussle ID->ID, direct_attack ID, activate ID->ID

## TASK
Generate 5-10 LEGAL sequences that spend as much CC as possible (aim for 0 CC left).
If you play cards that gain CC (e.g., Surge/Rush), your CC budget increases AFTER paying their cost.
1. Aggressive (maximize attacks)
2. Board-building (play multiple toys)
3. Balanced (mix playing + attacking)
4. If tussle clears board → add direct_attack!
5. Play CC-gain cards FIRST if available (look for "+X CC" in card descriptions)!

Verify math! Each sequence must not exceed available CC."""

    return prompt


def get_sequence_generator_temperature() -> float:
    """Return the temperature for sequence generation (Request 1)."""
    return 0.2


def parse_sequences_response(response_text: str, game_state=None) -> list[dict]:
    """
    Parse the JSON response from sequence generator.
    
    Converts string sequences to structured format for Request 2.
    
    Args:
        response_text: Raw JSON string from LLM
        game_state: Optional GameState for enriching UUID-only actions with card names
        
    Returns:
        List of sequence dictionaries with parsed info
    """
    import json
    import re
    import logging
    
    logger = logging.getLogger("game_engine.ai.sequence_generator")
    
    try:
        data = json.loads(response_text)
        raw_sequences = data.get("sequences", [])
        logger.debug(f"Parsing {len(raw_sequences)} raw sequences")
        
        sequences = []
        for i, seq_str in enumerate(raw_sequences):
            if not isinstance(seq_str, str):
                logger.warning(f"Sequence {i} is not a string: {type(seq_str)}")
                continue
                
            # Parse the string format: "actions | CC: X/Y spent | Sleeps: Z"
            parts = seq_str.split("|")
            actions_part = parts[0].strip() if len(parts) > 0 else ""
            cc_part = parts[1].strip() if len(parts) > 1 else ""
            sleeps_part = parts[2].strip() if len(parts) > 2 else ""
            
            # Extract CC spent
            cc_match = re.search(r'(\d+)/(\d+)', cc_part)
            cc_spent = int(cc_match.group(1)) if cc_match else 0
            cc_available = int(cc_match.group(2)) if cc_match else 0
            
            # Extract sleeps
            sleeps_match = re.search(r'(\d+)', sleeps_part)
            cards_slept = int(sleeps_match.group(1)) if sleeps_match else 0
            
            # Parse actions - need to handle both " -> " (correct) and "->" (no spaces)
            # while preserving "->" in tussle/activate targets like "tussle Knight->Enemy"
            # 
            # Strategy: First split by " -> " (with spaces), then re-split any parts
            # that still contain "->" followed by an action keyword.
            initial_parts = [a.strip() for a in actions_part.split(" -> ")]
            
            # Re-split any parts that have "->" followed by action keywords
            # This handles mixed formats like "play Knight->tussle Knight->Enemy"
            action_strs = []
            for part in initial_parts:
                if "->" in part:
                    # Split on "->" that comes before an action keyword
                    sub_parts = re.split(r'->(?=\s*(?:play|tussle|direct_attack|activate|end_turn)\b)', part)
                    action_strs.extend([p.strip() for p in sub_parts if p.strip()])
                else:
                    action_strs.append(part)
            
            actions = []
            for action_str in action_strs:
                action = _parse_action_string(action_str)
                if action:
                    actions.append(action)
                else:
                    logger.debug(f"Failed to parse action: {action_str!r}")
            
            if not actions:
                logger.warning(f"Sequence {i} has no valid actions: {seq_str[:80]}...")
                continue
            
            # Enrich actions with card names if we have game_state
            if game_state:
                for action in actions:
                    # If action has card_id but no card_name, look it up
                    if action.get("card_id") and not action.get("card_name"):
                        card = game_state.find_card_by_id(action["card_id"])
                        if card:
                            action["card_name"] = card.name
                    
                    # Same for target_id
                    if action.get("target_id") and not action.get("target_name"):
                        target = game_state.find_card_by_id(action["target_id"])
                        if target:
                            action["target_name"] = target.name
            
            # Determine tactical label
            attack_count = sum(1 for a in actions if a.get("action_type") in ["tussle", "direct_attack"])
            play_count = sum(1 for a in actions if a.get("action_type") == "play_card")
            has_resource = any(a.get("card_name") in ["Surge", "Rush"] for a in actions)
            
            if cards_slept >= 6:
                label = "[Lethal]"
            elif attack_count >= 2:
                label = "[Aggressive]"
            elif has_resource and attack_count == 0:
                label = "[Resource]"
            elif play_count >= 2 and attack_count == 0:
                label = "[Board Setup]"
            elif cc_spent <= 2:
                label = "[Conservative]"
            else:
                label = "[Balanced]"
            
            sequences.append({
                "raw_string": seq_str,
                "actions": actions,
                "total_cc_spent": cc_spent,
                "cc_available": cc_available,
                "cards_slept": cards_slept,
                "tactical_label": label,
            })
        
        logger.debug(f"Successfully parsed {len(sequences)} sequences")
        return sequences
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
        return []


def _parse_action_string(action_str: str) -> dict | None:
    """
    Parse a single action string into structured format.
    
    Supports both ID-based format (V4) and name-based format (legacy):
    - ID-based: "play Knight [k1]", "tussle b1->w1", "direct_attack ar1"
    - Name-based: "play Knight", "tussle Beary->Wizard"
    
    Always extracts card_id and target_id when IDs are present.
    Falls back to card_name and target_name when IDs are not found.
    """
    import re
    
    action_str = action_str.strip()
    
    if action_str == "end_turn":
        return {"action_type": "end_turn", "card_name": None, "card_id": None, "target_name": None, "target_id": None, "cc_cost": 0}
    
    # UUID pattern: 36 chars with hyphens (e.g., bd9629b1-0671-4024-8252-515e9f49f948)
    uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
    
    # Short ID pattern: alphanumeric with underscores (NO hyphens to avoid matching ->)
    # e.g., "k1", "ar1", "wa1", "p1_knight"
    short_id_pattern = r'[a-zA-Z0-9_]+'
    
    # Pattern for card names: word characters, optionally followed by space and more words
    # Starts with capital letter to distinguish from short IDs
    card_name_pattern = r'([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)?)'
    
    # -------------------------------------------------------------------------
    # PLAY CARD - matches:
    #   "play Knight [k1]"
    #   "play Knight [k1] [target: xyz]"  
    #   "play Wake [wa1] [target: k2]"
    #   "play Knight" (legacy)
    #   "play Knight [target: abc]" (legacy with target)
    # -------------------------------------------------------------------------
    play_match = re.match(
        rf'play\s+{card_name_pattern}'
        rf'(?:\s*\[({short_id_pattern})\])?'  # Optional ID in brackets
        rf'(?:\s*\[target:\s*([^\]]+)\])?',   # Optional target
        action_str, re.I
    )
    if play_match:
        card_name = play_match.group(1)
        card_id = play_match.group(2)  # May be None
        target_raw = play_match.group(3).strip() if play_match.group(3) else None
        
        # Target could be an ID or a name
        target_id = None
        target_name = None
        if target_raw:
            # Check if target looks like an ID (UUID or short alphanumeric without uppercase start)
            if re.fullmatch(uuid_pattern, target_raw) or (len(target_raw) <= 10 and re.fullmatch(r'[a-z0-9_]+', target_raw)):
                target_id = target_raw
            else:
                target_name = target_raw
        
        return {
            "action_type": "play_card",
            "card_name": card_name,
            "card_id": card_id,
            "target_name": target_name,
            "target_id": target_id,
            "cc_cost": 0,  # Card cost tracked in sequence's total_cc_spent
        }
    
    # For tussle/activate/direct_attack, we need ID patterns that don't include arrow
    # Short ID pattern: lowercase alphanumeric with underscores (e.g., "k1", "ar1")
    # UUID pattern: full UUID format with hyphens
    short_id_pat = r'[a-z0-9_]+'  # lowercase only, no hyphens
    full_uuid_pat = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'  # UUID format
    
    # -------------------------------------------------------------------------
    # TUSSLE - matches:
    #   "tussle b1->w1" (ID-based, preferred)
    #   "tussle uuid->uuid" (UUID-based)
    #   "tussle Beary->Wizard" (name-based, legacy)
    # -------------------------------------------------------------------------
    # Try name-based format FIRST (names start with uppercase)
    # This ensures "tussle Knight->Beary" is parsed as names, not IDs
    tussle_name_match = re.match(
        rf'tussle\s+{card_name_pattern}\s*->\s*{card_name_pattern}',
        action_str
    )  # Note: NO re.I flag - names must have capital letters
    if tussle_name_match:
        return {
            "action_type": "tussle",
            "card_name": tussle_name_match.group(1),
            "card_id": None,
            "target_name": tussle_name_match.group(2),
            "target_id": None,
            "cc_cost": 2,
        }
    
    # Try UUID format (with hyphens)
    tussle_uuid_match = re.match(
        rf'tussle\s+({full_uuid_pat})\s*->\s*({full_uuid_pat})',
        action_str, re.I
    )
    if tussle_uuid_match:
        return {
            "action_type": "tussle",
            "card_name": None,
            "card_id": tussle_uuid_match.group(1),
            "target_name": None,
            "target_id": tussle_uuid_match.group(2),
            "cc_cost": 2,
        }
    
    # Try short ID format (lowercase alphanumeric only)
    tussle_id_match = re.match(
        rf'tussle\s+({short_id_pat})\s*->\s*({short_id_pat})',
        action_str
    )  # Note: NO re.I flag - IDs must be lowercase
    if tussle_id_match:
        return {
            "action_type": "tussle",
            "card_name": None,
            "card_id": tussle_id_match.group(1),
            "target_name": None,
            "target_id": tussle_id_match.group(2),
            "cc_cost": 2,
        }
    
    # -------------------------------------------------------------------------
    # DIRECT ATTACK - matches:
    #   "direct_attack ar1" (ID-based)
    #   "direct_attack Archer" (name-based, legacy)
    # -------------------------------------------------------------------------
    # Try name-based first (starts with uppercase)
    da_name_match = re.match(rf'direct_attack\s+{card_name_pattern}', action_str)
    if da_name_match:
        return {
            "action_type": "direct_attack",
            "card_name": da_name_match.group(1),
            "card_id": None,
            "target_name": None,
            "target_id": None,
            "cc_cost": 2,
        }
    
    # Try ID-based (lowercase alphanumeric or UUID)
    da_uuid_match = re.match(rf'direct_attack\s+({full_uuid_pat})', action_str, re.I)
    if da_uuid_match:
        return {
            "action_type": "direct_attack",
            "card_name": None,
            "card_id": da_uuid_match.group(1),
            "target_name": None,
            "target_id": None,
            "cc_cost": 2,
        }
    
    da_id_match = re.match(rf'direct_attack\s+({short_id_pat})', action_str)
    if da_id_match:
        return {
            "action_type": "direct_attack",
            "card_name": None,
            "card_id": da_id_match.group(1),
            "target_name": None,
            "target_id": None,
            "cc_cost": 2,
        }
    
    # -------------------------------------------------------------------------
    # ACTIVATE ABILITY - matches:
    #   "activate ar1->w1" (ID-based)
    #   "activate Archer->Wizard" (name-based, legacy)
    # -------------------------------------------------------------------------
    # Try name-based format first - names start with uppercase
    activate_name_match = re.match(
        rf'activate\s+{card_name_pattern}\s*->\s*{card_name_pattern}',
        action_str
    )  # No re.I - names must have capitals
    if activate_name_match:
        return {
            "action_type": "activate_ability",
            "card_name": activate_name_match.group(1),
            "card_id": None,
            "target_name": activate_name_match.group(2),
            "target_id": None,
            "cc_cost": 1,
        }
    
    # Try UUID format
    activate_uuid_match = re.match(
        rf'activate\s+({full_uuid_pat})\s*->\s*({full_uuid_pat})',
        action_str, re.I
    )
    if activate_uuid_match:
        return {
            "action_type": "activate_ability",
            "card_name": None,
            "card_id": activate_uuid_match.group(1),
            "target_name": None,
            "target_id": activate_uuid_match.group(2),
            "cc_cost": 1,
        }
    
    # Try short ID format (lowercase only)
    activate_id_match = re.match(
        rf'activate\s+({short_id_pat})\s*->\s*({short_id_pat})',
        action_str
    )  # No re.I - IDs must be lowercase
    if activate_id_match:
        return {
            "action_type": "activate_ability",
            "card_name": None,
            "card_id": activate_id_match.group(1),
            "target_name": None,
            "target_id": activate_id_match.group(2),
            "cc_cost": 1,
        }
    
    return None


def add_tactical_labels(sequences: list[dict]) -> list[dict]:
    """
    Add tactical labels to validated sequences.
    
    Labels help Request 2 understand what each sequence accomplishes:
    - [Lethal]: Can win this turn (6+ cards slept)
    - [Aggressive]: Multiple attacks
    - [Resource]: Plays Surge/Rush without attacking
    - [Board Setup]: Plays multiple toys without attacking
    - [Conservative]: Minimal CC spent
    - [Balanced]: Everything else
    """
    for seq in sequences:
        # Skip if already labeled
        if "tactical_label" in seq:
            continue
            
        actions = seq.get("actions", [])
        cards_slept = seq.get("cards_slept", 0)
        cc_spent = seq.get("total_cc_spent", 0)
        
        # Count action types
        attack_count = sum(1 for a in actions if a.get("action_type") in ["tussle", "direct_attack"])
        play_count = sum(1 for a in actions if a.get("action_type") == "play_card")
        has_resource = any(a.get("card_name") in ["Surge", "Rush"] for a in actions)
        
        # Determine label
        if cards_slept >= 6:
            seq["tactical_label"] = "[Lethal]"
        elif attack_count >= 2:
            seq["tactical_label"] = "[Aggressive Removal]"
        elif has_resource and attack_count == 0:
            seq["tactical_label"] = "[Resource Building]"
        elif play_count >= 2 and attack_count == 0:
            seq["tactical_label"] = "[Board Setup]"
        elif cc_spent <= 2:
            seq["tactical_label"] = "[Conservative]"
        else:
            seq["tactical_label"] = "[Balanced]"
    
    return sequences


def format_sequence_for_display(seq: dict, index: int) -> str:
    """
    Format a sequence for display in Request 2 prompt.
    
    Args:
        seq: Sequence dictionary
        index: 0-based sequence index
        
    Returns:
        Formatted string showing sequence summary
    """
    label = seq.get("tactical_label", "[Unknown]")
    raw = seq.get("raw_string", "")
    cc_spent = seq.get("total_cc_spent", 0)
    cc_avail = seq.get("cc_available", 0)
    cards_slept = seq.get("cards_slept", 0)
    
    return f"""<sequence index="{index}" label="{label}">
<description>{raw}</description>
<cc_spent>{cc_spent}/{cc_avail}</cc_spent>
<cards_slept>{cards_slept}</cards_slept>
</sequence>"""