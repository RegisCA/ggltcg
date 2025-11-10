"""
FastAPI application for GGLTCG.

Main entry point for the REST API server.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_games import router as games_router
from .routes_actions import router as actions_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all our debug logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers to DEBUG for detailed logging
logging.getLogger("game_engine.ai.llm_player").setLevel(logging.DEBUG)
logging.getLogger("game_engine.data.card_loader").setLevel(logging.DEBUG)
logging.getLogger("api.game_service").setLevel(logging.DEBUG)
logging.getLogger("game_engine.game_engine").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GGLTCG API",
    description="REST API for Good Guy Legion Trading Card Game",
    version="0.1.0",
)

# Configure CORS - allow all origins for development
# In production, restrict to specific frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(games_router)
app.include_router(actions_router)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "GGLTCG API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "games": "/games",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from .game_service import get_game_service
    
    service = get_game_service()
    
    return {
        "status": "healthy",
        "active_games": service.get_active_games_count(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
