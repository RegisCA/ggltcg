"""Turn manager for handling game phases and CC management."""
from ..models.game_state import GameState, Phase
from ..models.player import Player


class TurnManager:
    """Manages turn progression and phase transitions."""
    
    @staticmethod
    def start_turn(game_state: GameState):
        """
        Execute start of turn phase.
        
        - Gain CC (4 normally, 2 on Turn 1 for first player)
        - Set phase to START
        - Resolve any "at start of turn" effects
        
        Args:
            game_state: Current game state
        """
        game_state.phase = Phase.START
        active_player = game_state.get_active_player()
        
        # Determine CC gain
        if game_state.is_first_turn() and game_state.active_player_id == game_state.first_player_id:
            cc_gain = 2
            game_state.log_event(f"{active_player.name} gains {cc_gain} CC (first turn)")
        else:
            cc_gain = 4
            game_state.log_event(f"{active_player.name} gains {cc_gain} CC")
        
        active_player.gain_cc(cc_gain)
        
        # Move to main phase
        game_state.phase = Phase.MAIN
    
    @staticmethod
    def end_turn(game_state: GameState):
        """
        Execute end of turn phase.
        
        - Set phase to END
        - Resolve any "at end of turn" effects
        - Reset turn-specific counters
        - Switch active player
        - Increment turn number
        
        Args:
            game_state: Current game state
        """
        game_state.phase = Phase.END
        active_player = game_state.get_active_player()
        
        game_state.log_event(f"{active_player.name} ends turn with {active_player.cc} CC banked")
        
        # Reset turn counters
        active_player.reset_turn_counters()
        
        # Switch to opponent
        opponent = game_state.get_opponent_of_active()
        game_state.active_player_id = opponent.player_id
        
        # Increment turn if we've completed a full round
        # (both players have had a turn)
        if len(game_state.players) == 2:
            # Check if we're switching back to first player
            if game_state.active_player_id == game_state.first_player_id:
                game_state.turn_number += 1
        
        # Start next player's turn
        TurnManager.start_turn(game_state)
    
    @staticmethod
    def can_play_card(player: Player, card_cost: int) -> bool:
        """
        Check if player can afford to play a card.
        
        Args:
            player: Player attempting to play
            card_cost: Cost of the card
            
        Returns:
            True if player has enough CC
        """
        return player.has_cc(card_cost)
