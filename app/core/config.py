from pydantic_settings import BaseSettings
from typing import List, Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""
    
    # App Configuration
    APP_NAME: str = "AI-Teacher"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    MONGO_URI: str = "mongodb://localhost:27017/ai-teacher"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Authentication
    JWT_SECRET: str = "your-super-secret-jwt-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LLM Configuration
    DEFAULT_LLM: str = "gemini"  # "gemini" or "openai"
    
    # Gemini AI (Default)
    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"
    
    # OpenAI (Fallback)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    
    # ElevenLabs (Text-to-Speech)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""
    
    # Replicate
    REPLICATE_API_TOKEN: str = ""
    
    # Stability AI
    STABILITY_API_KEY: str = ""
    
    # Avatar Services
    DID_API_KEY: str = ""
    HEYGEN_API_KEY: str = ""
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "ai-teacher-media"
    AWS_REGION: str = "us-east-1"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
