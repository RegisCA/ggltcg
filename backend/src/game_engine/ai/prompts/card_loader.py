"""
Dynamic Card Guidance Loader

Loads card-specific AI guidance from YAML and filters to only include
cards relevant to the current game state. This prevents prompt bloat
from including documentation for all 40+ cards when only 6-12 are relevant.

Architecture:
- YAML file contains condensed guidance (trap, reminder, threat)
- Loader filters to cards in: player.hand + player.in_play + opponent.in_play
- Output formatted as compact text (not full dict structure)
"""

import os
import yaml
from typing import Set, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState

# Cache the loaded YAML to avoid repeated file I/O
_CARD_GUIDANCE_CACHE: Dict[str, Any] = {}


def load_card_guidance() -> Dict[str, Any]:
    """
    Load card guidance from YAML file.
    
    Returns:
        Dict mapping card_name -> {trap, reminder, threat}
    """
    global _CARD_GUIDANCE_CACHE
    
    if _CARD_GUIDANCE_CACHE:
        return _CARD_GUIDANCE_CACHE
    
    # Find the YAML file relative to this module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(current_dir, "card_guidance.yaml")
    
    with open(yaml_path, "r") as f:
        _CARD_GUIDANCE_CACHE = yaml.safe_load(f)
    
    return _CARD_GUIDANCE_CACHE


