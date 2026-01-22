from typing import Optional, List
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Request schema for asking a question"""
    question: str = Field(..., min_length=3, max_length=2000, description="The question to ask")
    subject: Optional[str] = Field(None, description="Subject area (physics, chemistry, math, etc.)")
    include_visual: bool = Field(True, description="Whether to generate visual demonstration")
    include_avatar: bool = Field(True, description="Whether to generate avatar video response")
    language: str = Field("en", description="Response language")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is gravity?",
                "subject": "physics",
                "include_visual": True,
                "include_avatar": True,
                "language": "en"
            }
        }


class QuestionResponse(BaseModel):
    """Response schema for a question"""
    question_id: str
    question: str
    
    # Text explanation
    explanation: str
    
    # Visual demonstration
    visual_type: Optional[str] = None
    visual_url: Optional[str] = None
    visual_description: Optional[str] = None
    
    # Avatar video
    avatar_video_url: Optional[str] = None
    
    # Audio explanation
    audio_url: Optional[str] = None
    
    # Combined response
    combined_video_url: Optional[str] = None
    
    # Additional info
    keywords: List[str] = []
    related_concepts: List[str] = []
    follow_up_questions: List[str] = []
    
    # Status
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "question_id": "abc123",
                "question": "What is gravity?",
                "explanation": "Gravity is a fundamental force...",
                "visual_type": "animation",
                "visual_url": "https://storage.example.com/visuals/gravity.mp4",
                "avatar_video_url": "https://storage.example.com/avatar/gravity.mp4",
                "status": "completed"
            }
        }


class QuestionStatusResponse(BaseModel):
    """Response schema for question processing status"""
    question_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0  # 0-100
    current_step: Optional[str] = None
    steps_completed: List[str] = []
    error_message: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request schema for providing feedback on a response"""
    question_id: str
    was_helpful: bool
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None


class FollowUpRequest(BaseModel):
    """Request for follow-up questions"""
    original_question_id: str
    follow_up_question: str
