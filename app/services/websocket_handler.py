"""
WebSocket Handler for Real-time Live Teaching
Manages live classroom sessions with bi-directional communication
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from datetime import datetime

from app.services.live_teaching import live_teaching_service
from app.services.visual_generation import visual_service


class LiveClassroomManager:
    """
    Manages live classroom WebSocket connections
    Handles real-time teaching sessions with multiple students
    """
    
    def __init__(self):
        # Active connections: session_id -> set of websockets
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        
        # Session states: session_id -> session data
        self.session_states: Dict[str, Dict[str, Any]] = {}
        
        # User connections: websocket -> user data
        self.user_data: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: Optional[str] = None
    ):
        """Connect a user to a live session"""
        
        await websocket.accept()
        
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = set()
            self.session_states[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "current_question": None,
                "is_teaching": False,
                "participants": 0
            }
        
        self.active_sessions[session_id].add(websocket)
        self.user_data[websocket] = {
            "user_id": user_id,
            "session_id": session_id,
            "joined_at": datetime.utcnow().isoformat()
        }
        
        self.session_states[session_id]["participants"] += 1
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Welcome to the live classroom!",
            "participants": self.session_states[session_id]["participants"]
        })
        
        # Notify others
        await self.broadcast_to_session(
            session_id,
            {
                "type": "user_joined",
                "participants": self.session_states[session_id]["participants"]
            },
            exclude=websocket
        )
        
        logger.info(f"User connected to session {session_id}")
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a user from their session"""
        
        user_info = self.user_data.get(websocket)
        if not user_info:
            return
        
        session_id = user_info["session_id"]
        
        if session_id in self.active_sessions:
            self.active_sessions[session_id].discard(websocket)
            self.session_states[session_id]["participants"] -= 1
            
            # Clean up empty sessions
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
                del self.session_states[session_id]
            else:
                # Notify others
                await self.broadcast_to_session(
                    session_id,
                    {
                        "type": "user_left",
                        "participants": self.session_states[session_id]["participants"]
                    }
                )
        
        del self.user_data[websocket]
        logger.info(f"User disconnected from session {session_id}")
    
    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude: Optional[WebSocket] = None
    ):
        """Broadcast message to all users in a session"""
        
        if session_id not in self.active_sessions:
            return
        
        disconnected = set()
        
        for websocket in self.active_sessions[session_id]:
            if websocket == exclude:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def handle_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ):
        """Handle incoming WebSocket message"""
        
        user_info = self.user_data.get(websocket)
        if not user_info:
            return
        
        session_id = user_info["session_id"]
        msg_type = message.get("type")
        
        if msg_type == "ask_question":
            await self.handle_question(websocket, session_id, message)
        
        elif msg_type == "request_visual":
            await self.handle_visual_request(websocket, session_id, message)
        
        elif msg_type == "pause":
            await self.handle_pause(session_id)
        
        elif msg_type == "resume":
            await self.handle_resume(session_id)
        
        elif msg_type == "feedback":
            await self.handle_feedback(websocket, message)
        
        elif msg_type == "chat":
            await self.handle_chat(websocket, session_id, message)
    
    async def handle_question(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Handle a question from a student - start live teaching"""
        
        question = message.get("question", "")
        subject = message.get("subject")
        
        if not question:
            await websocket.send_json({
                "type": "error",
                "message": "Question is required"
            })
            return
        
        # Update session state
        self.session_states[session_id]["current_question"] = question
        self.session_states[session_id]["is_teaching"] = True
        
        # Notify all participants that teaching is starting
        await self.broadcast_to_session(
            session_id,
            {
                "type": "teaching_start",
                "question": question,
                "subject": subject
            }
        )
        
        # Start streaming the response to all participants
        try:
            async for event in live_teaching_service.stream_explanation(
                question=question,
                subject=subject
            ):
                # Broadcast each event to all session participants
                await self.broadcast_to_session(session_id, event)
                
                # Handle visual cues
                if event.get("type") == "visual_cue":
                    visual_event = await self._process_visual_cue(event)
                    if visual_event:
                        await self.broadcast_to_session(session_id, visual_event)
            
            # Teaching complete
            self.session_states[session_id]["is_teaching"] = False
            
            await self.broadcast_to_session(
                session_id,
                {
                    "type": "teaching_end",
                    "message": "Explanation complete. Feel free to ask follow-up questions!"
                }
            )
            
        except Exception as e:
            logger.error(f"Error during live teaching: {e}")
            await self.broadcast_to_session(
                session_id,
                {
                    "type": "error",
                    "message": "An error occurred during teaching"
                }
            )
            self.session_states[session_id]["is_teaching"] = False
    
    async def _process_visual_cue(
        self,
        event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process a visual cue and generate visual content"""
        
        data = event.get("data", {})
        action = event.get("action")
        
        if action == "animate":
            anim_type = data.get("type")
            
            # Return animation data for client to render
            return {
                "type": "visual_update",
                "visual_type": "animation",
                "animation": anim_type,
                "data": self._get_animation_data(anim_type)
            }
        
        elif action == "show_visual":
            return {
                "type": "visual_update",
                "visual_type": "image",
                "description": data.get("description")
            }
        
        return None
    
    def _get_animation_data(self, anim_type: str) -> Dict[str, Any]:
        """Get animation data for client-side rendering"""
        
        animations = {
            "falling_object": {
                "name": "Falling Object",
                "duration": 2000,
                "objects": [
                    {"type": "circle", "start": {"x": 50, "y": 10}, "end": {"x": 50, "y": 90}}
                ],
                "easing": "easeInQuad"
            },
            "apple_falling": {
                "name": "Apple Falling",
                "duration": 2000,
                "objects": [
                    {"type": "apple", "start": {"x": 50, "y": 20}, "end": {"x": 50, "y": 85}}
                ],
                "easing": "easeInQuad",
                "show_force_arrow": True
            },
            "pendulum_swing": {
                "name": "Pendulum",
                "duration": 3000,
                "type": "pendulum",
                "pivot": {"x": 50, "y": 10},
                "length": 60,
                "amplitude": 45
            },
            "wave_motion": {
                "name": "Wave",
                "duration": 4000,
                "type": "sine_wave",
                "amplitude": 30,
                "wavelength": 50,
                "speed": 2
            },
            "oscillation": {
                "name": "Oscillation",
                "duration": 3000,
                "type": "spring",
                "equilibrium": 50,
                "amplitude": 30
            }
        }
        
        return animations.get(anim_type, {"name": "Generic", "duration": 2000})
    
    async def handle_visual_request(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Handle request for a specific visual"""
        
        visual_type = message.get("visual_type", "animation")
        concept = message.get("concept", "")
        
        # Broadcast that visual is being generated
        await self.broadcast_to_session(
            session_id,
            {
                "type": "visual_loading",
                "message": f"Generating {visual_type} for {concept}..."
            }
        )
        
        # Generate visual
        try:
            result = await visual_service.generate_visual(
                visual_spec={"description": concept},
                concept=concept,
                visual_type=visual_type
            )
            
            await self.broadcast_to_session(
                session_id,
                {
                    "type": "visual_ready",
                    "visual_type": result.get("visual_type"),
                    "url": result.get("url"),
                    "concept": concept
                }
            )
            
        except Exception as e:
            logger.error(f"Visual generation error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Failed to generate visual"
            })
    
    async def handle_pause(self, session_id: str):
        """Pause the current teaching session"""
        
        self.session_states[session_id]["is_paused"] = True
        
        await self.broadcast_to_session(
            session_id,
            {
                "type": "session_paused",
                "message": "Session paused"
            }
        )
    
    async def handle_resume(self, session_id: str):
        """Resume the current teaching session"""
        
        self.session_states[session_id]["is_paused"] = False
        
        await self.broadcast_to_session(
            session_id,
            {
                "type": "session_resumed",
                "message": "Session resumed"
            }
        )
    
    async def handle_feedback(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ):
        """Handle real-time feedback from student"""
        
        feedback_type = message.get("feedback_type")  # "understood", "confused", "too_fast", "too_slow"
        
        # Could use this to adjust teaching pace/style
        logger.info(f"Received feedback: {feedback_type}")
        
        await websocket.send_json({
            "type": "feedback_received",
            "message": "Thank you for your feedback!"
        })
    
    async def handle_chat(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Handle chat messages in session"""
        
        user_info = self.user_data.get(websocket, {})
        chat_message = message.get("message", "")
        
        await self.broadcast_to_session(
            session_id,
            {
                "type": "chat_message",
                "user_id": user_info.get("user_id", "anonymous"),
                "message": chat_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Global classroom manager instance
classroom_manager = LiveClassroomManager()
