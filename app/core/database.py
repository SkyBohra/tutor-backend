from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.user import User
from app.models.question import Question, QuestionHistory
from app.models.visual import Visual
from app.models.course import Course
from loguru import logger


class Database:
    client: AsyncIOMotorClient = None
    

db = Database()


async def connect_to_mongo():
    """Connect to MongoDB"""
    logger.info("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGO_URI)
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=db.client.get_default_database(),
        document_models=[
            User,
            Question,
            QuestionHistory,
            Visual,
            Course,
        ]
    )
    logger.info("Connected to MongoDB successfully!")


async def close_mongo_connection():
    """Close MongoDB connection"""
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed!")


def get_database():
    """Get database instance"""
    return db.client.get_default_database()
