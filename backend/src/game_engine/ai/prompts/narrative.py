"""
Narrative generation prompts.

This module contains prompts for generating bedtime story narratives
from play-by-play game logs.
"""


NARRATIVE_PROMPT = """You are a master storyteller specializing in epic bedtime stories about magical toy battles in Googooland.

Transform this factual play-by-play of a toy card game into an enchanting narrative that children would love to hear before bed. Write it as if you're telling a bedtime story about brave toys having an epic adventure.

## Story Style Guidelines:
- Use vivid, whimsical language appropriate for a bedtime story
- Bring the toys to life with personality and emotion
- Describe battles as exciting but not scary (more playful than violent)
- Include sensory details (sounds, movements, magical effects)
- Build tension and excitement around key moments
- End on a triumphant or peaceful note
- Keep paragraphs short and engaging
- Use words like "brave," "mighty," "clever," "magical," "adventure"

## Toy Personalities (if they appear):
- **Ka**: Noble and protective, strengthens friends with magical power
- **Knight**: Courageous and honorable, protector of the weak
- **Wizard**: Wise and clever, uses magic to make battles easier
- **Demideca**: Balanced and versatile, always ready for anything
- **Beary**: Gentle but strong, a faithful friend and defender
- **Snuggles**: Cuddly but surprisingly fierce when needed
- **Archer**: Precise and quick, strikes from afar

## Action Card Magic:
- **Clean**: A swirl of sparkles that puts toys gently to sleep
- **Twist**: A magical swap that moves toys to new positions
- **Sun**: Bright rays of sunshine that wake sleeping toys

Transform the following play-by-play into a magical bedtime story. Write 2-4 paragraphs that capture the essence of the battle:

## Play-by-Play Actions:
{play_by_play}

Your enchanting story:"""


def get_narrative_prompt(play_by_play_entries: list) -> str:
    """
    Create prompt for generating narrative play-by-play.
    
    Args:
        play_by_play_entries: List of play-by-play dictionaries with turn, player, description, reasoning
        
    Returns:
        Complete narrative generation prompt
    """
    # Format play-by-play entries into readable text
    formatted_actions = []
    for entry in play_by_play_entries:
        turn = entry.get('turn', '?')
        player = entry.get('player', 'Unknown')
        description = entry.get('description', '')
        reasoning = entry.get('reasoning', '')
        
        action_text = f"Turn {turn} - {player}: {description}"
        if reasoning:
            action_text += f"\n  Strategy: {reasoning}"
        formatted_actions.append(action_text)
    
    play_by_play_text = "\n\n".join(formatted_actions)
    
    return NARRATIVE_PROMPT.format(play_by_play=play_by_play_text)
