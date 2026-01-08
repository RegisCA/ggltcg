#!/usr/bin/env python3
"""
Diagnostic script for testing simulation runner.

Usage:
    cd backend
    python scripts/test_simulation.py

Output goes to: /tmp/simulation_diagnostic.log
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# Setup logging to file
LOG_FILE = "/tmp/simulation_diagnostic.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduce noise from external libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google_genai').setLevel(logging.WARNING)

logger = logging.getLogger("simulation_test")


def log_separator(title: str):
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)


def main():
    log_separator("SIMULATION DIAGNOSTIC TEST")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working dir: {os.getcwd()}")
    
    # Step 1: Test imports
    log_separator("STEP 1: Testing Imports")
    try:
        from simulation import SimulationRunner
        from simulation.deck_loader import load_simulation_decks_dict
        from game_engine.game_engine import GameEngine
        from game_engine.models.game_state import GameState, Phase
        from game_engine.ai.llm_player import LLMPlayer
        logger.info("✅ All imports successful")
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 2: Load decks
    log_separator("STEP 2: Loading Decks")
    try:
        decks = load_simulation_decks_dict()
        logger.info(f"✅ Loaded {len(decks)} decks:")
        for name, deck in decks.items():
            logger.info(f"   - {name}: {deck.cards}")
    except Exception as e:
        logger.error(f"❌ Deck loading failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 3: Test GameState creation
    log_separator("STEP 3: Testing GameState Creation")
    try:
        from copy import deepcopy
        import uuid
        from game_engine.data.card_loader import load_cards_dict
        from game_engine.models.player import Player
        from game_engine.models.card import Zone
        
        card_templates = load_cards_dict()
        logger.info(f"✅ Loaded {len(card_templates)} card templates")
        
        deck1 = decks['Aggro_Rush']
        deck2 = decks['Disruption']
        
        # Create cards for each player
        p1_cards = []
        for card_name in deck1.cards:
            template = card_templates.get(card_name)
            if template is None:
                logger.error(f"❌ Card not found: {card_name}")
                return 1
            card = deepcopy(template)
            card.id = str(uuid.uuid4())
            card.owner = "player1"
            card.controller = "player1"
            card.zone = Zone.HAND
            p1_cards.append(card)
        
        p2_cards = []
        for card_name in deck2.cards:
            template = card_templates.get(card_name)
            card = deepcopy(template)
            card.id = str(uuid.uuid4())
            card.owner = "player2"
            card.controller = "player2"
            card.zone = Zone.HAND
            p2_cards.append(card)
        
        player1 = Player(player_id="player1", name="P1", hand=p1_cards)
        player2 = Player(player_id="player2", name="P2", hand=p2_cards)
        
        game_state = GameState(
            game_id=f"test-{uuid.uuid4()}",
            players={"player1": player1, "player2": player2},
            active_player_id="player1",
            first_player_id="player1",
            turn_number=1,
            phase=Phase.START,
            starting_decks={
                "player1": [c.name for c in p1_cards],
                "player2": [c.name for c in p2_cards],
            },
        )
        logger.info(f"✅ GameState created successfully")
        logger.info(f"   Game ID: {game_state.game_id}")
        logger.info(f"   P1 hand: {[c.name for c in player1.hand]}")
        logger.info(f"   P2 hand: {[c.name for c in player2.hand]}")
    except Exception as e:
        logger.error(f"❌ GameState creation failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 4: Test GameEngine
    log_separator("STEP 4: Testing GameEngine")
    try:
        engine = GameEngine(game_state)
        engine.start_turn()
        logger.info(f"✅ GameEngine initialized and turn started")
        logger.info(f"   Turn: {game_state.turn_number}")
        logger.info(f"   Phase: {game_state.phase}")
        logger.info(f"   Active player: {game_state.active_player_id}")
        logger.info(f"   P1 CC: {player1.cc}")
    except Exception as e:
        logger.error(f"❌ GameEngine failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 5: Test ActionValidator
    log_separator("STEP 5: Testing ActionValidator")
    try:
        from game_engine.validation.action_validator import ActionValidator
        validator = ActionValidator(engine)
        valid_actions = validator.get_valid_actions("player1", filter_for_ai=True)
        logger.info(f"✅ Got {len(valid_actions)} valid actions:")
        for i, action in enumerate(valid_actions[:5]):  # Show first 5
            logger.info(f"   {i+1}. {action.action_type}: {action.card_name or 'N/A'}")
        if len(valid_actions) > 5:
            logger.info(f"   ... and {len(valid_actions) - 5} more")
    except Exception as e:
        logger.error(f"❌ ActionValidator failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 6: Test LLMPlayer (single decision)
    log_separator("STEP 6: Testing LLMPlayer (single AI decision)")
    try:
        ai_player = LLMPlayer(provider="gemini", model="gemini-2.0-flash")
        logger.info("✅ LLMPlayer created")
        logger.info("   Making AI decision (this calls Gemini API)...")
        
        result = ai_player.select_action(
            game_state,
            "player1",
            valid_actions,
            engine
        )
        
        if result is None:
            logger.error("❌ AI returned None - decision failed")
            return 1
        
        action_index, reasoning = result
        selected_action = valid_actions[action_index]
        logger.info(f"✅ AI selected action:")
        logger.info(f"   Action: {selected_action.action_type}")
        logger.info(f"   Card: {selected_action.card_name}")
        logger.info(f"   Reasoning: {reasoning[:100]}...")
    except Exception as e:
        logger.error(f"❌ LLMPlayer failed: {e}")
        traceback.print_exc()
        return 1
    
    # Step 7: Run a full simulation game
    log_separator("STEP 7: Running Full Simulation Game")
    try:
        runner = SimulationRunner(
            player1_model='gemini-2.0-flash',
            player2_model='gemini-2.0-flash',
            max_turns=20
        )
        logger.info("✅ SimulationRunner created")
        
        deck1 = decks['Aggro_Rush']
        deck2 = decks['Disruption']
        
        logger.info(f"   Starting game: {deck1.name} vs {deck2.name}")
        logger.info("   This may take 1-3 minutes...")
        
        result = runner.run_game(deck1, deck2, game_number=1)
        
        logger.info(f"✅ Game completed!")
        logger.info(f"   Outcome: {result.outcome.value}")
        logger.info(f"   Winner: {result.winner_deck or 'Draw'}")
        logger.info(f"   Turns: {result.turn_count}")
        logger.info(f"   Duration: {result.duration_ms}ms ({result.duration_ms/1000:.1f}s)")
        logger.info(f"   Actions: {len(result.action_log)}")
        logger.info(f"   CC Tracking entries: {len(result.cc_tracking)}")
        
        if result.error_message:
            logger.warning(f"   Error: {result.error_message}")
        
        if result.action_log:
            logger.info("   First 5 actions:")
            for action in result.action_log[:5]:
                logger.info(f"      Turn {action['turn']}: {action['action']} {action.get('card', '')}")
        
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        traceback.print_exc()
        return 1
    
    log_separator("TEST COMPLETE")
    logger.info(f"Finished at: {datetime.now().isoformat()}")
    logger.info(f"All tests passed! Check {LOG_FILE} for details.")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
