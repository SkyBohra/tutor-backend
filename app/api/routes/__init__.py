# API Routes exports
from app.api.routes.questions import router as questions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.avatars import router as avatars_router
from app.api.routes.visuals import router as visuals_router
from app.api.routes.live_classroom import router as live_classroom_router
from app.api.routes.streaming import router as streaming_router
from app.api.routes.teaching_pipeline import router as teaching_pipeline_router

__all__ = [
    "questions_router",
    "auth_router",
    "avatars_router",
    "visuals_router",
    "live_classroom_router",
    "streaming_router",
    "teaching_pipeline_router",
]
