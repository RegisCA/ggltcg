"""
Base effect classes for the GGLTCG card game.

Effects are applied when:
- Continuous: While card is in play (Ka, Wizard, Demideca)
- Triggered: When specific condition occurs (Beary, Umbruh, Snuggles)
- Activated: Player pays cost to activate (Archer)
- Play: When card is played (Actions)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Any
from enum import Enum

if TYPE_CHECKING:
    from ...models.game_state import GameState
    from ...models.card import Card
    from ...models.player import Player


class EffectType(Enum):
    """Types of card effects in GGLTCG."""
    CONTINUOUS = "continuous"  # Applies while card is in play
    TRIGGERED = "triggered"    # Activates when condition is met
    ACTIVATED = "activated"    # Player pays cost to activate
    PLAY = "play"             # Resolves when card is played (Actions)


class TriggerTiming(Enum):
    """When triggered effects can activate."""
    WHEN_SLEEPED = "when_sleeped"           # Umbruh, Snuggles
    WHEN_OPPONENT_TUSSLES = "when_opponent_tussles"  # Beary
    WHEN_PLAYED = "when_played"             # Snuggles (on entry)
    START_OF_TURN = "start_of_turn"         # Belchaletta
    END_OF_TURN = "end_of_turn"
    WHEN_OTHER_CARD_PLAYED = "when_other_card_played"  # Hind Leg Kicker


class BaseEffect(ABC):
    """
    Abstract base class for all card effects.
    
    All card effects inherit from this class and implement their specific
    behavior in the apply() method.
    """
    
    def __init__(self, source_card: "Card"):
        """
        Initialize the effect.
        
        Args:
            source_card: The card that this effect belongs to
        """
        self.source_card = source_card
        self.effect_type: EffectType = EffectType.PLAY
    
    @abstractmethod
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Apply this effect to the game state.
        
        Args:
            game_state: The current game state
            **kwargs: Additional context-specific parameters
        """
        pass
    
    def can_apply(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if this effect can be applied.
        
        Args:
            game_state: The current game state
            **kwargs: Additional context-specific parameters
            
        Returns:
            True if the effect can be applied, False otherwise
        """
        return True
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(source={self.source_card.name})"


class ContinuousEffect(BaseEffect):
    """
    Base class for continuous effects that apply while the card is in play.
    
    Examples: Ka (+2 Strength), Wizard (tussle cost 1), Demideca (+1 all stats)
    
    Continuous effects:
    - Apply automatically while the source card is in play
    - Stack if multiple copies exist
    - Stop applying immediately when the source leaves play
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card)
        self.effect_type = EffectType.CONTINUOUS
    
    @abstractmethod
    def modify_stat(self, card: "Card", stat_name: str, base_value: int, 
                   game_state: "GameState") -> int:
        """
        Modify a card's stat value.
        
        Args:
            card: The card whose stat is being modified
            stat_name: Name of the stat ("speed", "strength", "stamina")
            base_value: The base value before modification
            game_state: The current game state
            
        Returns:
            The modified stat value
        """
        return base_value
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Continuous effects don't have a single "apply" moment.
        They're checked whenever stats are calculated.
        """
        pass


class TriggeredEffect(BaseEffect):
    """
    Base class for triggered effects that activate when a condition is met.
    
    Examples: Beary (cancel tussle), Umbruh (gain CC when sleeped), 
              Snuggles (sleep opponent card on entry)
    
    Triggered effects:
    - Have a specific trigger condition (timing)
    - May be optional (using "may") or mandatory
    - Only trigger if condition is met at the right time
    """
    
    def __init__(self, source_card: "Card", trigger: TriggerTiming, 
                 is_optional: bool = False):
        super().__init__(source_card)
        self.effect_type = EffectType.TRIGGERED
        self.trigger = trigger
        self.is_optional = is_optional
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if this triggered effect should activate.
        
        Args:
            game_state: The current game state
            **kwargs: Context about what triggered this (e.g., which card was sleeped)
            
        Returns:
            True if the trigger condition is met
        """
        return True
    
    @abstractmethod
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Apply the triggered effect."""
        pass


class ActivatedEffect(BaseEffect):
    """
    Base class for activated abilities that require payment to use.
    
    Example: Archer (spend CC to remove Stamina from cards)
    
    Activated effects:
    - Require the player to pay a cost (CC or other resource)
    - Can be used multiple times if affordable
    - Only available during appropriate phase/timing
    """
    
    def __init__(self, source_card: "Card", cost_cc: int = 0):
        super().__init__(source_card)
        self.effect_type = EffectType.ACTIVATED
        self.cost_cc = cost_cc
    
    def can_apply(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if the ability can be activated.
        
        Checks:
        - Player has enough CC to pay the cost
        - It's the appropriate phase/timing
        - Source card is in play and controlled by the active player
        """
        controller = game_state.get_card_controller(self.source_card)
        if not controller:
            return False
        
        active_player = game_state.get_active_player()
        if controller != active_player:
            return False
        
        if controller.cc < self.cost_cc:
            return False
        
        return True
    
    @abstractmethod
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Apply the activated effect.
        
        The cost payment should be handled before calling this method.
        """
        pass


class PlayEffect(BaseEffect):
    """
    Base class for effects that resolve when a card is played.
    
    Used for all Action cards: Clean, Copy, Rush, Sun, Toynado, Twist, Wake
    
    Play effects:
    - Resolve immediately when the card is played
    - Action cards go to Sleep Zone after resolving
    - May require targets or choices to be made when played
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card)
        self.effect_type = EffectType.PLAY
    
    @abstractmethod
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Resolve the play effect.
        
        Args:
            game_state: The current game state
            **kwargs: Targets or choices made when playing the card
        """
        pass
    
    def requires_targets(self) -> bool:
        """
        Check if this effect requires targets to be chosen.
        
        Returns:
            True if targets must be selected when playing
        """
        return False
    
    def get_max_targets(self) -> int:
        """
        Get the maximum number of targets this effect can have.
        
        Returns:
            Maximum number of targets (1 by default, 2 for Sun, etc.)
        """
        return 1
    
    def get_min_targets(self) -> int:
        """
        Get the minimum number of targets this effect requires.
        
        Returns:
            Minimum number of targets (1 for required targeting, 0 for optional)
        """
        return 1 if self.requires_targets() else 0
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> list:
        """
        Get list of valid targets for this effect.
        
        Args:
            game_state: The current game state
            player: Optional player who would be playing this card (if not provided, uses active player)
            
        Returns:
            List of valid target objects (cards, players, etc.)
        """
        return []


class CostModificationEffect(ContinuousEffect):
    """
    Special continuous effect that modifies costs.
    
    Examples: Wizard (tussles cost 1), Dream (costs 1 less per sleeping card)
    
    These effects are checked when calculating costs for actions.
    """
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """
        Modify the cost of a tussle.
        
        Args:
            base_cost: The base cost of the tussle (usually 2)
            game_state: The current game state
            controller: The player initiating the tussle
            
        Returns:
            The modified tussle cost
        """
        return base_cost
    
    def modify_card_cost(self, card: "Card", base_cost: int, 
                        game_state: "GameState", controller: "Player") -> int:
        """
        Modify the cost of playing a card.
        
        Args:
            card: The card being played
            base_cost: The printed cost of the card
            game_state: The current game state
            controller: The player playing the card
            
        Returns:
            The modified card cost
        """
        return base_cost


class ProtectionEffect(ContinuousEffect):
    """
    Special continuous effect that grants protection from other effects.
    
    Examples: Knight (opponent's effects don't affect), Beary (Knight's effects don't affect)
    
    Protection effects:
    - Prevent certain effects from targeting or affecting the card
    - Don't prevent tussle damage (damage is not an "effect")
    - Are checked before other effects apply
    """
    
    def __init__(self, source_card: "Card", protects_from: Optional[str] = None):
        super().__init__(source_card)
        self.protects_from = protects_from  # e.g., "opponent", "Knight"
    
    def is_protected_from(self, effect: BaseEffect, game_state: "GameState") -> bool:
        """
        Check if this card is protected from the given effect.
        
        Args:
            effect: The effect trying to affect this card
            game_state: The current game state
            
        Returns:
            True if protected from this effect
        """
        return False
