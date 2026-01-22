"""
Streaming API Routes - HTTP-based streaming for real-time responses
Alternative to WebSocket for simpler client implementations
"""

from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from loguru import logger

from app.services.live_teaching import live_teaching_service


router = APIRouter(prefix="/stream", tags=["Streaming"])


class StreamQuestionRequest(BaseModel):
    question: str
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    language: str = "en"


@router.post("/ask")
async def stream_question_answer(request: StreamQuestionRequest):
    """
    Stream a question answer using Server-Sent Events (SSE)
    
    This endpoint returns a streaming response that sends events as they're generated.
    Each event is a JSON object on a new line.
    
    Example usage with JavaScript:
    ```javascript
    const response = await fetch('/api/v1/stream/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: 'What is gravity?'})
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        
        const text = decoder.decode(value);
        const events = text.split('\\n').filter(line => line.startsWith('data: '));
        
        for (const event of events) {
            const data = JSON.parse(event.slice(6));
            console.log(data);
        }
    }
    ```
    """
    
    async def event_generator():
        try:
            async for event in live_teaching_service.stream_explanation(
                question=request.question,
                subject=request.subject,
                grade_level=request.grade_level,
                language=request.language
            ):
                # Format as Server-Sent Event
                yield f"data: {json.dumps(event)}\n\n"
            
            # Send end event
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/ask")
async def stream_question_get(
    question: str = Query(..., description="The question to ask"),
    subject: Optional[str] = Query(None, description="Subject area"),
    language: str = Query("en", description="Response language")
):
    """
    Stream a question answer using GET request (for simpler clients)
    
    Example:
    GET /api/v1/stream/ask?question=What%20is%20gravity?&subject=physics
    """
    
    async def event_generator():
        try:
            async for event in live_teaching_service.stream_explanation(
                question=question,
                subject=subject,
                language=language
            ):
                yield f"data: {json.dumps(event)}\n\n"
            
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/ask-with-audio")
async def stream_with_audio(request: StreamQuestionRequest):
    """
    Stream question answer with real-time audio chunks
    
    Returns text events along with base64-encoded audio chunks.
    Audio is generated sentence by sentence for low latency.
    """
    
    async def event_generator():
        try:
            import base64
            
            async for event in live_teaching_service.stream_with_audio(
                question=request.question,
                subject=request.subject
            ):
                # If it's an audio event, encode the binary data
                if event.get("type") == "audio" and event.get("data"):
                    event["data"] = base64.b64encode(event["data"]).decode('utf-8')
                
                yield f"data: {json.dumps(event)}\n\n"
            
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Audio streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
