"""
Live Classroom WebSocket Routes
Real-time teaching session endpoints
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from app.services.websocket_handler import classroom_manager
from app.services.live_teaching import live_teaching_service


router = APIRouter(tags=["Live Classroom"])


@router.websocket("/ws/classroom/{session_id}")
async def classroom_websocket(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(default=None)
):
    """
    WebSocket endpoint for live classroom sessions
    
    Connect to join a live teaching session.
    
    Message Types (Client -> Server):
    - {"type": "ask_question", "question": "What is gravity?", "subject": "physics"}
    - {"type": "request_visual", "visual_type": "animation", "concept": "gravity"}
    - {"type": "feedback", "feedback_type": "understood|confused|too_fast|too_slow"}
    - {"type": "chat", "message": "Can you explain more?"}
    - {"type": "pause"}
    - {"type": "resume"}
    
    Message Types (Server -> Client):
    - {"type": "connected", "session_id": "...", "participants": 1}
    - {"type": "teaching_start", "question": "..."}
    - {"type": "text", "content": "word ", "timestamp": 123.456}
    - {"type": "emphasis", "word": "gravity", "importance": "high"}
    - {"type": "visual_cue", "action": "animate", "data": {...}}
    - {"type": "visual_update", "visual_type": "animation", "data": {...}}
    - {"type": "pause", "duration": 0.3}
    - {"type": "complete", "full_text": "..."}
    - {"type": "teaching_end"}
    - {"type": "error", "message": "..."}
    """
    
    await classroom_manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            await classroom_manager.handle_message(websocket, data)
            
    except WebSocketDisconnect:
        await classroom_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await classroom_manager.disconnect(websocket)


@router.websocket("/ws/teach")
async def quick_teach_websocket(websocket: WebSocket):
    """
    Quick teaching WebSocket - single user, no session management
    
    Simple endpoint for one-on-one AI teaching.
    Send: {"question": "What is gravity?", "subject": "physics"}
    Receive: Streaming response events
    """
    
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("question")
            subject = data.get("subject")
            
            if not question:
                await websocket.send_json({
                    "type": "error",
                    "message": "Question is required"
                })
                continue
            
            # Stream the teaching response
            async for event in live_teaching_service.stream_explanation(
                question=question,
                subject=subject
            ):
                await websocket.send_json(event)
            
    except WebSocketDisconnect:
        logger.info("Quick teach WebSocket disconnected")
    except Exception as e:
        logger.error(f"Quick teach error: {e}")


@router.post("/sessions/create")
async def create_session():
    """Create a new classroom session and return session ID"""
    
    session_id = str(uuid.uuid4())[:8]
    
    return {
        "session_id": session_id,
        "websocket_url": f"/ws/classroom/{session_id}",
        "message": "Session created. Share this ID with students to join."
    }


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get status of a classroom session"""
    
    if session_id not in classroom_manager.session_states:
        return {
            "session_id": session_id,
            "active": False,
            "message": "Session not found or inactive"
        }
    
    state = classroom_manager.session_states[session_id]
    
    return {
        "session_id": session_id,
        "active": True,
        "participants": state.get("participants", 0),
        "is_teaching": state.get("is_teaching", False),
        "current_question": state.get("current_question"),
        "created_at": state.get("created_at")
    }
