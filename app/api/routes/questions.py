"""
Question API Routes - Handle question asking and response retrieval
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from loguru import logger

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.question import (
    QuestionRequest,
    QuestionResponse,
    QuestionStatusResponse,
    FeedbackRequest,
    FollowUpRequest,
)
from app.services.question_processor import question_processor
from app.models.question import Question, QuestionHistory


router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("/ask", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def ask_question(
    request: QuestionRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = None
):
    """
    Ask a question and get an AI-generated response with visual demonstration
    
    This endpoint:
    1. Analyzes the question to determine subject and topic
    2. Generates a comprehensive explanation
    3. Creates a visual demonstration (animation/image/diagram)
    4. Generates an avatar video explaining the concept
    
    Returns immediately with partial response, processing continues in background
    """
    
    try:
        user_id = str(current_user.id) if current_user else None
        grade_level = current_user.grade_level if current_user else None
        
        # Process the question
        result = await question_processor.process_question(
            question_text=request.question,
            user_id=user_id,
            subject=request.subject,
            include_visual=request.include_visual,
            include_avatar=request.include_avatar,
            language=request.language,
            grade_level=grade_level
        )
        
        return QuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}"
        )


@router.post("/ask-quick", response_model=dict)
async def ask_question_quick(
    request: QuestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Quick question endpoint - returns question ID immediately
    Processing happens in background
    Use /questions/{question_id}/status to check progress
    """
    
    from app.models.question import Question
    from datetime import datetime
    
    # Create question record
    question = Question(
        question_text=request.question,
        subject=request.subject,
        status="pending"
    )
    await question.insert()
    
    # Start background processing
    background_tasks.add_task(
        _process_question_background,
        question_id=str(question.id),
        request=request
    )
    
    return {
        "question_id": str(question.id),
        "status": "processing",
        "message": "Question received. Use /questions/{question_id}/status to check progress."
    }


async def _process_question_background(question_id: str, request: QuestionRequest):
    """Background task to process question"""
    
    try:
        await question_processor.process_question(
            question_text=request.question,
            subject=request.subject,
            include_visual=request.include_visual,
            include_avatar=request.include_avatar,
            language=request.language
        )
    except Exception as e:
        logger.error(f"Background processing failed for {question_id}: {e}")
        
        # Update question status to failed
        question = await Question.get(question_id)
        if question:
            question.status = "failed"
            await question.save()


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question_response(question_id: str):
    """Get the complete response for a processed question"""
    
    result = await question_processor.get_question_response(question_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    return QuestionResponse(**result)


@router.get("/{question_id}/status", response_model=QuestionStatusResponse)
async def get_question_status(question_id: str):
    """Get the current processing status of a question"""
    
    result = await question_processor.get_question_status(question_id)
    
    if result.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    return QuestionStatusResponse(**result)


@router.post("/{question_id}/feedback")
async def submit_feedback(
    question_id: str,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a question response"""
    
    # Find the history record
    history = await QuestionHistory.find_one(
        QuestionHistory.question_id == question_id,
        QuestionHistory.user_id == str(current_user.id)
    )
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question history not found"
        )
    
    # Update feedback
    history.was_helpful = request.was_helpful
    history.rating = request.rating
    history.feedback_text = request.feedback_text
    await history.save()
    
    return {"message": "Feedback submitted successfully"}


@router.post("/follow-up", response_model=QuestionResponse)
async def ask_follow_up(
    request: FollowUpRequest,
    current_user: Optional[User] = None
):
    """Ask a follow-up question based on a previous question"""
    
    # Get original question for context
    original = await Question.get(request.original_question_id)
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original question not found"
        )
    
    # Process follow-up with context
    user_id = str(current_user.id) if current_user else None
    
    result = await question_processor.process_question(
        question_text=request.follow_up_question,
        user_id=user_id,
        subject=original.subject,
        include_visual=True,
        include_avatar=True
    )
    
    # Update original question's history with follow-up
    if user_id:
        history = await QuestionHistory.find_one(
            QuestionHistory.question_id == request.original_question_id,
            QuestionHistory.user_id == user_id
        )
        if history:
            history.follow_up_questions.append(request.follow_up_question)
            await history.save()
    
    return QuestionResponse(**result)


@router.get("/history/me", response_model=list)
async def get_my_question_history(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """Get current user's question history"""
    
    history = await QuestionHistory.find(
        QuestionHistory.user_id == str(current_user.id)
    ).sort(-QuestionHistory.asked_at).skip(offset).limit(limit).to_list()
    
    return [
        {
            "question_id": h.question_id,
            "question": h.question_text,
            "asked_at": h.asked_at.isoformat(),
            "was_helpful": h.was_helpful,
            "rating": h.rating
        }
        for h in history
    ]
