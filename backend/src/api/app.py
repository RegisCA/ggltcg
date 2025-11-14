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
    level=logging.INFO,  # Set back to INFO for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers to DEBUG for detailed AI logging
logging.getLogger("game_engine.ai.llm_player").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GGLTCG API",
    description="REST API for Googooland TCG game engine",
    version="0.1.0",
)

# Configure CORS - allow frontend origins
import os

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
