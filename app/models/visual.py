from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import Field


class Visual(Document):
    """Model for storing generated visual demonstrations"""
    
    # Visual metadata
    title: str
    description: str
    
    # Type: animation, image, diagram, video, 3d_model
    visual_type: str
    
    # Related concept/topic
    concept: str
    subject: Optional[str] = None
    keywords: List[str] = []
    
    # Generated content URLs
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    full_url: str
    
    # For animations
    animation_data: Optional[dict] = None  # Manim or Lottie animation data
    duration_seconds: Optional[float] = None
    
    # Source info
    generation_method: str = "ai"  # ai, manim, manual
    generation_prompt: Optional[str] = None
    
    # Usage stats
    view_count: int = 0
    use_count: int = 0
    
    # Status
    is_approved: bool = False
    is_public: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "visuals"


class VisualTemplate(Document):
    """Pre-defined visual templates for common concepts"""
    
    name: str
    description: str
    concept: str
    subject: str
    
    # Template type
    template_type: str  # manim_scene, lottie, svg, canvas
    
    # Template code/data
    template_code: str
    parameters: List[dict] = []  # Customizable parameters
    
    # Preview
    preview_url: Optional[str] = None
    
    # Usage
    use_count: int = 0
    
    # Status
    is_active: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "visual_templates"
