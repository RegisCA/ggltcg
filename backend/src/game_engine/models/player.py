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
        cc: Current Command Counters
        hand: List of cards in hand
        in_play: List of cards in play
        sleep_zone: List of cards in sleep zone
        direct_attacks_this_turn: Count of direct attacks made this turn
    """
    player_id: str
    name: str
    cc: int = 0
    hand: List[Card] = field(default_factory=list)
    in_play: List[Card] = field(default_factory=list)
    sleep_zone: List[Card] = field(default_factory=list)
    direct_attacks_this_turn: int = 0
    
    def gain_cc(self, amount: int):
        """
        Gain CC, respecting the maximum cap of 7.
        
        Args:
            amount: Amount of CC to gain
        """
        self.cc = min(self.cc + amount, 7)
    
    def spend_cc(self, amount: int) -> bool:
        """
        Attempt to spend CC.
        
        Args:
            amount: Amount of CC to spend
            
        Returns:
            True if successful, False if insufficient CC
        """
        if self.cc >= amount:
            self.cc -= amount
            return True
        return False
    
    def has_cc(self, amount: int) -> bool:
        """Check if player has at least the specified amount of CC."""
        return self.cc >= amount
    
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
        elif from_zone == Zone.SLEEP:
            self.sleep_zone.remove(card)
        
        # Reset modifications when leaving IN_PLAY or going to SLEEP
        # This covers: IN_PLAY→SLEEP, IN_PLAY→HAND, HAND→SLEEP
        if from_zone == Zone.IN_PLAY or to_zone == Zone.SLEEP:
            card.reset_modifications()
        
        card.zone = to_zone
        
        # Add to destination zone
        if to_zone == Zone.HAND:
            self.hand.append(card)
        elif to_zone == Zone.IN_PLAY:
            self.in_play.append(card)
        elif to_zone == Zone.SLEEP:
            self.sleep_zone.append(card)
    
    def sleep_card(self, card: Card):
        """
        Move a card to sleep zone from its current zone.
        
        Args:
            card: The card to sleep
        """
        if card in self.hand:
            self.move_card(card, Zone.HAND, Zone.SLEEP)
        elif card in self.in_play:
            self.move_card(card, Zone.IN_PLAY, Zone.SLEEP)
    
    def unsleep_card(self, card: Card):
        """
        Return a card from sleep zone to hand.
        
        Args:
            card: The card to unsleep
        """
        if card in self.sleep_zone:
            self.move_card(card, Zone.SLEEP, Zone.HAND)
    
    def has_cards_in_play(self) -> bool:
        """Check if player has any Toys in play."""
        return len(self.in_play) > 0
    
    def all_cards_sleeped(self) -> bool:
        """Check if all player's cards are in sleep zone (loss condition)."""
        total_cards = len(self.hand) + len(self.in_play) + len(self.sleep_zone)
        return total_cards == len(self.sleep_zone) and total_cards > 0
    
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
            "cc": self.cc,
            "hand": [card.to_dict() for card in self.hand] if reveal_hand else [],
            "hand_count": len(self.hand),
            "in_play": [card.to_dict() for card in self.in_play],
            "sleep_zone": [card.to_dict() for card in self.sleep_zone],
            "direct_attacks_this_turn": self.direct_attacks_this_turn,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """Deserialize player from dictionary."""
        from .card import Card
        
        return cls(
            player_id=data["player_id"],
            name=data["name"],
            cc=data["cc"],
            hand=[Card.from_dict(c) for c in data.get("hand", [])],
            in_play=[Card.from_dict(c) for c in data["in_play"]],
            sleep_zone=[Card.from_dict(c) for c in data["sleep_zone"]],
            direct_attacks_this_turn=data.get("direct_attacks_this_turn", 0),
        )