def get_relevant_card_names(game_state: "GameState", player_id: str) -> Set[str]:
    """
    Get card names relevant to the current game state.
    
    Includes:
    - Player's hand
    - Player's in_play
    - Opponent's in_play
    
    Does NOT include break zones (those cards aren't immediately playable).
    
    Args:
        game_state: Current game state
        player_id: AI player's ID
        
    Returns:
        Set of card names relevant to this game
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    relevant_names = set()
    
    # Player's cards (can play or use)
    for card in player.hand:
        relevant_names.add(card.name)
    for card in player.in_play:
        relevant_names.add(card.name)
    
    # Opponent's cards (need to react to)
    for card in opponent.in_play:
        relevant_names.add(card.name)
    
    return relevant_names


def generate_threat_priorities(game_state: "GameState", player_id: str) -> str:
    """
    Generate threat priority guidance based on opponent's cards actually in play.

    Surfaces CRITICAL, HIGH, and MEDIUM threats (only for cards present in the
    current game — avoids listing cards that aren't on the board). LOW threats
    are omitted since card_guidance's per-card trap/reminder text already
    covers them without needing a priority callout.
    """
    guidance_data = load_card_guidance()
    opponent = game_state.get_opponent(player_id)

    critical: list[str] = []
    high: list[str] = []
    medium: list[str] = []

    for card in opponent.in_play:
        card_info = guidance_data.get(card.name)
        if not card_info:
            continue
        threat = card_info.get("threat", "MEDIUM")
        if threat == "CRITICAL":
            critical.append(card.name)
        elif threat == "HIGH":
            high.append(card.name)
        elif threat == "MEDIUM":
            medium.append(card.name)

    if not critical and not high and not medium:
        return ""

    lines = ["# THREAT PRIORITIES (opponent in play)"]
    if critical:
        lines.append(f"CRITICAL: {', '.join(critical)}")
    if high:
        lines.append(f"HIGH: {', '.join(high)}")
    if medium:
        lines.append(f"MEDIUM: {', '.join(medium)}")
    return "\n".join(lines)


def get_relevant_card_guidance(game_state: "GameState", player_id: str) -> str:
    """
    Get formatted card guidance for cards relevant to current game state.

    Args:
        game_state: Current game state
        player_id: AI player's ID

    Returns:
        Formatted string with card guidance (empty if no relevant cards)
    """
    guidance_data = load_card_guidance()
    relevant_names = get_relevant_card_names(game_state, player_id)

    # Filter to only cards with guidance entries
    relevant_with_guidance = relevant_names & guidance_data.keys()

    if not relevant_with_guidance:
        return ""
    
    # Format as compact text
    lines = ["# CARD-SPECIFIC GUIDANCE"]
    
    for card_name in sorted(relevant_with_guidance):
        card_info = guidance_data[card_name]
        
        # Format: **CardName** (THREAT): Trap: ... | Reminder: ...
        threat = card_info.get("threat", "MEDIUM")
        trap = card_info.get("trap", "")
        reminder = card_info.get("reminder", "")
        
        line_parts = [f"**{card_name}** ({threat})"]
        
        if trap:
            line_parts.append(f"⚠️ {trap}")
        if reminder:
            line_parts.append(f"→ {reminder}")
        
        lines.append(" | ".join(line_parts))
    
    return "\n".join(lines)


def format_card_guidance(game_state: "GameState", player_id: str) -> str:
    """
    Format card guidance (trap/reminder/threat) for cards relevant to the
    current game, sent in full to the strategic-selection prompt.

    Args:
        game_state: Current game state
        player_id: AI player's ID

    Returns:
        Compact formatted guidance string
    """
    guidance_text = get_relevant_card_guidance(game_state, player_id)

    if not guidance_text:
        return "# CARD-SPECIFIC GUIDANCE\nNo special guidance needed for cards in current game."

    return guidance_text


def build_card_labels(game_state: "GameState", player_id: str) -> Dict[str, str]:
    """
    Assign a short, stable label to every card the AI is allowed to see: its
    own hand + in_play + break_zone (Y1, Y2, ...) and the opponent's in_play
    (O1, O2, ...).

    The AI's own break zone is included (unlike the opponent's hand) because
    it is not hidden information - it's the AI's own zone, and recursion
    cards (Wake/Sun/Glue/"That was fun") target it, so the model needs to see
    what's actually recoverable rather than reasoning about it blind.

    Deliberately excludes the opponent's hand - this game hides hand contents
    from the opponent (see ``get_relevant_card_names``, which the same module
    already scopes the same way for card_guidance lookups); a label/legend
    entry must not leak it. No action ever targets a card sitting in a hand,
    so nothing downstream needs a label for one. The opponent's break zone is
    also excluded: no effect in this game ever targets an opponent's break
    zone, so a label for it would add prompt noise with no actionable use.

    Built fresh from whatever ``game_state`` snapshot is passed in, but pure
    and deterministic given that snapshot — the enumerator (raw_string target
    labels) and the strategic-selector prompt (board legend) each call this
    independently on the same turn's root game state and get identical
    mappings, with no need to thread a shared dict between them.
    """
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)

    labels: Dict[str, str] = {}
    own_cards = list(player.hand) + list(player.in_play) + list(player.break_zone)
    for i, card in enumerate(own_cards, start=1):
        labels[card.id] = f"Y{i}"
    for i, card in enumerate(opponent.in_play, start=1):
        labels[card.id] = f"O{i}"
    return labels


def format_board_legend(
    game_state: "GameState", player_id: str, game_engine: Optional[Any] = None
) -> str:
    """
    Render the board-state legend for the Request 2 prompt: one line per card
    in the AI's own hand/in-play/break_zone and the opponent's in-play (see
    ``build_card_labels`` - the opponent's hand is intentionally omitted,
    since this game does not reveal hand contents to the opponent), giving
    its short label, name, cost, stats (Toys only), and effect text.

    Passing ``game_engine`` lets in-play stats reflect continuous effects
    (Ka's +2 STR aura, Gibbers' cost tax, etc); without it, base stats/cost
    are shown.
    """
    labels = build_card_labels(game_state, player_id)
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)

    lines = ["# BOARD LEGEND (label [side zone] Name (cost) stats - effect)"]
    for side_label, side, zones in (
        (
            "YOU",
            player,
            (("hand", player.hand), ("in_play", player.in_play), ("break_zone", player.break_zone)),
        ),
        ("OPP", opponent, (("in_play", opponent.in_play),)),
    ):
        for zone_label, zone in zones:
            for card in zone:
                label = labels[card.id]

                if game_engine is not None and card.cost >= 0:
                    cost = game_engine.calculate_card_cost(card, side)
                else:
                    cost = card.cost

                if card.is_toy():
                    if zone_label == "in_play" and game_engine is not None:
                        spd = game_engine.get_card_stat(card, "speed")
                        str_val = game_engine.get_card_stat(card, "strength")
                        cur_sta = game_engine.get_effective_stamina(card)
                        max_sta = game_engine.get_card_stat(card, "stamina")
                    else:
                        spd, str_val = card.speed, card.strength
                        cur_sta = max_sta = card.stamina
                    stats = f" [{spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA]"
                else:
                    stats = ""

                lines.append(
                    f"{label} [{side_label} {zone_label}] {card.name} (cost {cost}){stats} - {card.effect_text}"
                )
    return "\n".join(lines)
