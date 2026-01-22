"""
Avatar API Routes - Handle avatar and voice options
"""

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.services.avatar_service import avatar_service


router = APIRouter(prefix="/avatars", tags=["Avatars"])


@router.get("/options")
async def get_avatar_options():
    """Get available avatar and voice options"""
    
    return await avatar_service.get_available_avatars()


@router.post("/preview")
async def preview_avatar(
    text: str = "Hello! I'm your AI teacher. How can I help you today?",
    avatar_style: str = "professional",
    voice_style: str = "friendly"
):
    """
    Generate a preview of an avatar with sample text
    Useful for users to try different avatar/voice combinations
    """
    
    try:
        result = await avatar_service.generate_avatar_response(
            text=text,
            avatar_style=avatar_style,
            voice_style=voice_style
        )
        
        return {
            "preview_audio_url": result.get("audio_url"),
            "preview_video_url": result.get("video_url"),
            "avatar_style": avatar_style,
            "voice_style": voice_style,
            "duration_seconds": result.get("duration_seconds")
        }
        
    except Exception as e:
        logger.error(f"Error generating avatar preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.post("/generate-audio")
async def generate_audio_only(
    text: str,
    voice_style: str = "friendly"
):
    """Generate audio only (no avatar video)"""
    
    try:
        result = await avatar_service.generate_audio(
            text=text,
            voice_style=voice_style
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio"
            )
        
        return {
            "audio_url": result.get("audio_url"),
            "duration_seconds": result.get("duration_seconds"),
            "voice_style": voice_style
        }
        
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audio: {str(e)}"
        )
