"""AI player implementation using Gemini API."""
import logging
import os

# Configure AI module logging based on LOG_LEVEL environment variable
# Default to WARNING to reduce noise in simulations
_log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
_level = getattr(logging, _log_level, logging.WARNING)

# Set level for all AI submodules
logging.getLogger("game_engine.ai").setLevel(_level)