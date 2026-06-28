"""Player model for GGLTCG game engine."""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from .card import Card, Zone


@dataclass
class Player:
    """
    Represents a player in the game.

    Attributes:
        player_id: Unique identifier for the player
        name: Player's display name
        charge: Current Charge
        hand: List of cards in hand
        in_play: List of cards in play
        break_zone: List of cards in break zone
        direct_attacks_this_turn: Count of direct attacks made this turn
    """
    player_id: str
    name: str
    charge: int = 0
    hand: List[Card] = field(default_factory=list)
    in_play: List[Card] = field(default_factory=list)
    break_zone: List[Card] = field(default_factory=list)
    direct_attacks_this_turn: int = 0

    def gain_charge(self, amount: int):
        """
        Gain Charge, respecting the maximum cap of 7.

        Args:
            amount: Amount of Charge to gain
        """
        self.charge = min(self.charge + amount, 7)

    def spend_charge(self, amount: int) -> bool:
        """
        Attempt to spend Charge.

        Args:
            amount: Amount of Charge to spend

        Returns:
            True if successful, False if insufficient Charge
        """
        if self.charge >= amount:
            self.charge -= amount
            return True
        return False

    def has_charge(self, amount: int) -> bool:
        """Check if player has at least the specified amount of Charge."""
        return self.charge >= amount

    def move_card(self, card: Card, from_zone: Zone, to_zone: Zone):
        """
        Move a card from one zone to another.

        Args:
            card: The card to move
            from_zone: Source zone
            to_zone: Destination zone
        """
        # Remove from source zone
        if from_zone == Zone.HAND:
            self.hand.remove(card)
        elif from_zone == Zone.IN_PLAY:
            self.in_play.remove(card)
        elif from_zone == Zone.BREAK:
            self.break_zone.remove(card)

        # Reset modifications when leaving IN_PLAY or going to BREAK
        # This covers: IN_PLAY→BREAK, IN_PLAY→HAND, HAND→BREAK
        if from_zone == Zone.IN_PLAY or to_zone == Zone.BREAK:
            card.reset_modifications()

        card.zone = to_zone

        # Add to destination zone
        if to_zone == Zone.HAND:
            self.hand.append(card)
        elif to_zone == Zone.IN_PLAY:
            self.in_play.append(card)
        elif to_zone == Zone.BREAK:
            self.break_zone.append(card)

    def break_card(self, card: Card):
        """
        Move a card to break zone from its current zone.

        Args:
            card: The card to break
        """
        if card in self.hand:
            self.move_card(card, Zone.HAND, Zone.BREAK)
        elif card in self.in_play:
            self.move_card(card, Zone.IN_PLAY, Zone.BREAK)

    def fix_card(self, card: Card):
        """
        Return a card from break zone to hand.

        Args:
            card: The card to fix
        """
        if card in self.break_zone:
            self.move_card(card, Zone.BREAK, Zone.HAND)

    def has_cards_in_play(self) -> bool:
        """Check if player has any Toys in play."""
        return len(self.in_play) > 0

    def all_cards_broken(self) -> bool:
        """Check if all player's cards are in break zone (loss condition)."""
        total_cards = len(self.hand) + len(self.in_play) + len(self.break_zone)
        return total_cards == len(self.break_zone) and total_cards > 0

    def reset_turn_counters(self):
        """Reset turn-specific counters at end of turn."""
        self.direct_attacks_this_turn = 0

    def to_dict(self, reveal_hand: bool = False) -> Dict[str, Any]:
        """
        Serialize player to dictionary for API responses.

        Args:
            reveal_hand: Whether to include hand cards (for owner) or just count

        Returns:
            Dictionary representation of player
        """
        return {
            "player_id": self.player_id,
            "name": self.name,
            "charge": self.charge,
            "hand": [card.to_dict() for card in self.hand] if reveal_hand else [],
            "hand_count": len(self.hand),
            "in_play": [card.to_dict() for card in self.in_play],
            "break_zone": [card.to_dict() for card in self.break_zone],
            "direct_attacks_this_turn": self.direct_attacks_this_turn,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """Deserialize player from dictionary."""
        from .card import Card

        return cls(
            player_id=data["player_id"],
            name=data["name"],
            charge=data["charge"],
            hand=[Card.from_dict(c) for c in data.get("hand", [])],
            in_play=[Card.from_dict(c) for c in data["in_play"]],
            break_zone=[Card.from_dict(c) for c in data["break_zone"]],
            direct_attacks_this_turn=data.get("direct_attacks_this_turn", 0),
        )
