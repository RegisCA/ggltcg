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
from typing import Set, Dict, Any, TYPE_CHECKING

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
    
    Does NOT include sleep zones (those cards aren't immediately playable).
    
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


def format_card_guidance_compact(game_state: "GameState", player_id: str) -> str:
    """
    Format card guidance in ultra-compact format for minimal token usage.
    
    This is the version to include in the planning prompt.
    
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
