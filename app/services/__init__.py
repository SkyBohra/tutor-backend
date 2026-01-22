# Services exports
from app.services.ai_explanation import AIExplanationService, explanation_service
from app.services.visual_generation import VisualGenerationService, visual_service
from app.services.avatar_service import AvatarService, avatar_service
from app.services.question_processor import QuestionProcessingService, question_processor
from app.services.live_teaching import LiveTeachingService, live_teaching_service
from app.services.websocket_handler import LiveClassroomManager, classroom_manager

__all__ = [
    "AIExplanationService",
    "explanation_service",
    "VisualGenerationService",
    "visual_service",
    "AvatarService",
    "avatar_service",
    "QuestionProcessingService",
    "question_processor",
    "LiveTeachingService",
    "live_teaching_service",
    "LiveClassroomManager",
    "classroom_manager",
]
