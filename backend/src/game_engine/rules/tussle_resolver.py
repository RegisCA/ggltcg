"""Tussle resolver for combat resolution in GGLTCG."""
from dataclasses import dataclass
from typing import Optional, List
from ..models.game_state import GameState
from ..models.card import Card
from ..models.player import Player
import random
import copy


@dataclass
class TussleResult:
    """
    Result of a tussle resolution.
    
    Attributes:
        attacker_name: Name of attacking card
        defender_name: Name of defending card (or "Hand" for direct attack)
        attacker_speed: Effective speed of attacker
        defender_speed: Effective speed of defender
        attacker_damage: Damage dealt by attacker
        defender_damage: Damage dealt by defender
        attacker_sleeped: Whether attacker was sleeped
        defender_sleeped: Whether defender was sleeped
        first_striker: Who struck first ("attacker", "defender", or "simultaneous")
        direct_attack: Whether this was a direct attack
        sleeped_from_hand: Card sleeped from hand (direct attack only)
    """
    attacker_name: str
    defender_name: str
    attacker_speed: int
    defender_speed: int = 0
    attacker_damage: int = 0
    defender_damage: int = 0
    attacker_sleeped: bool = False
    defender_sleeped: bool = False
    first_striker: str = "simultaneous"
    direct_attack: bool = False
    sleeped_from_hand: Optional[str] = None


