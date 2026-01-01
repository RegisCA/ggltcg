"""
Formatters for AI prompts.

This module contains functions that format game state and valid actions
into prompts for the AI player.
"""

import logging
from typing import List, Optional, Any

from .card_library import CARD_EFFECTS_LIBRARY
from .system_prompt import ACTION_SELECTION_PROMPT

logger = logging.getLogger(__name__)


def format_game_state_for_ai(game_state, ai_player_id: str, game_engine=None) -> str:
    """
    Format game state into a clear, strategic summary for the AI.
    Includes card effects and strategic analysis.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
    Returns:
        Formatted string describing the game state with strategic context
    """
    ai_player = game_state.players[ai_player_id]
    opponent = game_state.get_opponent(ai_player_id)
    
    # Format AI's hand with effect descriptions and stats for Toys
    ai_hand_details = []
    for card in ai_player.hand:
        card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
        effect = card_info.get("effect", "Unknown effect")
        # Include stats for Toy cards so AI can compare with opponent's board
        if card.is_toy():
            # Show base stats (cards in hand don't have continuous effects applied yet)
            stats_str = f" [{card.speed} SPD, {card.strength} STR, {card.stamina} STA]"
        else:
            stats_str = ""
        # Calculate effective cost with Gibbers and other cost modifiers
        if game_engine and card.cost >= 0:  # Skip Copy card (cost -1)
            effective_cost = game_engine.calculate_card_cost(card, ai_player)
        else:
            effective_cost = card.cost
        # Don't include strategic_use here - it will be shown in valid actions
        ai_hand_details.append(
            f"{card.name} (cost {effective_cost}){stats_str} - {effect}."
        )
    ai_hand = "\n    ".join(ai_hand_details) if ai_hand_details else "EMPTY - Must tussle or end turn"
    
    # Format AI's in-play cards
    ai_in_play = []
    for card in ai_player.in_play:
        if card.is_toy():
            if game_engine:
                # Use GameEngine to get stats with continuous effects (Ka, Demideca, etc.)
                spd = game_engine.get_card_stat(card, "speed")
                str_val = game_engine.get_card_stat(card, "strength")
                cur_sta = game_engine.get_effective_stamina(card)
                max_sta = game_engine.get_card_stat(card, "stamina")
            else:
                # Fallback to card methods (won't include continuous effects)
                spd = card.get_effective_speed()
                str_val = card.get_effective_strength()
                cur_sta = card.get_effective_stamina()
                max_sta = card.stamina + card.modifications.get("stamina", 0)
            ai_in_play.append(
                f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA)"
            )
        else:
            ai_in_play.append(card.name)
    
    # Format opponent's in-play cards with threat analysis
    opp_in_play_details = []
    for card in opponent.in_play:
        if card.is_toy():
            # For copied cards (e.g., "Copy of Gibbers"), look up the original card name
            lookup_name = card.name
            if card.name.startswith("Copy of "):
                lookup_name = card.name[8:]  # Remove "Copy of " prefix
            card_info = CARD_EFFECTS_LIBRARY.get(lookup_name, {})
            threat = card_info.get("threat_level", "UNKNOWN")
            if game_engine:
                # Use GameEngine to get stats with continuous effects (Ka, Demideca, etc.)
                spd = game_engine.get_card_stat(card, "speed")
                str_val = game_engine.get_card_stat(card, "strength")
                cur_sta = game_engine.get_effective_stamina(card)
                max_sta = game_engine.get_card_stat(card, "stamina")
            else:
                # Fallback to card methods (won't include continuous effects)
                spd = card.get_effective_speed()
                str_val = card.get_effective_strength()
                cur_sta = card.get_effective_stamina()
                max_sta = card.stamina + card.modifications.get("stamina", 0)
            opp_in_play_details.append(
                f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA) - THREAT: {threat}"
            )
        else:
            opp_in_play_details.append(card.name)
    opp_in_play = "\n    ".join(opp_in_play_details) if opp_in_play_details else "NONE (play a Toy first, then you can direct attack)"
    
    # Calculate board strength (total STR of all Toys in play)
    if game_engine:
        ai_total_str = sum(game_engine.get_card_stat(card, "strength") for card in ai_player.in_play if card.is_toy())
        opp_total_str = sum(game_engine.get_card_stat(card, "strength") for card in opponent.in_play if card.is_toy())
    else:
        ai_total_str = sum(card.get_effective_strength() for card in ai_player.in_play if card.is_toy())
        opp_total_str = sum(card.get_effective_strength() for card in opponent.in_play if card.is_toy())
    
    # Determine board state
    if opp_total_str > ai_total_str + 3:
        board_state = "[BEHIND] OPPONENT DOMINATES - You are behind on board. Consider defensive plays or board wipes."
    elif ai_total_str > opp_total_str + 3:
        board_state = "[AHEAD] YOU DOMINATE - You have board advantage. Press your advantage with tussles."
    else:
        board_state = "[EVEN] EVEN BOARD - Board state is balanced. Look for favorable tussles."
    
    state_summary = f"""## CURRENT GAME STATE (Turn {game_state.turn_number})

### YOUR STATUS (You are: {ai_player.name})
- CC: {ai_player.cc}/7
- Hand ({len(ai_player.hand)} cards):
    {ai_hand}
- In Play ({len(ai_player.in_play)}): {', '.join(ai_in_play) if ai_in_play else "NONE"}
- Sleep Zone ({len(ai_player.sleep_zone)} cards): {', '.join([c.name for c in ai_player.sleep_zone])}

### OPPONENT STATUS ({opponent.name})
- CC: {opponent.cc}/7
- Hand: {len(opponent.hand)} cards{' (hidden)' if len(opponent.hand) > 0 else ' - EMPTY, no hand cards to attack!'}
- In Play ({len(opponent.in_play)}):
    {opp_in_play}
- Sleep Zone ({len(opponent.sleep_zone)} cards): {', '.join([c.name for c in opponent.sleep_zone])}

### BOARD ANALYSIS
- Your Total Strength: {ai_total_str}
- Opponent Total Strength: {opp_total_str}
- {board_state}

### VICTORY CHECK
- Your cards sleeped: {len(ai_player.sleep_zone)}/{len(ai_player.hand) + len(ai_player.in_play) + len(ai_player.sleep_zone)}
- Opponent cards sleeped: {len(opponent.sleep_zone)}/{len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)}
- **YOU WIN IF: Opponent's Sleep Zone = {len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)} cards**
"""
    
    return state_summary


