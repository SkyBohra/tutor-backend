"""
AI Teacher Backend - FastAPI Application
Main entry point for the application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys
import os

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.routes import (
    questions_router,
    auth_router,
    avatars_router,
    visuals_router,
    live_classroom_router,
    streaming_router,
    teaching_pipeline_router,
)


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    await connect_to_mongo()
    logger.info(f"{settings.APP_NAME} started successfully!")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_mongo_connection()
    logger.info(f"{settings.APP_NAME} shut down successfully!")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    AI Teacher Backend API
    
    An intelligent educational platform that provides:
    - AI-powered question answering with detailed explanations
    - Visual demonstrations (animations, diagrams, images)
    - Interactive avatar video responses
    - Personalized learning experiences
    
    ## Features
    
    - **Ask Questions**: Submit any educational question and receive a comprehensive response
    - **Visual Demonstrations**: Automatic generation of relevant visual content
    - **Avatar Responses**: AI avatar explains concepts with voice
    - **Learning History**: Track your learning progress
    
    ## Example Usage
    
    Ask a question like "What is gravity?" and receive:
    1. A detailed text explanation
    2. An animation showing an apple falling
    3. An avatar video explaining the concept
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else "Internal server error"
        }
    )


# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(avatars_router, prefix="/api/v1")
app.include_router(visuals_router, prefix="/api/v1")
app.include_router(streaming_router, prefix="/api/v1")
app.include_router(teaching_pipeline_router, prefix="/api/v1")

# WebSocket routes (no prefix)
app.include_router(live_classroom_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Create media directories if they don't exist
os.makedirs("media/audio", exist_ok=True)
os.makedirs("media/video", exist_ok=True)
os.makedirs("media/animations", exist_ok=True)
os.makedirs("media/images", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files for media
app.mount("/media", StaticFiles(directory="media"), name="media")

# Mount static files for demo frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
