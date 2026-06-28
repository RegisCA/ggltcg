"""
Formatters for AI prompts.

This module contains functions that format valid actions into the execution
prompt sent to the AI player.
"""

import logging

logger = logging.getLogger(__name__)


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
            for card in player.hand + player.in_play + player.break_zone:
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
            action_text += f"\n   Can pay alternative cost by breaking (use the UUID from [ID: ...]):\n   - {alt_cost_list}"
        
        # NOTE: Strategic hints removed from action list to avoid confusion
        # Generic hints like "Return opponent's threat" contradict specific targets like "YOUR Knight"
        # Strategic hints are shown in the hand section instead, where they provide context
        # without conflicting with specific targeting choices
        
        actions_text += action_text + "\n"

    return actions_text
