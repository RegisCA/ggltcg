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
    from .planning_prompt_v3 import format_hand_for_planning_v3, format_in_play_for_planning_v3
    
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Get cards in each zone
    hand = player.hand
    in_play = player.in_play
    opp_in_play = opponent.in_play
    opp_sleep = opponent.sleep_zone
    
    # Format cards compactly
    hand_entries = []
    for card in hand:
        cc_mod = ""
        if card.name == "Surge":
            cc_mod = " (+1 CC when played)"
        elif card.name == "Rush":
            cc_mod = " (+2 CC when played)"
        
        target_req = ""
        if card.name == "Wake":
            target_req = f" [REQUIRES: my sleep zone card as target, my sleep={len(player.sleep_zone)} cards]"
        elif card.name == "Drop":
            target_req = f" [REQUIRES: opp in_play card as target, opp_toys={len(opp_in_play)}]"
        elif card.name == "Clean":
            target_req = " [TARGETS: opp card]"
        elif card.name == "Twist":
            target_req = " [TARGETS: opp card]"
        
        # Action cards don't have stats
        if card.is_action():
            entry = f"- {card.name} (id={card.id}, cost={card.cost}{cc_mod}, ACTION){target_req}"
        else:
            # Toys have stats - get effective values
            str_val = game_engine.get_card_stat(card, "strength") if game_engine else (card.strength or 0)
            sta_val = game_engine.get_effective_stamina(card) if game_engine else (card.stamina or 0)
            entry = f"- {card.name} (id={card.id}, cost={card.cost}{cc_mod}, STR={str_val}, HP={sta_val}){target_req}"
        hand_entries.append(entry)
    hand_text = "\n".join(hand_entries) if hand_entries else "(empty)"
    
    toy_entries = []
    for card in in_play:
        # Toys always have stats - get effective values
        s = game_engine.get_card_stat(card, "strength") if game_engine else (card.strength or 0)
        sta_val = game_engine.get_effective_stamina(card) if game_engine else (card.stamina or 0)
        
        can_attack = "CAN attack" if s and s > 0 else "CANNOT attack (STR=0)"
        special = ""
        if card.name == "Archer":
            special = " [has activate: 1 CC deals 1 damage to any target]"
        elif card.name == "Knight":
            special = " [auto-wins tussles on your turn]"
        entry = f"- {card.name} (id={card.id}, STR={s}, HP={sta_val}, {can_attack}){special}"
        toy_entries.append(entry)
    toys_text = "\n".join(toy_entries) if toy_entries else "(no toys - must play from hand first to attack)"
    
    opp_entries = []
    for card in opp_in_play:
        # Opponent toys always have stats - get effective values
        str_val = game_engine.get_card_stat(card, "strength") if game_engine else (card.strength or 0)
        sta_val = game_engine.get_effective_stamina(card) if game_engine else (card.stamina or 0)
        
        entry = f"- {card.name} (id={card.id}, STR={str_val}, HP={sta_val})"
        opp_entries.append(entry)
    opp_toys_text = "\n".join(opp_entries) if opp_entries else "(EMPTY - direct_attack allowed!)"
    
    # Sleep zone info for Wake targeting
    sleep_entries = []
    for card in player.sleep_zone:
        sleep_entries.append(f"- {card.name} (id={card.id})")
    sleep_zone_text = "\n".join(sleep_entries) if sleep_entries else "(empty)"
    
    # Direct attack availability
    can_direct = len(opp_in_play) == 0
    direct_msg = "YES - opponent has 0 toys" if can_direct else f"NO - opponent has {len(opp_in_play)} toys"
    
    # Calculate max CC (including potential Surge/Rush)
    cc_available = player.cc
    potential_cc = cc_available
    for card in hand:
        if card.name == "Surge":
            potential_cc += 1
        elif card.name == "Rush":
            potential_cc += 2
    
    prompt = f"""You are a sequence generator for a turn-based card game. Generate LEGAL action sequences.

## CC MATH (CRITICAL - read carefully!)
Your CC: {cc_available}
If you play Surge first: {cc_available} - 0 + 1 = {cc_available + 1} CC available after
If you play Rush first: {cc_available} - 0 + 2 = {cc_available + 2} CC available after

## ACTION COSTS
- play_card: costs the card's CC_cost (shown after each card)
- tussle: costs 2 CC (attack opponent toy with your toy)  
- direct_attack: costs 2 CC (attack opponent directly - ONLY if opponent has 0 toys!)
- activate_ability: costs 1 CC (Archer's ability)
- end_turn: costs 0 CC

## KEY CONSTRAINTS
1. direct_attack allowed? {direct_msg}
2. To tussle or direct_attack, your toy must have STR > 0
3. Wake requires targeting a card in YOUR sleep zone (you have {len(player.sleep_zone)} cards there)
4. Drop requires targeting a card in OPPONENT's in_play (they have {len(opp_in_play)} toys)
5. Knight always wins tussles on your turn (regardless of STR/HP)

## YOUR HAND
{hand_text}

## YOUR TOYS IN PLAY  
{toys_text}

## YOUR SLEEP ZONE (for Wake targeting)
{sleep_zone_text}

## OPPONENT'S TOYS
{opp_toys_text}

## OPPONENT'S SLEPT CARDS: {len(opp_sleep)}/6

## OUTPUT FORMAT
Each sequence must be a string in this exact format:
"[Action1] -> [Action2] -> ... -> end_turn | CC: X/Y spent | Sleeps: Z"

Where:
- Each action is: "play CARDNAME" or "tussle ATTACKER->TARGET" or "direct_attack ATTACKER" or "activate CARDNAME->TARGET" or "end_turn"
- X = total CC spent this sequence
- Y = CC available at start of sequence (accounting for Surge/Rush played first)
- Z = number of opponent cards that would sleep this turn

## EXAMPLES OF CORRECT FORMAT
With 4 CC, Surge+Knight in hand, 1 toy (Beary STR=2), opponent has 1 toy (Wizard HP=2):
- "play Surge -> play Knight -> tussle Beary->Wizard -> end_turn | CC: 3/5 spent | Sleeps: 1"
  (Surge costs 0, gives +1 CC so 5 total. Knight costs 1, tussle costs 2. Total: 0+1+2=3)

With 3 CC, Wake in hand, 1 toy (Archer STR=1), no opp toys, Knight in sleep zone:
- "play Wake [target: Knight] -> direct_attack Archer -> end_turn | CC: 3/3 spent | Sleeps: 1"
  (Wake costs 1, direct_attack costs 2. Total: 1+2=3)

## TASK
Generate 5-10 LEGAL sequences varying in approach:
1. At least one aggressive sequence (maximize attacks)
2. At least one board-building sequence (play toys without attacking)  
3. At least one conservative sequence (spend minimal CC)
4. If Surge/Rush in hand, include sequence that plays it first

Important: Verify your math! Each sequence must not exceed available CC."""

    return prompt


