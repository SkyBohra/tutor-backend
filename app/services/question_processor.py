"""
Question Processing Service - Orchestrates the complete question-to-response pipeline
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.models.question import Question, QuestionHistory
from app.services.ai_explanation import explanation_service
from app.services.visual_generation import visual_service
from app.services.avatar_service import avatar_service


class QuestionProcessingService:
    """
    Main service that orchestrates the complete question processing pipeline:
    1. Analyze question
    2. Generate explanation
    3. Generate visual demonstration
    4. Generate avatar video response
    5. Combine everything into final response
    """
    
    async def process_question(
        self,
        question_text: str,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        include_visual: bool = True,
        include_avatar: bool = True,
        language: str = "en",
        grade_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a question and generate complete response
        
        Args:
            question_text: The question to process
            user_id: Optional user ID for tracking
            subject: Optional subject hint
            include_visual: Whether to generate visual demonstration
            include_avatar: Whether to generate avatar video
            language: Response language
            grade_level: Student's grade level
        
        Returns:
            Complete response with explanation, visual, and avatar video
        """
        
        # Create question record
        question = Question(
            question_text=question_text,
            subject=subject,
            status="processing",
            processing_steps=[]
        )
        await question.insert()
        
        try:
            # Step 1: Analyze the question
            logger.info(f"Processing question: {question_text[:50]}...")
            await self._update_status(question, "analyzing", "Analyzing question...")
            
            analysis = await explanation_service.analyze_question(question_text)
            
            # Update question with analysis
            question.subject = analysis.get("subject", subject)
            question.topic = analysis.get("topic")
            question.difficulty_level = analysis.get("difficulty")
            question.keywords = analysis.get("keywords", [])
            
            # Step 2: Generate explanation
            await self._update_status(question, "generating_explanation", "Generating explanation...")
            
            explanation_result = await explanation_service.generate_explanation(
                question=question_text,
                subject=question.subject,
                grade_level=grade_level,
                language=language
            )
            
            question.explanation_text = explanation_result.get("explanation", "")
            question.related_concepts = explanation_result.get("related_concepts", [])
            
            # Get visual suggestion from explanation
            visual_suggestion = explanation_result.get("visual_suggestion", {})
            
            # Step 3: Generate visual demonstration (parallel with avatar)
            visual_task = None
            avatar_task = None
            
            if include_visual and visual_suggestion:
                await self._update_status(question, "generating_visual", "Generating visual demonstration...")
                visual_task = asyncio.create_task(
                    self._generate_visual(question, visual_suggestion)
                )
            
            # Step 4: Generate avatar video (parallel with visual)
            if include_avatar:
                await self._update_status(question, "generating_avatar", "Generating avatar video...")
                avatar_task = asyncio.create_task(
                    self._generate_avatar(question, explanation_result.get("explanation", ""))
                )
            
            # Wait for parallel tasks
            if visual_task:
                visual_result = await visual_task
                question.visual_type = visual_result.get("visual_type")
                question.visual_url = visual_result.get("url")
                question.visual_description = visual_suggestion.get("description")
            
            if avatar_task:
                avatar_result = await avatar_task
                question.avatar_video_url = avatar_result.get("video_url")
                question.explanation_audio_url = avatar_result.get("audio_url")
            
            # Step 5: Mark as completed
            question.status = "completed"
            question.updated_at = datetime.utcnow()
            await question.save()
            
            # Create history record if user is logged in
            if user_id:
                history = QuestionHistory(
                    user_id=user_id,
                    question_id=str(question.id),
                    question_text=question_text,
                    follow_up_questions=explanation_result.get("follow_up_questions", [])
                )
                await history.insert()
            
            logger.info(f"Successfully processed question: {question.id}")
            
            return {
                "question_id": str(question.id),
                "question": question_text,
                "explanation": question.explanation_text,
                "visual_type": question.visual_type,
                "visual_url": question.visual_url,
                "visual_description": question.visual_description,
                "avatar_video_url": question.avatar_video_url,
                "audio_url": question.explanation_audio_url,
                "keywords": question.keywords,
                "related_concepts": question.related_concepts,
                "follow_up_questions": explanation_result.get("follow_up_questions", []),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            question.status = "failed"
            question.processing_steps.append({
                "step": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            await question.save()
            
            raise
    
    async def _update_status(
        self,
        question: Question,
        step: str,
        message: str
    ):
        """Update question processing status"""
        
        question.processing_steps.append({
            "step": step,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        await question.save()
    
    async def _generate_visual(
        self,
        question: Question,
        visual_suggestion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate visual demonstration"""
        
        try:
            # First, get detailed visual script
            visual_script = await explanation_service.generate_visual_script(
                visual_suggestion,
                question.question_text
            )
            
            # Determine visual type
            visual_type = visual_suggestion.get("type", "animation")
            
            # Generate the visual
            result = await visual_service.generate_visual(
                visual_spec=visual_script,
                concept=question.question_text,
                visual_type=visual_type
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating visual: {e}")
            return {
                "visual_type": "placeholder",
                "url": None,
                "error": str(e)
            }
    
    async def _generate_avatar(
        self,
        question: Question,
        explanation_text: str
    ) -> Dict[str, Any]:
        """Generate avatar video response"""
        
        try:
            result = await avatar_service.generate_avatar_response(
                text=explanation_text,
                avatar_style="professional",
                voice_style="friendly"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating avatar: {e}")
            return {
                "video_url": None,
                "audio_url": None,
                "error": str(e)
            }
    
    async def get_question_status(self, question_id: str) -> Dict[str, Any]:
        """Get the current status of a question being processed"""
        
        question = await Question.get(question_id)
        
        if not question:
            return {
                "question_id": question_id,
                "status": "not_found",
                "error": "Question not found"
            }
        
        # Calculate progress percentage
        total_steps = 4  # analyze, explain, visual, avatar
        completed_steps = len([s for s in question.processing_steps if s["step"] != "error"])
        progress = min(int((completed_steps / total_steps) * 100), 100)
        
        if question.status == "completed":
            progress = 100
        
        current_step = None
        if question.processing_steps:
            current_step = question.processing_steps[-1].get("message")
        
        return {
            "question_id": question_id,
            "status": question.status,
            "progress": progress,
            "current_step": current_step,
            "steps_completed": [s["step"] for s in question.processing_steps]
        }
    
    async def get_question_response(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete response for a processed question"""
        
        question = await Question.get(question_id)
        
        if not question:
            return None
        
        return {
            "question_id": str(question.id),
            "question": question.question_text,
            "explanation": question.explanation_text,
            "visual_type": question.visual_type,
            "visual_url": question.visual_url,
            "visual_description": question.visual_description,
            "avatar_video_url": question.avatar_video_url,
            "audio_url": question.explanation_audio_url,
            "keywords": question.keywords,
            "related_concepts": question.related_concepts,
            "status": question.status
        }


# Singleton instance
question_processor = QuestionProcessingService()
