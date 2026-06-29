"""Game state model for GGLTCG game engine."""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from .player import Player
from .card import Card, Zone


class Phase(Enum):
    """Turn phases."""
    START = "Start"
    MAIN = "Main"
    END = "End"


@dataclass
class TurnChargeRecord:
    """
    Charge tracking for a single turn.

    Records Charge state at the start and end of a turn, along with
    Charge gained and spent during the turn.

    Note: charge_spent is calculated as: charge_start + charge_gained - charge_end
    This captures all spending without needing to track individual actions.
    """
    turn: int
    player_id: str
    charge_start: int  # Charge at start of turn (BEFORE any gains)
    charge_gained: int  # Charge gained during turn (from effects, start of turn, etc.)
    charge_spent: int  # Charge spent during turn (calculated at end)
    charge_end: int  # Charge at end of turn

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "turn": self.turn,
            "player_id": self.player_id,
            "charge_start": self.charge_start,
            "charge_gained": self.charge_gained,
            "charge_spent": self.charge_spent,
            "charge_end": self.charge_end,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TurnChargeRecord':
        """Create from dictionary."""
        return cls(
            turn=data["turn"],
            player_id=data["player_id"],
            charge_start=data["charge_start"],
            charge_gained=data["charge_gained"],
            charge_spent=data["charge_spent"],
            charge_end=data["charge_end"],
        )


