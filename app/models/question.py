from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import Field


class Question(Document):
    """Model for storing questions and their AI-generated responses"""
    
    # Question details
    question_text: str
    subject: Optional[str] = None  # physics, chemistry, math, etc.
    topic: Optional[str] = None
    difficulty_level: Optional[str] = None  # easy, medium, hard
    
    # AI Response
    explanation_text: str = ""
    explanation_audio_url: Optional[str] = None
    
    # Visual demonstration
    visual_type: Optional[str] = None  # animation, image, diagram, video
    visual_url: Optional[str] = None
    visual_description: Optional[str] = None
    
    # Avatar response
    avatar_video_url: Optional[str] = None
    
    # Combined response (avatar + visual side by side)
    combined_video_url: Optional[str] = None
    
    # Metadata
    keywords: List[str] = []
    related_concepts: List[str] = []
    
    # Processing status
    status: str = "pending"  # pending, processing, completed, failed
    processing_steps: List[dict] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "questions"


class QuestionHistory(Document):
    """Model for tracking user question history"""
    
    user_id: str
    question_id: str
    question_text: str
    
    # User feedback
    was_helpful: Optional[bool] = None
    rating: Optional[int] = None  # 1-5
    feedback_text: Optional[str] = None
    
    # Session info
    session_id: Optional[str] = None
    
    # Follow-up questions
    follow_up_questions: List[str] = []
    
    # Timestamps
    asked_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "question_history"