class TussleResolver:
    """Handles tussle resolution logic."""
    
    @staticmethod
    def predict_winner(game_state: GameState, attacker: Card, defender: Card) -> str:
        """
        Predict the winner of a tussle without mutating the real game state.
        
        Simulates a tussle to determine the outcome without side effects.
        Used by AI to filter out guaranteed-loss tussles.
        
        Args:
            game_state: Current game state
            attacker: Attacking card
            defender: Defending card
            
        Returns:
            'attacker' if attacker wins (defender gets sleeped)
            'defender' if defender wins (attacker gets sleeped)
            'simultaneous' if both are sleeped or both survive
        """
        # Create copies of just the cards to avoid game_state deepcopy issues
        attacker_copy = copy.deepcopy(attacker)
        defender_copy = copy.deepcopy(defender)
        
        # Calculate effective speeds
        attacker_speed = attacker_copy.get_effective_speed()
        defender_speed = defender_copy.get_effective_speed()
        
        # Apply turn bonus: attacker ALWAYS gets +1 speed (attacking on their turn)
        # Defender does NOT get turn bonus (defending on opponent's turn)
        attacker_speed += 1
        
        # Get effective strengths
        attacker_strength = attacker_copy.get_effective_strength()
        defender_strength = defender_copy.get_effective_strength()
        
        # Check for Knight's auto-win ability
        if TussleResolver._check_knight_auto_win(game_state, attacker_copy, defender_copy):
            return "attacker"
        
        # Simulate the tussle outcome based on speed and strength
        attacker_survives = True
        defender_survives = True
        
        if attacker_speed > defender_speed:
            # Attacker strikes first
            if defender_copy.current_stamina <= attacker_strength:
                defender_survives = False
            else:
                # Defender survives and strikes back
                if attacker_copy.current_stamina <= defender_strength:
                    attacker_survives = False
        elif defender_speed > attacker_speed:
            # Defender strikes first
            if attacker_copy.current_stamina <= defender_strength:
                attacker_survives = False
            else:
                # Attacker survives and strikes back
                if defender_copy.current_stamina <= attacker_strength:
                    defender_survives = False
        else:
            # Simultaneous strikes
            if attacker_copy.current_stamina <= defender_strength:
                attacker_survives = False
            if defender_copy.current_stamina <= attacker_strength:
                defender_survives = False
        
        # Determine winner
        if not attacker_survives and defender_survives:
            return "defender"
        if not defender_survives and attacker_survives:
            return "attacker"
        return "simultaneous"
    
    @staticmethod
    def resolve_tussle(
        game_state: GameState,
        attacker: Card,
        defender: Optional[Card] = None
    ) -> TussleResult:
        """
        Resolve a tussle between two cards or a direct attack.
        
        Args:
            game_state: Current game state
            attacker: The attacking Toy
            defender: The defending Toy (None for direct attack)
            
        Returns:
            TussleResult with outcome details
        """
        if defender is None:
            return TussleResolver._resolve_direct_attack(game_state, attacker)
        else:
            return TussleResolver._resolve_standard_tussle(game_state, attacker, defender)
    
    @staticmethod
    def _resolve_standard_tussle(
        game_state: GameState,
        attacker: Card,
        defender: Card
    ) -> TussleResult:
        """
        Resolve a standard tussle between two Toys.
        
        1. Calculate effective speeds (including turn bonus)
        2. Determine strike order
        3. Apply damage
        4. Sleep defeated cards
        
        Args:
            game_state: Current game state
            attacker: The attacking Toy
            defender: The defending Toy
            
        Returns:
            TussleResult with outcome details
        """
        active_player = game_state.get_active_player()
        
        # Calculate effective speeds
        attacker_speed = attacker.get_effective_speed()
        defender_speed = defender.get_effective_speed()
        
        # Apply turn bonus (+1 speed for active player's cards)
        if attacker.controller == active_player.player_id:
            attacker_speed += 1
        if defender.controller == active_player.player_id:
            defender_speed += 1
        
        # Apply continuous effects (Ka, Demideca, etc.)
        attacker_speed += TussleResolver._get_speed_modifiers(game_state, attacker)
        defender_speed += TussleResolver._get_speed_modifiers(game_state, defender)
        
        # Get effective strengths
        attacker_strength = attacker.get_effective_strength()
        defender_strength = defender.get_effective_strength()
        
        # Apply strength modifiers (Ka, Demideca, etc.)
        attacker_strength += TussleResolver._get_strength_modifiers(game_state, attacker)
        defender_strength += TussleResolver._get_strength_modifiers(game_state, defender)
        
        result = TussleResult(
            attacker_name=attacker.name,
            defender_name=defender.name,
            attacker_speed=attacker_speed,
            defender_speed=defender_speed,
            attacker_damage=attacker_strength,
            defender_damage=defender_strength,
        )
        
        # Check for Knight's auto-win ability
        if TussleResolver._check_knight_auto_win(game_state, attacker, defender):
            result.defender_sleeped = True
            result.first_striker = "attacker"
            game_state.log_event(f"{attacker.name} (Knight) auto-wins tussle against {defender.name}")
            return result
        
        # Determine strike order and resolve
        if attacker_speed > defender_speed:
            # Attacker strikes first
            result.first_striker = "attacker"
            attacker.apply_damage(defender_strength)
            defender.apply_damage(attacker_strength)
            
            # Check if defender is sleeped before counter-attack
            if defender.is_defeated():
                result.defender_sleeped = True
                # Defender doesn't strike back
                result.defender_damage = 0
            elif attacker.is_defeated():
                result.attacker_sleeped = True
        
        elif defender_speed > attacker_speed:
            # Defender strikes first
            result.first_striker = "defender"
            defender.apply_damage(attacker_strength)
            attacker.apply_damage(defender_strength)
            
            # Check if attacker is sleeped before counter-attack
            if attacker.is_defeated():
                result.attacker_sleeped = True
                # Attacker doesn't deal damage
                result.attacker_damage = 0
            elif defender.is_defeated():
                result.defender_sleeped = True
        
        else:
            # Simultaneous strikes
            result.first_striker = "simultaneous"
            attacker.apply_damage(defender_strength)
            defender.apply_damage(attacker_strength)
            
            if attacker.is_defeated():
                result.attacker_sleeped = True
            if defender.is_defeated():
                result.defender_sleeped = True
        
        # Log the tussle
        game_state.log_event(
            f"Tussle: {attacker.name} ({attacker_speed} spd, {attacker_strength} str) "
            f"vs {defender.name} ({defender_speed} spd, {defender_strength} str) "
            f"- First strike: {result.first_striker}"
        )
        
        return result
    
    @staticmethod
    def _resolve_direct_attack(game_state: GameState, attacker: Card) -> TussleResult:
        """
        Resolve a direct attack (when opponent has no Toys in play).
        
        Sleep a random card from opponent's hand.
        Does NOT trigger "when sleeped" abilities.
        
        Args:
            game_state: Current game state
            attacker: The attacking Toy
            
        Returns:
            TussleResult with direct attack details
        """
        active_player = game_state.get_active_player()
        opponent = game_state.get_opponent_of_active()
        
        if not opponent.hand:
            raise ValueError("Opponent has no cards in hand for direct attack")
        
        # Select random card from opponent's hand
        target_card = random.choice(opponent.hand)
        
        result = TussleResult(
            attacker_name=attacker.name,
            defender_name="Hand",
            attacker_speed=attacker.get_effective_speed(),
            direct_attack=True,
            sleeped_from_hand=target_card.name,
        )
        
        # Sleep the card (does not trigger "when sleeped" effects)
        opponent.sleep_card(target_card)
        
        game_state.log_event(
            f"Direct attack: {attacker.name} sleeps {target_card.name} from opponent's hand"
        )
        
        # Increment direct attack counter
        active_player.direct_attacks_this_turn += 1
        
        return result
    
    @staticmethod
    def can_direct_attack(game_state: GameState) -> bool:
        """
        Check if active player can make a direct attack.
        
        Requirements:
        - Opponent has no Toys in play
        - Active player has fewer than 2 direct attacks this turn
        - Active player has at least one Toy in play
        
        Args:
            game_state: Current game state
            
        Returns:
            True if direct attack is allowed
        """
        active_player = game_state.get_active_player()
        opponent = game_state.get_opponent_of_active()
        
        return (
            not opponent.has_cards_in_play() and
            active_player.direct_attacks_this_turn < 2 and
            active_player.has_cards_in_play() and
            len(opponent.hand) > 0
        )
    
    @staticmethod
    def _check_knight_auto_win(
        game_state: GameState,
        attacker: Card,
        defender: Card
    ) -> bool:
        """
        Check if Knight's auto-win ability applies.
        
        Knight wins all tussles on active player's turn,
        EXCEPT against Beary.
        
        Args:
            game_state: Current game state
            attacker: The attacking card
            defender: The defending card
            
        Returns:
            True if Knight auto-wins
        """
        active_player = game_state.get_active_player()
        
        # Knight must be attacker and controlled by active player
        if attacker.name != "Knight" or attacker.controller != active_player.player_id:
            return False
        
        # Doesn't work against Beary
        if defender.name == "Beary":
            return False
        
        return True
    
    @staticmethod
    def _get_speed_modifiers(game_state: GameState, card: Card) -> int:
        """
        Calculate total speed modifiers from continuous effects.
        
        Args:
            game_state: Current game state
            card: Card to calculate modifiers for
            
        Returns:
            Total speed modifier
        """
        controller = game_state.players[card.controller]
        modifier = 0
        
        # Demideca: +1 to all stats
        for in_play_card in controller.in_play:
            if in_play_card.name == "Demideca":
                modifier += 1
        
        return modifier
    
    @staticmethod
    def _get_strength_modifiers(game_state: GameState, card: Card) -> int:
        """
        Calculate total strength modifiers from continuous effects.
        
        Args:
            game_state: Current game state
            card: Card to calculate modifiers for
            
        Returns:
            Total strength modifier
        """
        controller = game_state.players[card.controller]
        modifier = 0
        
        # Ka: +2 Strength
        for in_play_card in controller.in_play:
            if in_play_card.name == "Ka":
                modifier += 2
        
        # Demideca: +1 to all stats
        for in_play_card in controller.in_play:
            if in_play_card.name == "Demideca":
                modifier += 1
        
        return modifier
    
    @staticmethod
    def _get_stamina_modifiers(game_state: GameState, card: Card) -> int:
        """
        Calculate total stamina modifiers from continuous effects.
        
        Args:
            game_state: Current game state
            card: Card to calculate modifiers for
            
        Returns:
            Total stamina modifier
        """
        controller = game_state.players[card.controller]
        modifier = 0
        
        # Demideca: +1 to all stats
        for in_play_card in controller.in_play:
            if in_play_card.name == "Demideca":
                modifier += 1
        
        return modifier
