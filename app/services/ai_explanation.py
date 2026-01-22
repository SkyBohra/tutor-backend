"""
AI Explanation Service - Generates educational explanations using OpenAI GPT
"""

import json
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from loguru import logger
from app.core.config import settings


class AIExplanationService:
    """Service for generating AI-powered educational explanations"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    async def generate_explanation(
        self,
        question: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive explanation for a question
        
        Returns:
            Dict containing:
            - explanation: Main explanation text
            - key_points: List of key points
            - visual_suggestion: Suggested visual demonstration
            - keywords: Related keywords
            - related_concepts: Related concepts for further learning
            - follow_up_questions: Suggested follow-up questions
        """
        
        system_prompt = self._build_system_prompt(subject, grade_level, language)
        user_prompt = self._build_user_prompt(question)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Generated explanation for: {question[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            raise
    
    def _build_system_prompt(
        self,
        subject: Optional[str],
        grade_level: Optional[str],
        language: str
    ) -> str:
        """Build the system prompt for the AI"""
        
        grade_context = ""
        if grade_level:
            grade_context = f"The student is in {grade_level} grade. Adjust your explanation complexity accordingly."
        
        subject_context = ""
        if subject:
            subject_context = f"This question is about {subject}."
        
        language_instruction = ""
        if language != "en":
            language_instruction = f"Respond in {language} language."
        
        return f"""You are an expert AI teacher who explains concepts in an engaging and educational way.
Your goal is to help students understand concepts through clear explanations and visual demonstrations.

{subject_context}
{grade_context}
{language_instruction}

When answering questions, you should:
1. Provide a clear, engaging explanation suitable for the student's level
2. Suggest a visual demonstration that would help illustrate the concept
3. Identify key points and related concepts
4. Suggest follow-up questions to deepen understanding

IMPORTANT: You must respond in valid JSON format with this exact structure:
{{
    "explanation": "Your detailed explanation here...",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "visual_suggestion": {{
        "type": "animation|image|diagram|video",
        "description": "Description of what visual should show",
        "elements": ["element1", "element2"],
        "animation_steps": ["step1", "step2"] // Only for animations
    }},
    "keywords": ["keyword1", "keyword2"],
    "related_concepts": ["concept1", "concept2"],
    "follow_up_questions": ["Question 1?", "Question 2?"],
    "difficulty_level": "easy|medium|hard",
    "estimated_read_time_seconds": 30
}}"""
    
    def _build_user_prompt(self, question: str) -> str:
        """Build the user prompt"""
        return f"""Please explain the following question in detail with a visual suggestion:

Question: {question}

Remember to respond in the exact JSON format specified."""
    
    async def generate_visual_script(
        self,
        visual_suggestion: Dict[str, Any],
        concept: str
    ) -> Dict[str, Any]:
        """
        Generate a detailed script/code for creating the visual demonstration
        This can be used to generate Manim animations or other visuals
        """
        
        system_prompt = """You are an expert at creating educational visualizations.
Generate a detailed specification for creating an animation or visual that explains a concept.

Respond in JSON format with:
{
    "visual_type": "manim_animation|lottie|svg|canvas",
    "title": "Title of the visual",
    "duration_seconds": 10,
    "scenes": [
        {
            "scene_number": 1,
            "description": "What happens in this scene",
            "duration_seconds": 3,
            "elements": [
                {
                    "type": "text|shape|image|arrow",
                    "properties": {...}
                }
            ],
            "animations": [
                {
                    "type": "fade_in|move|transform|highlight",
                    "target": "element_name",
                    "duration": 1
                }
            ]
        }
    ],
    "manim_code": "Optional Manim Python code to create this animation"
}"""
        
        user_prompt = f"""Create a visual specification for explaining: {concept}

Visual suggestion details:
{json.dumps(visual_suggestion, indent=2)}

Generate a detailed specification including Manim code if it's an animation."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=3000
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error generating visual script: {e}")
            raise
    
    async def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Analyze a question to determine subject, topic, and complexity
        """
        
        system_prompt = """Analyze the given question and categorize it.

Respond in JSON format:
{
    "subject": "physics|chemistry|biology|math|history|geography|computer_science|other",
    "topic": "specific topic within subject",
    "subtopics": ["subtopic1", "subtopic2"],
    "difficulty": "easy|medium|hard",
    "question_type": "conceptual|numerical|factual|analytical",
    "requires_visual": true/false,
    "suggested_visual_type": "animation|diagram|chart|image|none",
    "keywords": ["keyword1", "keyword2"]
}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this question: {question}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error analyzing question: {e}")
            raise


# Singleton instance
explanation_service = AIExplanationService()
