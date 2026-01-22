"""
Real-time Live Teaching Service
Handles streaming responses for live interactive teaching experience
"""

import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any, Callable
from openai import AsyncOpenAI
from loguru import logger
from app.core.config import settings


class LiveTeachingService:
    """
    Service for real-time live teaching with streaming responses
    Provides live explanation streaming, real-time TTS, and visual cues
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    async def stream_explanation(
        self,
        question: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        language: str = "en",
        on_visual_cue: Optional[Callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream explanation in real-time, word by word
        
        Yields events like:
        - {"type": "start", "question": "..."}
        - {"type": "text", "content": "word"}
        - {"type": "visual_cue", "action": "show_animation", "data": {...}}
        - {"type": "emphasis", "word": "gravity", "importance": "high"}
        - {"type": "pause", "duration": 0.5}
        - {"type": "complete", "full_text": "..."}
        """
        
        system_prompt = self._build_live_teaching_prompt(subject, grade_level, language)
        
        yield {"type": "start", "question": question, "status": "teaching"}
        
        try:
            # Stream from OpenAI
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                stream=True,
                temperature=0.7,
                max_tokens=1500
            )
            
            full_text = ""
            current_sentence = ""
            word_buffer = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_text += content
                    word_buffer += content
                    current_sentence += content
                    
                    # Yield word by word for natural speech pacing
                    if ' ' in word_buffer or '\n' in word_buffer:
                        words = word_buffer.split()
                        for word in words[:-1]:  # Keep last incomplete word in buffer
                            yield {
                                "type": "text",
                                "content": word + " ",
                                "timestamp": asyncio.get_event_loop().time()
                            }
                            
                            # Check for emphasis words
                            emphasis = self._check_emphasis(word)
                            if emphasis:
                                yield {
                                    "type": "emphasis",
                                    "word": word,
                                    "importance": emphasis
                                }
                            
                            # Small delay for natural pacing
                            await asyncio.sleep(0.05)
                        
                        word_buffer = words[-1] if words else ""
                    
                    # Check for visual cues in the sentence
                    if '.' in current_sentence or '!' in current_sentence or '?' in current_sentence:
                        visual_cue = self._extract_visual_cue(current_sentence)
                        if visual_cue:
                            yield {
                                "type": "visual_cue",
                                "action": visual_cue["action"],
                                "data": visual_cue["data"]
                            }
                        current_sentence = ""
                        
                        # Natural pause at end of sentences
                        yield {"type": "pause", "duration": 0.3}
            
            # Yield remaining buffer
            if word_buffer:
                yield {"type": "text", "content": word_buffer}
            
            # Final completion event
            yield {
                "type": "complete",
                "full_text": full_text,
                "status": "finished"
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }
    
    def _build_live_teaching_prompt(
        self,
        subject: Optional[str],
        grade_level: Optional[str],
        language: str
    ) -> str:
        """Build prompt for live teaching style"""
        
        return f"""You are a live AI teacher giving a real-time explanation. 
Speak naturally as if you're teaching in a classroom.

Guidelines for live teaching:
1. Start with a brief, engaging introduction
2. Explain concepts step by step
3. Use examples and analogies
4. When explaining something visual, clearly describe what's being shown
5. Use natural pauses (indicated by periods)
6. Emphasize key terms
7. Keep explanations concise but complete
8. End with a brief summary

Subject: {subject or 'General'}
Student Level: {grade_level or 'General'}
Language: {language}

Speak conversationally, as if talking directly to the student.
Use phrases like "Let me show you...", "Notice how...", "This is important..."
When mentioning visual demonstrations, use [VISUAL: description] markers."""
    
    def _check_emphasis(self, word: str) -> Optional[str]:
        """Check if a word should be emphasized"""
        
        # High importance scientific/mathematical terms
        high_importance = [
            "gravity", "force", "energy", "mass", "velocity", "acceleration",
            "important", "key", "crucial", "remember", "note", "formula",
            "equation", "theorem", "law", "principle", "concept"
        ]
        
        # Medium importance terms
        medium_importance = [
            "example", "because", "therefore", "however", "although",
            "first", "second", "third", "finally", "result"
        ]
        
        word_lower = word.lower().strip('.,!?')
        
        if word_lower in high_importance:
            return "high"
        elif word_lower in medium_importance:
            return "medium"
        
        return None
    
    def _extract_visual_cue(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Extract visual cues from text"""
        
        sentence_lower = sentence.lower()
        
        # Check for visual markers
        if "[visual:" in sentence_lower:
            # Extract visual description
            start = sentence_lower.find("[visual:") + 8
            end = sentence_lower.find("]", start)
            if end > start:
                description = sentence[start:end].strip()
                return {
                    "action": "show_visual",
                    "data": {"description": description}
                }
        
        # Auto-detect visual cues from content
        visual_triggers = {
            "falling": {"action": "animate", "data": {"type": "falling_object"}},
            "dropping": {"action": "animate", "data": {"type": "falling_object"}},
            "apple falls": {"action": "animate", "data": {"type": "apple_falling"}},
            "pendulum": {"action": "animate", "data": {"type": "pendulum_swing"}},
            "swings": {"action": "animate", "data": {"type": "pendulum_swing"}},
            "wave": {"action": "animate", "data": {"type": "wave_motion"}},
            "oscillate": {"action": "animate", "data": {"type": "oscillation"}},
            "graph": {"action": "show_graph", "data": {"type": "function_graph"}},
            "circle": {"action": "draw", "data": {"type": "circle"}},
            "triangle": {"action": "draw", "data": {"type": "triangle"}},
            "diagram": {"action": "show_diagram", "data": {"type": "generic"}},
        }
        
        for trigger, cue in visual_triggers.items():
            if trigger in sentence_lower:
                return cue
        
        return None
    
    async def stream_with_audio(
        self,
        question: str,
        subject: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream explanation with real-time audio chunks
        Uses ElevenLabs streaming API for low-latency TTS
        """
        
        import httpx
        
        # First, start the text stream
        text_buffer = ""
        
        async for event in self.stream_explanation(question, subject):
            yield event
            
            if event["type"] == "text":
                text_buffer += event["content"]
                
                # When we have a complete sentence, generate audio
                if text_buffer.endswith(('.', '!', '?', '\n')):
                    if settings.ELEVENLABS_API_KEY:
                        audio_chunk = await self._generate_audio_chunk(
                            text_buffer,
                            voice_id or settings.ELEVENLABS_VOICE_ID
                        )
                        if audio_chunk:
                            yield {
                                "type": "audio",
                                "data": audio_chunk,
                                "text": text_buffer
                            }
                    text_buffer = ""
    
    async def _generate_audio_chunk(
        self,
        text: str,
        voice_id: str
    ) -> Optional[bytes]:
        """Generate audio chunk using ElevenLabs streaming"""
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                    headers={
                        "xi-api-key": settings.ELEVENLABS_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.content
                    
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
        
        return None


# Singleton instance
live_teaching_service = LiveTeachingService()
