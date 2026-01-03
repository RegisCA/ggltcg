"""
Dynamic Effect Guidance Loader

Scans cards in play and generates effect guidance for the AI based on
the actual effects present in the current game state. This keeps the prompt
compact by only including relevant effect information.
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...card import Card

from .effect_metadata import get_effect_metadata, extract_unique_effect_types


def generate_effect_guidance(
    player_cards: List["Card"],
    opponent_cards: List["Card"]
) -> str:
    """
    Generate effect guidance based on cards currently in play.
    
    Args:
        player_cards: Cards in player's hand + in_play zones
        opponent_cards: Cards in opponent's hand + in_play zones
    
    Returns:
        Formatted effect guidance string for the AI prompt
    """
    all_cards = player_cards + opponent_cards
    
    # Extract unique effect types
    effect_types = extract_unique_effect_types(all_cards)
    
    if not effect_types:
        return ""
    
    # Group effects by classification
    continuous_effects = []
    triggered_effects = []
    activated_effects = []
    passive_effects = []
    temporary_effects = []
    
    for effect_def in effect_types:
        metadata = get_effect_metadata(effect_def)
        if not metadata:
            continue
        
        if metadata.classification == "continuous":
            continuous_effects.append(metadata)
        elif metadata.classification == "triggered":
            triggered_effects.append(metadata)
        elif metadata.classification == "activated":
            activated_effects.append(metadata)
        elif metadata.classification == "passive":
            passive_effects.append(metadata)
        elif metadata.classification == "temporary":
            temporary_effects.append(metadata)
    
    # Build guidance sections
    sections = []
    
    if continuous_effects:
        section = "**Continuous Effects** (always active while in play):\n"
        section += "\n".join(f"- {e.to_guidance_text()}" for e in continuous_effects)
        sections.append(section)
    
    if triggered_effects:
        section = "**Triggered Effects** (automatic on game events):\n"
        section += "\n".join(f"- {e.to_guidance_text()}" for e in triggered_effects)
        sections.append(section)
    
    if activated_effects:
        section = "**Activated Abilities** (require action_type: activate_ability):\n"
        section += "\n".join(f"- {e.to_guidance_text()}" for e in activated_effects)
        sections.append(section)
    
    if passive_effects:
        section = "**Passive Effects** (trigger on play, no separate action needed):\n"
        section += "\n".join(f"- {e.to_guidance_text()}" for e in passive_effects)
        sections.append(section)
    
    if temporary_effects:
        section = "**Temporary Effects** (last this turn only):\n"
        section += "\n".join(f"- {e.to_guidance_text()}" for e in temporary_effects)
        sections.append(section)
    
    if not sections:
        return ""
    
    guidance = "## EFFECT MECHANICS (for cards in this game)\n\n"
    guidance += "\n\n".join(sections)
    
    return guidance


def get_cards_with_activated_abilities(cards: List["Card"]) -> List[str]:
    """
    Get list of card names that have activated abilities.
    
    Args:
        cards: List of Card objects
    
    Returns:
        List of card names with activated abilities
    """
    activated_cards = []
    
    for card in cards:
        if not hasattr(card, 'effect_definitions') or not card.effect_definitions:
            continue
        
        effects = card.effect_definitions.split(";")
        for effect in effects:
            effect = effect.strip()
            metadata = get_effect_metadata(effect)
            if metadata and metadata.classification == "activated":
                activated_cards.append(card.name)
                break
    
    return activated_cards
