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
    
    @staticmethod
    def get_tussle_cost(game_state: GameState, attacker_name: str) -> int:
        """
        Calculate the CC cost for a tussle.
        
        Default is 2 CC, but modified by:
        - Wizard: All tussles cost 1
        - Raggy: Raggy's tussles cost 0
        
        Args:
            game_state: Current game state
            attacker_name: Name of the attacking card
            
        Returns:
            CC cost for the tussle
        """
        active_player = game_state.get_active_player()
        
        # Check for Raggy (specific card, cost 0)
        if attacker_name == "Raggy":
            return 0
        
        # Check for Wizard (all tussles cost 1)
        for card in active_player.in_play:
            if card.name == "Wizard":
                return 1
        
        # Default tussle cost
        return 2
    
    @staticmethod
    def can_raggy_tussle(game_state: GameState) -> bool:
        """
        Check if Raggy can tussle (not allowed on Turn 1).
        
        Args:
            game_state: Current game state
            
        Returns:
            True if Raggy can tussle
        """
        return not game_state.is_first_turn()
    
    @staticmethod
    def calculate_card_cost(game_state: GameState, card_name: str, base_cost: int) -> int:
        """
        Calculate the actual cost to play a card after modifiers.
        
        Handles:
        - Dream: Costs 1 less per sleeping card
        - Copy: Costs same as copied Toy
        - Other reductions
        
        Args:
            game_state: Current game state
            card_name: Name of the card
            base_cost: Base cost from card definition
            
        Returns:
            Final cost to pay
        """
        active_player = game_state.get_active_player()
        
        # Dream: costs 1 less for each sleeping card
        if card_name == "Dream":
            reduction = len(active_player.sleep_zone)
            return max(0, base_cost - reduction)
        
        # Copy: cost determined by copied card (handled separately)
        if card_name == "Copy":
            return base_cost  # Should be set before calling this
        
        return base_cost
