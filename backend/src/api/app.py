"""
FastAPI application for GGLTCG.

Main entry point for the REST API server.
"""

import logging
import os
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_games import router as games_router
from .routes_actions import router as actions_router
from .routes_lobby import router as lobby_router
from .routes_stats import router as stats_router
from .routes_maintenance import router as maintenance_router
from .routes_admin import router as admin_router
from .routes_simulation import router as simulation_router
from .auth_routes import router as auth_router

# Initialize Sentry for error tracking (production only)
SENTRY_DSN = os.getenv("SENTRY_DSN")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if SENTRY_DSN and ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
        profiles_sample_rate=1.0,  # Capture 100% of profiles
        environment=ENVIRONMENT,
        enable_tracing=True,
    )

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
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(actions_router)
app.include_router(lobby_router)
app.include_router(stats_router)
app.include_router(maintenance_router)
app.include_router(admin_router)
app.include_router(simulation_router)


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
    """Health check endpoint with database and migration status."""
    from .game_service import get_game_service
    from .database import SessionLocal
    from .db_models import GameModel
    import os
    
    service = get_game_service()
    
    # Get game counts by status
    db_connected = False
    games_in_progress = 0
    total_games = 0
    alembic_version = None
    
    try:
        db = SessionLocal()
        db_connected = True
        
        # Count games by status
        games_in_progress = db.query(GameModel).filter(GameModel.status == "active").count()
        total_games = db.query(GameModel).count()
        
        # Get current Alembic migration version
        from sqlalchemy import text
        result = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if result:
            alembic_version = result[0]
        
        db.close()
    except Exception as e:
        logger.warning(f"Health check database query failed: {e}")
    
    return {
        "status": "healthy",
        "database": {
            "connected": db_connected,
            "migration_version": alembic_version,
        },
        "games": {
            "in_progress": games_in_progress,
            "total": total_games,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
