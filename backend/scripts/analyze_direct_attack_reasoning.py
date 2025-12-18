"""
Analyze AI reasoning logs for "direct attack" patterns.

This script queries the database for AI decision logs that mention
"direct attack" in their reasoning field and displays them for analysis.
"""

import sys
import os
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from api.database import get_db
from api.db_models import AIDecisionLogModel
from sqlalchemy import func


def main():
    """Query and display AI logs mentioning direct attacks."""
    db = next(get_db())
    
    try:
        # Query for logs containing "direct attack" (case-insensitive)
        logs = db.query(AIDecisionLogModel).filter(
            func.lower(AIDecisionLogModel.reasoning).like('%direct attack%')
        ).order_by(AIDecisionLogModel.created_at.desc()).all()
        
        print(f"\n{'='*80}")
        print(f"Found {len(logs)} AI decision logs mentioning 'direct attack'")
        print(f"{'='*80}\n")
        
        if not logs:
            print("No logs found containing 'direct attack' in reasoning.")
            return
        
        # Group by game for better readability
        games = {}
        for log in logs:
            game_id = str(log.game_id)
            if game_id not in games:
                games[game_id] = []
            games[game_id].append(log)
        
        # Display each game's logs
        for game_id, game_logs in games.items():
            print(f"\n{'='*80}")
            print(f"Game ID: {game_id}")
            print(f"{'='*80}")
            
            for log in sorted(game_logs, key=lambda x: x.turn_number):
                print(f"\n{'─'*80}")
                print(f"Turn {log.turn_number} | Player: {log.player_id}")
                print(f"Model: {log.model_name} | Action #{log.action_number}")
                print(f"Created: {log.created_at}")
                print(f"{'─'*80}")
                print(f"\nREASONING:")
                print(f"{log.reasoning}\n")
                
                # Extract and show just the valid actions list from prompt
                prompt = log.prompt
                if "Valid Actions:" in prompt:
                    actions_start = prompt.find("Valid Actions:")
                    actions_section = prompt[actions_start:actions_start+2000]
                    
                    # Find where actions list ends
                    if "\n\n" in actions_section:
                        actions_section = actions_section[:actions_section.find("\n\n", 100)]
                    
                    print("AVAILABLE ACTIONS (snippet):")
                    print(actions_section[:1000])
                    if len(actions_section) > 1000:
                        print("... (truncated)")
                
                print()
        
        # Summary statistics
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total logs: {len(logs)}")
        print(f"Unique games: {len(games)}")
        
        # Count by model
        model_counts = {}
        for log in logs:
            model = log.model_name
            model_counts[model] = model_counts.get(model, 0) + 1
        
        print(f"\nBy model:")
        for model, count in sorted(model_counts.items()):
            print(f"  {model}: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
