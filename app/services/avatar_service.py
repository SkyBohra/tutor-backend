"""
Avatar Service - Generates avatar video responses with text-to-speech
Uses ElevenLabs for TTS and D-ID/HeyGen for avatar video generation
"""

import os
import json
import asyncio
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
import httpx
from loguru import logger
from app.core.config import settings


class AvatarService:
    """Service for generating avatar video responses"""
    
    def __init__(self):
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_voice_id = settings.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"  # Default voice
        self.did_api_key = settings.DID_API_KEY
        self.heygen_api_key = settings.HEYGEN_API_KEY
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_teacher_avatar"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def generate_avatar_response(
        self,
        text: str,
        avatar_style: str = "professional",
        voice_style: str = "friendly"
    ) -> Dict[str, Any]:
        """
        Generate a complete avatar video response
        
        Args:
            text: The explanation text to speak
            avatar_style: Style of avatar (professional, casual, animated)
            voice_style: Voice style (friendly, professional, energetic)
        
        Returns:
            Dict with avatar video URL and metadata
        """
        
        try:
            # Step 1: Generate audio from text using TTS
            audio_result = await self.generate_audio(text, voice_style)
            
            if not audio_result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to generate audio",
                    "audio_url": None,
                    "video_url": None
                }
            
            # Step 2: Generate avatar video with the audio
            video_result = await self.generate_avatar_video(
                audio_url=audio_result.get("audio_url"),
                text=text,
                avatar_style=avatar_style
            )
            
            return {
                "success": True,
                "audio_url": audio_result.get("audio_url"),
                "video_url": video_result.get("video_url"),
                "duration_seconds": audio_result.get("duration_seconds"),
                "avatar_style": avatar_style,
                "voice_style": voice_style
            }
            
        except Exception as e:
            logger.error(f"Error generating avatar response: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_url": None,
                "video_url": None
            }
    
    async def generate_audio(
        self,
        text: str,
        voice_style: str = "friendly"
    ) -> Dict[str, Any]:
        """Generate audio using ElevenLabs TTS"""
        
        if not self.elevenlabs_api_key:
            logger.warning("ElevenLabs API key not configured, using fallback")
            return await self._generate_fallback_audio(text)
        
        try:
            # ElevenLabs voice settings based on style
            voice_settings = self._get_voice_settings(voice_style)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}",
                    headers={
                        "xi-api-key": self.elevenlabs_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": voice_settings
                    }
                )
                
                if response.status_code == 200:
                    # Save audio file
                    audio_filename = f"audio_{hash(text)}.mp3"
                    audio_path = self.temp_dir / audio_filename
                    audio_path.write_bytes(response.content)
                    
                    # Estimate duration (rough estimate: ~150 words per minute)
                    word_count = len(text.split())
                    duration_seconds = (word_count / 150) * 60
                    
                    # TODO: Upload to S3 and return URL
                    return {
                        "success": True,
                        "audio_url": f"/media/audio/{audio_filename}",  # Placeholder
                        "local_path": str(audio_path),
                        "duration_seconds": duration_seconds
                    }
                else:
                    logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                    return await self._generate_fallback_audio(text)
                    
        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {e}")
            return await self._generate_fallback_audio(text)
    
    def _get_voice_settings(self, voice_style: str) -> Dict[str, float]:
        """Get ElevenLabs voice settings based on style"""
        
        settings_map = {
            "friendly": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True
            },
            "professional": {
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.1,
                "use_speaker_boost": True
            },
            "energetic": {
                "stability": 0.3,
                "similarity_boost": 0.7,
                "style": 0.5,
                "use_speaker_boost": True
            },
            "calm": {
                "stability": 0.8,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": False
            }
        }
        
        return settings_map.get(voice_style, settings_map["friendly"])
    
    async def generate_avatar_video(
        self,
        audio_url: Optional[str] = None,
        text: Optional[str] = None,
        avatar_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        Generate avatar video using D-ID or HeyGen
        """
        
        # Try D-ID first
        if self.did_api_key:
            return await self._generate_did_video(audio_url, text, avatar_style)
        
        # Try HeyGen
        if self.heygen_api_key:
            return await self._generate_heygen_video(audio_url, text, avatar_style)
        
        # Fallback: Return placeholder
        return self._get_placeholder_video(text)
    
    async def _generate_did_video(
        self,
        audio_url: Optional[str],
        text: Optional[str],
        avatar_style: str
    ) -> Dict[str, Any]:
        """Generate video using D-ID API"""
        
        try:
            # D-ID presenter images based on style
            presenter_map = {
                "professional": "amy-Aq6OmGZnMt",
                "casual": "josh-lite-D0BYJxg4",
                "animated": "sarah-lite-D0BYJxg4"
            }
            
            presenter_id = presenter_map.get(avatar_style, presenter_map["professional"])
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Create talk request
                payload = {
                    "source_url": f"https://d-id.com/api/clips/presenters/{presenter_id}",
                    "script": {
                        "type": "text" if text else "audio",
                    },
                    "config": {
                        "stitch": True
                    }
                }
                
                if text:
                    payload["script"]["input"] = text
                    payload["script"]["provider"] = {
                        "type": "microsoft",
                        "voice_id": "en-US-JennyNeural"
                    }
                elif audio_url:
                    payload["script"]["audio_url"] = audio_url
                
                response = await client.post(
                    "https://api.d-id.com/talks",
                    headers={
                        "Authorization": f"Basic {self.did_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code == 201:
                    talk_data = response.json()
                    talk_id = talk_data.get("id")
                    
                    # Poll for completion
                    video_url = await self._poll_did_video(client, talk_id)
                    
                    return {
                        "success": True,
                        "video_url": video_url,
                        "provider": "d-id"
                    }
                else:
                    logger.error(f"D-ID API error: {response.status_code} - {response.text}")
                    return self._get_placeholder_video(text)
                    
        except Exception as e:
            logger.error(f"Error generating D-ID video: {e}")
            return self._get_placeholder_video(text)
    
    async def _poll_did_video(
        self,
        client: httpx.AsyncClient,
        talk_id: str,
        max_attempts: int = 30
    ) -> Optional[str]:
        """Poll D-ID API for video completion"""
        
        for attempt in range(max_attempts):
            response = await client.get(
                f"https://api.d-id.com/talks/{talk_id}",
                headers={
                    "Authorization": f"Basic {self.did_api_key}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "done":
                    return data.get("result_url")
                elif status == "error":
                    logger.error(f"D-ID video generation failed: {data}")
                    return None
            
            await asyncio.sleep(2)
        
        logger.error("D-ID video generation timed out")
        return None
    
    async def _generate_heygen_video(
        self,
        audio_url: Optional[str],
        text: Optional[str],
        avatar_style: str
    ) -> Dict[str, Any]:
        """Generate video using HeyGen API"""
        
        try:
            # HeyGen avatar IDs based on style
            avatar_map = {
                "professional": "josh_lite_front",
                "casual": "anna_costume1_front",
                "animated": "monica_costume1_front"
            }
            
            avatar_id = avatar_map.get(avatar_style, avatar_map["professional"])
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": avatar_id,
                                "avatar_style": "normal"
                            },
                            "voice": {
                                "type": "text",
                                "input_text": text,
                                "voice_id": "1bd001e7e50f421d891986aad5158bc8"  # Default voice
                            }
                        }
                    ],
                    "dimension": {
                        "width": 1280,
                        "height": 720
                    }
                }
                
                response = await client.post(
                    "https://api.heygen.com/v2/video/generate",
                    headers={
                        "X-Api-Key": self.heygen_api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    video_id = data.get("data", {}).get("video_id")
                    
                    # Poll for completion
                    video_url = await self._poll_heygen_video(client, video_id)
                    
                    return {
                        "success": True,
                        "video_url": video_url,
                        "provider": "heygen"
                    }
                else:
                    logger.error(f"HeyGen API error: {response.status_code} - {response.text}")
                    return self._get_placeholder_video(text)
                    
        except Exception as e:
            logger.error(f"Error generating HeyGen video: {e}")
            return self._get_placeholder_video(text)
    
    async def _poll_heygen_video(
        self,
        client: httpx.AsyncClient,
        video_id: str,
        max_attempts: int = 60
    ) -> Optional[str]:
        """Poll HeyGen API for video completion"""
        
        for attempt in range(max_attempts):
            response = await client.get(
                f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                headers={
                    "X-Api-Key": self.heygen_api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {}).get("status")
                
                if status == "completed":
                    return data.get("data", {}).get("video_url")
                elif status == "failed":
                    logger.error(f"HeyGen video generation failed: {data}")
                    return None
            
            await asyncio.sleep(3)
        
        logger.error("HeyGen video generation timed out")
        return None
    
    async def _generate_fallback_audio(self, text: str) -> Dict[str, Any]:
        """Generate fallback audio using gTTS (free alternative)"""
        
        try:
            from gtts import gTTS
            import io
            
            # Generate audio
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to file
            audio_filename = f"audio_{hash(text)}.mp3"
            audio_path = self.temp_dir / audio_filename
            tts.save(str(audio_path))
            
            # Estimate duration
            word_count = len(text.split())
            duration_seconds = (word_count / 150) * 60
            
            return {
                "success": True,
                "audio_url": f"/media/audio/{audio_filename}",
                "local_path": str(audio_path),
                "duration_seconds": duration_seconds,
                "provider": "gtts"
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback audio: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_placeholder_video(self, text: Optional[str]) -> Dict[str, Any]:
        """Return placeholder video info"""
        
        return {
            "success": False,
            "video_url": None,
            "message": "Avatar video generation requires API keys (D-ID or HeyGen)",
            "provider": "placeholder"
        }
    
    async def get_available_avatars(self) -> Dict[str, Any]:
        """Get list of available avatar styles"""
        
        return {
            "avatars": [
                {
                    "id": "professional",
                    "name": "Professional Teacher",
                    "description": "A professional-looking teacher avatar",
                    "preview_url": "/avatars/professional.jpg"
                },
                {
                    "id": "casual",
                    "name": "Casual Tutor",
                    "description": "A friendly, casual tutor avatar",
                    "preview_url": "/avatars/casual.jpg"
                },
                {
                    "id": "animated",
                    "name": "Animated Character",
                    "description": "An animated cartoon-style character",
                    "preview_url": "/avatars/animated.jpg"
                }
            ],
            "voices": [
                {
                    "id": "friendly",
                    "name": "Friendly",
                    "description": "Warm and approachable voice"
                },
                {
                    "id": "professional",
                    "name": "Professional",
                    "description": "Clear and professional voice"
                },
                {
                    "id": "energetic",
                    "name": "Energetic",
                    "description": "Enthusiastic and lively voice"
                },
                {
                    "id": "calm",
                    "name": "Calm",
                    "description": "Soothing and calm voice"
                }
            ]
        }


# Singleton instance
avatar_service = AvatarService()
