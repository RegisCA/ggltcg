#!/usr/bin/env python3
"""
Start the GGLTCG FastAPI server.
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the GGLTCG FastAPI server")
    parser.add_argument(
        "--deck",
        type=str,
        help="Path to the deck CSV file (default: backend/data/cards.csv)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload on code changes"
    )
    
    args = parser.parse_args()
    
    # Echo AI version configuration
    ai_version = os.getenv("AI_VERSION", "2")
    print(f"🤖 AI Version: {ai_version} (2=per-action, 3=turn-planning)")
    
    # Set the cards CSV path via environment variable if provided
    # Must be set BEFORE uvicorn.run() and in os.environ so child processes inherit it
    if args.deck:
        deck_path = Path(args.deck)
        if not deck_path.exists():
            print(f"Error: Deck CSV file not found: {deck_path}", file=sys.stderr)
            sys.exit(1)
        absolute_path = str(deck_path.absolute())
        os.environ["CARDS_CSV_PATH"] = absolute_path
        print(f"Using deck CSV: {absolute_path}")
    
    import uvicorn
    
    # When reload=True, uvicorn spawns a subprocess that needs to inherit env vars.
    # We use env_file or pass environment explicitly via the config.
    # Setting os.environ before uvicorn.run should work, but let's also
    # ensure the subprocess inherits by using reload_dirs to trigger reloads properly.
    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        reload_dirs=["src"] if not args.no_reload else None,
    )
