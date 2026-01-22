from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import Field


class Course(Document):
    """Course model for structured learning"""
    
    title: str
    description: str
    subject: str  # physics, chemistry, math, etc.
    
    # Course structure
    grade_level: str  # 10th, 11th, 12th, college
    difficulty: str = "medium"  # easy, medium, hard
    
    # Content
    chapters: List[dict] = []  # List of chapters with topics
    total_lessons: int = 0
    total_duration_hours: Optional[float] = None
    
    # Instructor
    instructor_id: Optional[str] = None
    instructor_name: Optional[str] = None
    
    # Media
    thumbnail_url: Optional[str] = None
    intro_video_url: Optional[str] = None
    
    # Stats
    enrolled_count: int = 0
    completion_rate: float = 0.0
    average_rating: float = 0.0
    
    # Status
    is_published: bool = False
    is_free: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    class Settings:
        name = "courses"


class Lesson(Document):
    """Individual lesson within a course"""
    
    course_id: str
    chapter_index: int
    lesson_index: int
    
    title: str
    description: str
    
    # Content type
    content_type: str  # video, interactive, quiz, reading
    
    # Media
    video_url: Optional[str] = None
    visual_ids: List[str] = []  # Related visuals
    
    # Text content
    content_markdown: Optional[str] = None
    
    # Duration
    duration_minutes: int = 0
    
    # Questions covered
    key_concepts: List[str] = []
    common_questions: List[str] = []
    
    # Status
    is_published: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "lessons"