def format_valid_actions_for_ai(valid_actions: list, game_state=None, ai_player_id: str = None, game_engine=None) -> str:
    """
    Format the list of valid actions into a numbered list for the AI.
    Actions are numbered 1-based to match how the AI will reference them.
    Includes target options and strategic context.
    
    Args:
        valid_actions: List of ValidAction objects
        game_state: Optional GameState to look up card details
        ai_player_id: Optional player ID to identify AI's cards
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
    Returns:
        Formatted string with numbered actions and strategic context
    """
    if not valid_actions:
        return "NO VALID ACTIONS AVAILABLE"
    
    actions_text = "## YOUR VALID ACTIONS (Choose ONE):\n\n"
    
    # Helper to get card details with ID
    def get_card_details(card_id: str) -> tuple[str, str, str]:
        """Returns (display_name, actual_id, owner_label) tuple"""
        if not game_state:
            return (card_id, card_id, "")
        # Search all zones for the card
        for player in game_state.players.values():
            for card in player.hand + player.in_play + player.sleep_zone:
                if card.id == card_id:
                    # Determine ownership label
                    if player.player_id == ai_player_id:
                        owner_label = "YOUR"
                    else:
                        owner_label = "OPPONENT'S"
                    
                    if card.is_toy():
                        if game_engine:
                            # Use GameEngine to get stats with continuous effects
                            spd = game_engine.get_card_stat(card, "speed")
                            str_val = game_engine.get_card_stat(card, "strength")
                            cur_sta = game_engine.get_effective_stamina(card)
                            max_sta = game_engine.get_card_stat(card, "stamina")
                        else:
                            # Fallback to card methods
                            spd = card.get_effective_speed()
                            str_val = card.get_effective_strength()
                            cur_sta = card.get_effective_stamina()
                            max_sta = card.stamina + card.modifications.get("stamina", 0)
                        display = f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA)"
                    else:
                        display = card.name
                    return (display, card.id, owner_label)
        return (card_id, card_id, "")
    
    # Number actions 1-based (action_number will be converted to 0-based index)
    for i, action in enumerate(valid_actions, start=1):
        action_text = f"{i}. {action.description}"
        
        # DEBUG: Log target_options for debugging
        logger.debug(f"Action {i} ({action.description}): target_options={action.target_options}, alt_cost={action.alternative_cost_options}, max_targets={action.max_targets}")
        
        # Add target information if available
        if action.target_options is not None and len(action.target_options) > 0:
            if action.target_options == ["direct_attack"]:
                action_text += " [Direct attack - no defender]"
            else:
                target_details = []
                for target_id in action.target_options:
                    display_name, actual_id, owner_label = get_card_details(target_id)
                    # Put the UUID first so LLM clearly sees it's the ID to use
                    # Add owner label to clarify whose card this is
                    if owner_label:
                        target_details.append(f"[ID: {actual_id}] {owner_label} {display_name}")
                    else:
                        target_details.append(f"[ID: {actual_id}] {display_name}")
                # Format targets list (extract join logic to avoid backslash in f-string)
                targets_list = '\n   - '.join(target_details)
                
                # Indicate multi-target selection when max_targets > 1 (e.g., Sun)
                max_targets = getattr(action, 'max_targets', 1) or 1
                if max_targets > 1:
                    action_text += f"\n   Select up to {max_targets} targets (add UUIDs to target_ids array):\n   - {targets_list}"
                else:
                    action_text += f"\n   Available targets (use the UUID from [ID: ...]):\n   - {targets_list}"
        
        # Add alternative cost information if available
        if action.alternative_cost_options is not None and len(action.alternative_cost_options) > 0:
            alt_cost_details = []
            for alt_id in action.alternative_cost_options:
                display_name, actual_id, owner_label = get_card_details(alt_id)
                # Put the UUID first so LLM clearly sees it's the ID to use
                # Note: Alternative costs are always from your own cards
                alt_cost_details.append(f"[ID: {actual_id}] {display_name}")
            # Format alternative cost list (extract join logic to avoid backslash in f-string)
            alt_cost_list = '\n   - '.join(alt_cost_details)
            action_text += f"\n   Can pay alternative cost by sleeping (use the UUID from [ID: ...]):\n   - {alt_cost_list}"
        
        # NOTE: Strategic hints removed from action list to avoid confusion
        # Generic hints like "Return opponent's threat" contradict specific targets like "YOUR Knight"
        # Strategic hints are shown in the hand section instead, where they provide context
        # without conflicting with specific targeting choices
        
        actions_text += action_text + "\n"
    
    return actions_text


def get_ai_turn_prompt(game_state, ai_player_id: str, valid_actions: list, game_engine=None) -> str:
    """
    Create the complete prompt for the AI's turn.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        valid_actions: List of valid actions from the API
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
    Returns:
        Complete prompt string
    """
    state_text = format_game_state_for_ai(game_state, ai_player_id, game_engine)
    actions_text = format_valid_actions_for_ai(valid_actions, game_state, ai_player_id, game_engine)
    
    return f"""{state_text}

{actions_text}

{ACTION_SELECTION_PROMPT}"""
