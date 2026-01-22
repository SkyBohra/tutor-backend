# API module
from app.api.routes import questions_router, auth_router, avatars_router, visuals_router

__all__ = [
    "questions_router",
    "auth_router",
    "avatars_router",
    "visuals_router",
]