def get_sequence_generator_temperature() -> float:
    """Return the temperature for sequence generation (Request 1)."""
    return 0.2


def parse_sequences_response(response_text: str) -> list[dict]:
    """
    Parse the JSON response from sequence generator.
    
    Converts string sequences to structured format for Request 2.
    
    Args:
        response_text: Raw JSON string from LLM
        
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
    """Parse a single action string into structured format."""
    import re
    
    action_str = action_str.strip()
    
    if action_str == "end_turn":
        return {"action_type": "end_turn", "card_name": None, "target_name": None, "cc_cost": 0}
    
    # Pattern for card names: word characters, optionally followed by space and more words
    # E.g., "Knight", "Paper Plane"
    card_name_pattern = r'(\w+(?:\s+\w+)?)'
    
    # Pattern for targets: can be card name OR UUID
    # UUID: hex chars and hyphens like bd9629b1-0671-4024-8252-515e9f49f948
    target_pattern = r'([a-f0-9-]{36}|\w+(?:\s+\w+)?)'
    
    # Match "play CARDNAME" or "play CARDNAME [target: xyz]"
    play_match = re.match(rf'play\s+{card_name_pattern}\s*(?:\[target:\s*([^\]]+)\])?', action_str, re.I)
    if play_match:
        return {
            "action_type": "play_card",
            "card_name": play_match.group(1),
            "target_name": play_match.group(2).strip() if play_match.group(2) else None,
            "cc_cost": 0,  # Card cost tracked in sequence's total_cc_spent
        }
    
    # Match "tussle ATTACKER->TARGET" (target can be UUID or name)
    tussle_match = re.match(rf'tussle\s+{card_name_pattern}\s*[->]+\s*{target_pattern}', action_str, re.I)
    if tussle_match:
        return {
            "action_type": "tussle",
            "card_name": tussle_match.group(1),
            "target_name": tussle_match.group(2),
            "cc_cost": 2,
        }
    
    # Match "direct_attack ATTACKER"
    da_match = re.match(rf'direct_attack\s+{card_name_pattern}', action_str, re.I)
    if da_match:
        return {
            "action_type": "direct_attack",
            "card_name": da_match.group(1),
            "target_name": None,
            "cc_cost": 2,
        }
    
    # Match "activate CARDNAME->TARGET" (target can be UUID or name)
    activate_match = re.match(rf'activate\s+{card_name_pattern}\s*[->]+\s*{target_pattern}', action_str, re.I)
    if activate_match:
        return {
            "action_type": "activate_ability",
            "card_name": activate_match.group(1),
            "target_name": activate_match.group(2),
            "cc_cost": 1,  # Default ability cost
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