@dataclass
class GameState:
    """
    Represents the complete state of a game.

    Attributes:
        game_id: Unique identifier for this game
        players: Dictionary mapping player_id to Player objects
        active_player_id: ID of the player whose turn it is
        turn_number: Current turn number (starts at 1)
        phase: Current phase of the turn
        first_player_id: ID of the player who went first
        winner_id: ID of the winning player (None if game ongoing)
        game_log: List of game events for history
        play_by_play: List of detailed action records for end-game summary
        starting_decks: Dict mapping player_id to list of card names at game start
        charge_history: List of Charge tracking records per turn
    """
    game_id: str
    players: Dict[str, Player]
    active_player_id: str
    turn_number: int = 1
    phase: Phase = Phase.START
    first_player_id: str = ""
    winner_id: Optional[str] = None
    game_log: List[str] = field(default_factory=list)
    play_by_play: List[Dict[str, Any]] = field(default_factory=list)
    starting_decks: Dict[str, List[str]] = field(default_factory=dict)
    charge_history: List[TurnChargeRecord] = field(default_factory=list)
    # Internal: Charge tracking for current turn (not serialized).
    # Note: If GameState is serialized mid-turn and deserialized,
    # these fields reset to defaults. Mid-turn serialization is not
    # supported for Charge tracking - finalize_turn_charge_tracking() must
    # be called before serialization to preserve accurate Charge data.
    _turn_charge_snapshot: int = field(default=0, repr=False)
    _turn_charge_gained: int = field(default=0, repr=False)

    def get_active_player(self) -> Player:
        """Get the active player object."""
        return self.players[self.active_player_id]

    def get_opponent(self, player_id: str) -> Player:
        """
        Get the opponent of the specified player.

        Args:
            player_id: ID of the player

        Returns:
            The opponent Player object
        """
        for pid, player in self.players.items():
            if pid != player_id:
                return player
        raise ValueError("Could not find opponent")

    def get_opponent_of_active(self) -> Player:
        """Get the opponent of the active player."""
        return self.get_opponent(self.active_player_id)

    def is_first_turn(self) -> bool:
        """Check if this is the first turn of the game."""
        return self.turn_number == 1

    def log_event(self, message: str):
        """Add an event to the game log."""
        self.game_log.append(f"Turn {self.turn_number} ({self.phase.value}): {message}")

    # ========================================================================
    # CHARGE TRACKING (simple design - only 3 method calls per turn)
    # ========================================================================

    def start_turn_charge_tracking(self) -> None:
        """
        Initialize Charge tracking at turn start (BEFORE any Charge gains).

        Called once at the very beginning of start_turn().
        """
        player = self.get_active_player()
        self._turn_charge_snapshot = player.charge
        self._turn_charge_gained = 0

    def record_charge_gained(self, amount: int) -> None:
        """
        Record Charge gained during the current turn.

        Called when Charge is gained from:
        - Turn start (2 or 4 Charge)
        - Effects (e.g., Belchaletta's +2 Charge)

        Args:
            amount: Amount of Charge gained
        """
        self._turn_charge_gained += amount

    def finalize_turn_charge_tracking(self) -> None:
        """
        Record Charge tracking for the completed turn.

        Called at end of turn. Calculates charge_spent from the difference:
        charge_spent = charge_start + charge_gained - charge_end
        """
        # Idempotency guard: victory detection can finalize Charge mid-turn,
        # and caller paths may still finalize again.
        if any(
            record.turn == self.turn_number and record.player_id == self.active_player_id
            for record in self.charge_history
        ):
            return

        player = self.get_active_player()
        charge_end = player.charge
        charge_start = self._turn_charge_snapshot
        charge_gained = self._turn_charge_gained
        # Simple math: what we started with + what we gained - what we have = what we spent
        charge_spent = max(0, charge_start + charge_gained - charge_end)

        record = TurnChargeRecord(
            turn=self.turn_number,
            player_id=self.active_player_id,
            charge_start=charge_start,
            charge_gained=charge_gained,
            charge_spent=charge_spent,
            charge_end=charge_end,
        )
        self.charge_history.append(record)

    def get_charge_efficiency(self, player_id: str) -> Dict[str, Any]:
        """
        Calculate Charge efficiency metrics for a player.

        Args:
            player_id: Player to calculate efficiency for

        Returns:
            Dictionary with:
            - total_charge_spent: Total Charge spent by this player
            - total_charge_gained: Total Charge gained by this player
            - opponent_cards_broken: Number of opponent cards in break zone
            - charge_per_card_broken: Charge efficiency (None if 0 cards broken)

        Note: opponent_cards_broken counts ALL cards in opponent's break zone,
        regardless of how they got there. This includes cards the opponent
        broke themselves (e.g., Ballaber alternative cost, played Actions).
        For more precise metrics, analyze individual game events.
        """
        # Calculate totals from Charge history
        total_charge_spent = sum(
            record.charge_spent
            for record in self.charge_history
            if record.player_id == player_id
        )
        total_charge_gained = sum(
            record.charge_gained
            for record in self.charge_history
            if record.player_id == player_id
        )

        # Count opponent cards broken
        opponent = self.get_opponent(player_id)
        opponent_cards_broken = len(opponent.break_zone)

        # Calculate efficiency
        charge_per_card_broken = None
        if opponent_cards_broken > 0:
            charge_per_card_broken = round(total_charge_spent / opponent_cards_broken, 2)

        return {
            "total_charge_spent": total_charge_spent,
            "total_charge_gained": total_charge_gained,
            "opponent_cards_broken": opponent_cards_broken,
            "charge_per_card_broken": charge_per_card_broken,
        }

    # ========================================================================
    # PLAY-BY-PLAY
    # ========================================================================

    def add_play_by_play(
        self,
        player_name: str,
        action_type: str,
        description: str,
        reasoning: Optional[str] = None,
        ai_endpoint: Optional[str] = None,
    ):
        """
        Add a detailed action record to the play-by-play history.

        Args:
            player_name: Name of the player who took the action
            action_type: Type of action (play_card, tussle, end_turn, etc.)
            description: Human-readable description of the action
            reasoning: Optional AI reasoning for the action
            ai_endpoint: Optional AI endpoint name if this was an AI action
        """
        entry = {
            "turn": self.turn_number,
            "player": player_name,
            "action_type": action_type,
            "description": description,
        }

        if reasoning:
            entry["reasoning"] = reasoning
        if ai_endpoint:
            entry["ai_endpoint"] = ai_endpoint

        self.play_by_play.append(entry)

    def check_victory(self) -> Optional[str]:
        """
        Check if any player has won the game.

        NOTE: This does NOT add to play-by-play anymore.
        The caller should add the victory message after logging the winning action.

        Returns:
            Player ID of winner if game is won, None otherwise
        """
        # If game is already over, don't check again (prevents duplicate entries)
        if self.winner_id is not None:
            return self.winner_id

        def _charge_recorded_for_current_turn() -> bool:
            return any(
                (r.turn == self.turn_number and r.player_id == self.active_player_id)
                for r in self.charge_history
            )

        for player_id, player in self.players.items():
            opponent = self.get_opponent(player_id)
            if opponent.all_cards_broken():
                # If the game ends mid-turn, we may never reach end_turn(), so
                # finalize Charge tracking now to avoid missing the final turn.
                if not _charge_recorded_for_current_turn():
                    try:
                        self.finalize_turn_charge_tracking()
                    except Exception:
                        # Charge tracking should never block victory detection.
                        pass
                self.winner_id = player_id
                victory_message = f"{player.name} wins! All opponent's cards are broken."
                self.log_event(victory_message)
                # Don't add to play-by-play here - let the caller do it after the action
                return player_id
        return None

    def get_all_cards_in_play(self) -> List[Card]:
        """Get all cards currently in play across both players."""
        cards = []
        for player in self.players.values():
            cards.extend(player.in_play)
        return cards

    def get_cards_in_play(self, player: Player) -> List[Card]:
        """Get all cards in play for a specific player."""
        return list(player.in_play)

    def get_card_controller(self, card: Card) -> Optional[Player]:
        """
        Get the player who currently controls a card.

        Args:
            card: Card to check

        Returns:
            Player controlling the card, or None if not in play
        """
        # First check if card is in play
        for player in self.players.values():
            if card in player.in_play:
                return player

        # Fallback: use card's controller field (for action cards or cards not yet in play)
        if card.controller:
            return self.players.get(card.controller)

        return None

    def get_card_owner(self, card: Card) -> Optional[Player]:
        """
        Get the player who owns a card (from their original deck).

        Args:
            card: Card to check

        Returns:
            Player who owns the card, or None if not found
        """
        # Check the card's owner field directly
        if card.owner:
            return self.players.get(card.owner)

        # Fallback: search through all zones (for cards without owner set)
        for player in self.players.values():
            if card in player.hand or card in player.in_play or card in player.break_zone:
                return player
        return None

    def break_card(self, card: Card, was_in_play: bool) -> None:
        """
        Move a card to its owner's break zone.

        Args:
            card: Card to break
            was_in_play: Whether the card was in play (affects triggers)
        """
        owner = self.get_card_owner(card)
        if owner:
            owner.break_card(card)

    def fix_card(self, card: Card, player: Player) -> None:
        """
        Return a card from break zone to hand.

        Args:
            card: Card to fix
            player: Player to return card to
        """
        player.fix_card(card)

    def return_card_to_hand(self, card: Card, owner: Player) -> None:
        """
        Return a card from play to owner's hand.

        Used by Toynado effect.

        Args:
            card: Card to return
            owner: Owner to return card to
        """
        # Update card state
        card.zone = Zone.HAND
        card.controller = owner.player_id  # Reset controller to owner
        card.reset_modifications()

        # Add to owner's hand
        owner.hand.append(card)

    def change_control(self, card: Card, new_controller: Player) -> None:
        """
        Change control of a card to a different player.

        Used by Twist effect. Ownership remains unchanged.

        Args:
            card: Card to change control of
            new_controller: Player to give control to
        """
        # Remove from current controller
        current_controller = self.get_card_controller(card)
        if not current_controller:
            return

        # Remove from old controller's in_play
        if card in current_controller.in_play:
            current_controller.in_play.remove(card)

        # Update controller field
        card.controller = new_controller.player_id

        # Add to new controller
        new_controller.in_play.append(card)

        self.log_event(f"Control of {card.name} changed from {current_controller.name} to {new_controller.name}")

    def is_protected_from_effect(self, card: Card, effect: Any) -> bool:
        """
        Check if a card is protected from an effect.

        Protection can come from:
        1. The card's own protection effects (e.g., Beary's opponent_immunity)
        2. Team-wide protection from other cards (e.g., Sock Sorcerer)

        Args:
            card: Card being targeted
            effect: Effect trying to affect the card

        Returns:
            True if protected
        """
        from ..rules.effects import EffectRegistry
        from ..rules.effects.base_effect import ProtectionEffect
        from ..rules.effects.continuous_effects import TeamOpponentImmunityEffect

        # Check card's own protection effects
        card_effects = EffectRegistry.get_effects(card)
        for card_effect in card_effects:
            if isinstance(card_effect, ProtectionEffect):
                if card_effect.is_protected_from(effect, self):
                    return True

        # Check team-wide protection from other cards in play
        for player in self.players.values():
            for protector in player.in_play:
                protector_effects = EffectRegistry.get_effects(protector)
                for protector_effect in protector_effects:
                    if isinstance(protector_effect, TeamOpponentImmunityEffect):
                        if protector_effect.is_card_protected(card, effect, self):
                            return True

        return False

    def find_card_by_id(self, card_id: str) -> Optional[Card]:
        """
        Find a card by its unique ID across all zones and players.

        Args:
            card_id: Unique card instance ID

        Returns:
            Card if found, None otherwise
        """
        for player in self.players.values():
            # Search in hand
            for card in player.hand:
                if card.id == card_id:
                    return card
            # Search in play
            for card in player.in_play:
                if card.id == card_id:
                    return card
            # Search in break zone
            for card in player.break_zone:
                if card.id == card_id:
                    return card
        return None

    def to_dict(self, requesting_player_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Serialize game state to dictionary for API responses.

        Args:
            requesting_player_id: If provided, reveal that player's hand

        Returns:
            Dictionary representation of game state
        """
        return {
            "game_id": self.game_id,
            "turn_number": self.turn_number,
            "phase": self.phase.value,
            "active_player_id": self.active_player_id,
            "first_player_id": self.first_player_id,
            "winner_id": self.winner_id,
            "players": {
                pid: player.to_dict(reveal_hand=(pid == requesting_player_id))
                for pid, player in self.players.items()
            },
            "game_log": self.game_log[-20:],  # Last 20 events only
            "play_by_play": self.play_by_play,  # Full play-by-play for victory screen
            "charge_history": [record.to_dict() for record in self.charge_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Deserialize game state from dictionary."""
        charge_history = [
            TurnChargeRecord.from_dict(record)
            for record in data.get("charge_history", [])
        ]
        return cls(
            game_id=data["game_id"],
            players={
                pid: Player.from_dict(pdata)
                for pid, pdata in data["players"].items()
            },
            active_player_id=data["active_player_id"],
            turn_number=data["turn_number"],
            phase=Phase(data["phase"]),
            first_player_id=data["first_player_id"],
            winner_id=data.get("winner_id"),
            game_log=data.get("game_log", []),
            play_by_play=data.get("play_by_play", []),
            charge_history=charge_history,
        )
