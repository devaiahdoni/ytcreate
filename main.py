import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as jobs_router
from database.repository import init_db
from config.settings import settings
from loguru import logger
import sys

# Configure structured logging with Loguru
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "C:/git/python/ytcreate/logs/pipeline.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG"
)

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Fully Automated AI Video Generation Pipeline with LangGraph Multi-Agent Workflows.",
    version="1.0.0"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(jobs_router)

@app.on_event("startup")
async def startup_event():
    """Event handler triggered on web service start."""
    logger.info("Initializing application and database tables...")
    try:
        await init_db()
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("FastAPI started but database connection is unavailable. Ensure Postgres is running locally.")

@app.get("/", tags=["General"])
async def root():
    """Service health and index endpoint."""
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "health": "Database is verified on startup."
    }

if __name__ == "__main__":
    # Start the server locally on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
