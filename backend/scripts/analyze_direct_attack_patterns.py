"""
Analyze AI reasoning patterns for direct attack decisions.

This script categorizes the reasoning into patterns to help improve the system prompt.
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


def categorize_reasoning(reasoning):
    """Categorize the reasoning into patterns."""
    reasoning_lower = reasoning.lower()
    
    categories = []
    
    # Pattern: Recognizes opportunity for direct attack
    if "opponent has no toys" in reasoning_lower or "opponent has no cards in play" in reasoning_lower:
        categories.append("RECOGNIZES_OPPORTUNITY")
    
    # Pattern: Performs direct attack
    if "direct attack" in reasoning_lower and any(word in reasoning_lower for word in ["will", "can", "should"]):
        categories.append("PERFORMS_DIRECT_ATTACK")
    
    # Pattern: Chooses not to direct attack
    if ("cannot direct attack" in reasoning_lower or 
        "direct attacks are not" in reasoning_lower or
        "direct attacking now is not ideal" in reasoning_lower):
        categories.append("DECLINES_DIRECT_ATTACK")
    
    # Pattern: Prioritizes board state over direct attack
    if any(phrase in reasoning_lower for phrase in [
        "build board", "board presence", "board state", 
        "establish a toy", "playing", "not yet possible"
    ]) and "direct attack" in reasoning_lower:
        categories.append("PRIORITIZES_BOARD")
    
    # Pattern: Direct attack for pressure/win condition
    if any(phrase in reasoning_lower for phrase in [
        "pressure", "win condition", "closer to victory", 
        "closer to winning", "closer to defeat", "progress towards"
    ]):
        categories.append("STRATEGIC_PRESSURE")
    
    # Pattern: Direct attack to win game
    if "win the game" in reasoning_lower or "winning the game" in reasoning_lower:
        categories.append("WIN_CONDITION")
    
    # Pattern: Resource constraint (not enough CC)
    if "0 cc" in reasoning_lower or "1 cc" in reasoning_lower or "cannot afford" in reasoning_lower:
        categories.append("RESOURCE_CONSTRAINT")
    
    return categories


def main():
    """Analyze patterns in direct attack reasoning."""
    db = next(get_db())
    
    try:
        # Query for logs containing "direct attack"
        logs = db.query(AIDecisionLogModel).filter(
            func.lower(AIDecisionLogModel.reasoning).like('%direct attack%')
        ).order_by(AIDecisionLogModel.created_at.desc()).all()
        
        print(f"\n{'='*80}")
        print(f"PATTERN ANALYSIS: {len(logs)} logs mentioning 'direct attack'")
        print(f"{'='*80}\n")
        
        # Categorize all logs
        pattern_counts = {}
        pattern_examples = {}
        
        for log in logs:
            categories = categorize_reasoning(log.reasoning)
            
            for category in categories:
                pattern_counts[category] = pattern_counts.get(category, 0) + 1
                
                # Store first 2 examples of each pattern
                if category not in pattern_examples:
                    pattern_examples[category] = []
                if len(pattern_examples[category]) < 2:
                    pattern_examples[category].append({
                        'reasoning': log.reasoning,
                        'turn': log.turn_number,
                        'model': log.model_name
                    })
        
        # Display pattern summary
        print("PATTERN FREQUENCY:")
        print("─" * 80)
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{pattern:30s}: {count:2d} occurrences")
        
        # Display examples for each pattern
        print(f"\n{'='*80}")
        print("PATTERN EXAMPLES")
        print(f"{'='*80}\n")
        
        for pattern in sorted(pattern_counts.keys()):
            print(f"\n{pattern}")
            print("─" * 80)
            
            for i, example in enumerate(pattern_examples[pattern], 1):
                print(f"\nExample {i} (Turn {example['turn']}, {example['model']}):")
                print(f"{example['reasoning']}\n")
        
        # Key insights
        print(f"\n{'='*80}")
        print("KEY INSIGHTS")
        print(f"{'='*80}\n")
        
        performs_attack = pattern_counts.get("PERFORMS_DIRECT_ATTACK", 0)
        declines_attack = pattern_counts.get("DECLINES_DIRECT_ATTACK", 0)
        recognizes_opp = pattern_counts.get("RECOGNIZES_OPPORTUNITY", 0)
        prioritizes_board = pattern_counts.get("PRIORITIZES_BOARD", 0)
        
        print(f"✅ Recognizes opportunity: {recognizes_opp}/{len(logs)} ({recognizes_opp/len(logs)*100:.1f}%)")
        print(f"✅ Performs direct attack: {performs_attack}/{len(logs)} ({performs_attack/len(logs)*100:.1f}%)")
        print(f"⚠️  Declines direct attack: {declines_attack}/{len(logs)} ({declines_attack/len(logs)*100:.1f}%)")
        print(f"⚠️  Prioritizes board over attack: {prioritizes_board}/{len(logs)} ({prioritizes_board/len(logs)*100:.1f}%)")
        
        print(f"\nRECOMMENDATIONS:")
        print("─" * 80)
        
        if declines_attack > 0 or prioritizes_board > 0:
            print("\n🎯 Issue: AI sometimes declines direct attacks or prioritizes board presence")
            print("\nSuggested system prompt improvements:")
            print("1. Add explicit guidance that when opponent has no toys in play:")
            print("   - Direct attacks should be strongly preferred (costs 2 CC)")
            print("   - Only skip if you need to save CC for critical next turn setup")
            print("   - Direct attacks remove cards from opponent's hand (reduces options)")
            print("   - You can do 2 direct attacks per turn (maximize pressure)")
            print("\n2. Clarify the value proposition:")
            print("   - Direct attack = guaranteed progress toward win condition")
            print("   - Building board = potential future value (less certain)")
            print("   - Exception: If you can play a toy AND still direct attack, do both")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
