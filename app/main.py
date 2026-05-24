from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, drop_db
from app.routes import users, teams, projects, recommendations
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for FastAPI application
    Initialize database on startup
    """
    logger.info("Starting application...")
    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-driven Project and User Management Microservice",
    version=settings.app_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name}


@app.get("/", tags=["root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Project Management Microservice",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
