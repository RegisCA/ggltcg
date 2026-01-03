"""
Example loader for AI V4.

Selects exactly 3 relevant examples based on current game state:
1. Combo examples (highest priority) - when synergistic cards present
2. Phase examples (always include one) - based on turn number
3. Card-specific examples (fill remaining) - based on cards in hand/play

Selection priority ensures the most relevant guidance is provided.
"""

from typing import TYPE_CHECKING

from .combo_examples import COMBO_EXAMPLES
from .phase_examples import PHASE_EXAMPLES
from .card_examples import CARD_EXAMPLES

if TYPE_CHECKING:
    from game_engine.models.game_state import GameState


def get_relevant_examples(game_state: "GameState", player_id: str) -> list[str]:
    """
    Return exactly 3 examples relevant to current game state.
    
    Priority:
    1. Combo examples if synergistic cards are present
    2. Phase example based on turn number (always include one)
    3. Card-specific examples to fill remaining slots
    
    Args:
        game_state: Current GameState object
        player_id: ID of the AI player
        
    Returns:
        List of exactly 3 example strings (XML formatted)
    """
    examples: list[str] = []
    player = game_state.players[player_id]
    opponent = game_state.get_opponent(player_id)
    
    # Collect card names for lookup
    card_names = {c.name for c in player.hand + player.in_play}
    
    # Track which cards already have examples to avoid duplicates
    cards_covered: set[str] = set()
    
    # 1. Check for COMBO examples first (highest priority)
    if "Surge" in card_names and "Knight" in card_names:
        examples.append(COMBO_EXAMPLES["surge_knight"])
        cards_covered.update(["Surge", "Knight"])
    elif "Surge" in card_names and len([c for c in player.hand if c.cost == 1]) >= 2:
        # Surge + multiple 1-CC toys
        examples.append(COMBO_EXAMPLES["surge_double_play"])
        cards_covered.add("Surge")
    
    # Archer finish combo - check if opponent has low-STA toy
    if "Archer" in card_names and "Archer" not in cards_covered:
        low_sta_targets = [
            c for c in opponent.in_play 
            if c.is_toy() and c.get_effective_stamina() <= player.cc
        ]
        if low_sta_targets:
            examples.append(COMBO_EXAMPLES["archer_finish"])
            cards_covered.add("Archer")
    
    # Knight cleanup combo - if Knight in play and opponent has toys
    if "Knight" in [c.name for c in player.in_play] and "Knight" not in cards_covered:
        if len(opponent.in_play) >= 1:
            examples.append(COMBO_EXAMPLES["knight_cleanup"])
            cards_covered.add("Knight")
    
    # 2. Add phase-based example (always include one)
    turn = game_state.turn_number
    if turn <= 3:
        phase_example = PHASE_EXAMPLES["early_game"]
    elif turn <= 6:
        phase_example = PHASE_EXAMPLES["mid_game"]
    else:
        phase_example = PHASE_EXAMPLES["end_game"]
    
    # Only add if we haven't exceeded 3
    if len(examples) < 3:
        examples.append(phase_example)
    
    # 3. Fill remaining slots with card-specific examples
    # Priority order from design doc
    CARD_PRIORITY = ["Knight", "Archer", "Surge", "Paper Plane", "Drop", "Wake"]
    
    for card_name in CARD_PRIORITY:
        if len(examples) >= 3:
            break
        
        # Skip if card not in player's cards
        if card_name not in card_names:
            continue
        
        # Skip if already covered by combo example
        if card_name in cards_covered:
            continue
        
        # Skip if card not in examples library
        if card_name not in CARD_EXAMPLES:
            continue
        
        examples.append(CARD_EXAMPLES[card_name])
        cards_covered.add(card_name)
    
    # 4. Pad with generic efficiency if needed
    # Use early_game as fallback since it covers CC efficiency
    while len(examples) < 3:
        # Avoid duplicates
        if PHASE_EXAMPLES["early_game"] not in examples:
            examples.append(PHASE_EXAMPLES["early_game"])
        elif PHASE_EXAMPLES["mid_game"] not in examples:
            examples.append(PHASE_EXAMPLES["mid_game"])
        else:
            examples.append(PHASE_EXAMPLES["end_game"])
    
    return examples[:3]


def get_game_phase(turn_number: int) -> str:
    """
    Determine the game phase based on turn number.
    
    Args:
        turn_number: Current turn number
        
    Returns:
        Phase string: "early_game", "mid_game", or "end_game"
    """
    if turn_number <= 3:
        return "early_game"
    elif turn_number <= 6:
        return "mid_game"
    else:
        return "end_game"


def format_examples_for_prompt(examples: list[str]) -> str:
    """
    Format examples list into a single string for the prompt.
    
    Args:
        examples: List of example strings (XML formatted)
        
    Returns:
        Combined examples string with spacing
    """
    return "\n\n".join(examples)
