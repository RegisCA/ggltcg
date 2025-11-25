"""
Check if Copy cards have their effects properly applied.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.game_service import GameService
from game_engine.rules.effects import EffectRegistry

def check_copy_effects(game_id: str):
    """Check if Copy cards have their effects."""
    cards_csv_path = Path(__file__).parent / "data" / "cards.csv"
    service = GameService(cards_csv_path=str(cards_csv_path))
    engine = service.get_game(game_id)
    
    if not engine:
        print(f"Game {game_id} not found")
        return
    
    print("="*70)
    print("CHECKING COPY EFFECTS")
    print("="*70)
    
    for player_id, player in engine.game_state.players.items():
        print(f'\n{player.name} ({player_id}):')
        
        for card in player.in_play:
            effects = EffectRegistry.get_effects(card)
            print(f'\n  {card.name}:')
            print(f'    Has _copied_effects attr: {hasattr(card, "_copied_effects")}')
            if hasattr(card, '_copied_effects'):
                print(f'    _copied_effects: {[type(e).__name__ for e in card._copied_effects]}')
            print(f'    EffectRegistry returns: {[type(e).__name__ for e in effects]}')
            
            # For toys, show calculated stats
            if card.card_type.value == 'Toy':
                speed = engine.get_card_stat(card, 'speed')
                strength = engine.get_card_stat(card, 'strength')
                stamina = engine.get_card_stat(card, 'stamina')
                print(f'    Calculated stats: SPD={speed} STR={strength} STA={stamina}')
                print(f'    Base stats: SPD={card.speed} STR={card.strength} STA={card.stamina}')


if __name__ == '__main__':
    game_id = '8592a7ee-d0a7-47e6-9f7f-8324bda06514'
    if len(sys.argv) > 1:
        game_id = sys.argv[1]
    
    check_copy_effects(game_id)
