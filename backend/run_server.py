#!/usr/bin/env python3
"""
Start the GGLTCG FastAPI server.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the GGLTCG FastAPI server")
    parser.add_argument(
        "--deck-csv",
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
    
    # Set the cards CSV path via environment variable if provided
    if args.deck_csv:
        deck_path = Path(args.deck_csv)
        if not deck_path.exists():
            print(f"Error: Deck CSV file not found: {deck_path}", file=sys.stderr)
            sys.exit(1)
        os.environ["CARDS_CSV_PATH"] = str(deck_path.absolute())
        print(f"Using deck CSV: {deck_path.absolute()}")
    
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )
