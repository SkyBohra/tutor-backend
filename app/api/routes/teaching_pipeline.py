"""
Teaching Pipeline API
Orchestrates: Question → LLM → Parallel(ElevenLabs Voice + Visual + Avatar Lip Sync)
Supports: Gemini (default) and OpenAI
"""
import asyncio
import os
import json
import base64
import time
from pathlib import Path
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Load environment variables from correct path
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from openai import AsyncOpenAI
import google.generativeai as genai

router = APIRouter(prefix="/teaching", tags=["Teaching Pipeline"])

# Initialize API keys
openai_api_key = os.getenv("OPENAI_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model_name = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
default_llm = os.getenv("DEFAULT_LLM", "gemini")  # Default to Gemini

print(f"Teaching Pipeline: OpenAI API Key loaded: {bool(openai_api_key)}")
print(f"Teaching Pipeline: Gemini API Key loaded: {bool(gemini_api_key)}")
print(f"Teaching Pipeline: Gemini Model: {gemini_model_name}")
print(f"Teaching Pipeline: Default LLM: {default_llm}")

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None

# Initialize Gemini
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel(gemini_model_name)
else:
    gemini_model = None

class TeachingRequest(BaseModel):
    question: str
    subject: Optional[str] = "general"
    voice_id: Optional[str] = None
    include_visual: bool = True
    include_avatar: bool = True
    llm_provider: Optional[Literal["gemini", "openai"]] = None  # Override default

class TeachingResponse(BaseModel):
    question: str
    spoken_answer: str  # What the teacher SAYS (for voice)
    visual_example: str  # Description of visual to SHOW
    remember: str  # Key point to remember
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    visual_type: str
    visual_description: str
    lip_sync_data: Optional[dict] = None
    processing_time: float

# Visual type mapping - comprehensive mapping for different topics
def get_visual_type(question: str, visual_example: str = "") -> tuple[str, str]:
    """Determine visual type based on question and LLM's visual suggestion"""
    # Combine question and visual_example for better matching
    combined = f"{question} {visual_example}".lower()
    
    # Extensive visual mappings with more keywords for better detection
    visuals = [
        # Physics - Mechanics
        (['gravity', 'fall', 'falling', 'apple', 'drop', 'weight', 'newton', 'गुरुत्वाकर्षण', 'गिरना', 'सेब'], 
         'falling_object', 'Demonstrating gravity with a falling apple'),
        
        (['pendulum', 'swing', 'swinging', 'clock', 'oscillat', 'पेंडुलम', 'झूलना', 'घड़ी'], 
         'pendulum_swing', 'Showing pendulum motion'),
        
        (['spring', 'elastic', 'hooke', 'stretch', 'compress', 'bounce', 'स्प्रिंग', 'लचीला'], 
         'spring_oscillation', 'Demonstrating spring mechanics'),
        
        (['force', 'push', 'pull', 'motion', 'accelerat', 'velocity', 'speed', 'बल', 'गति', 'रफ्तार'], 
         'force_motion', 'Demonstrating force and motion'),
        
        # Physics - Waves & Energy
        (['wave', 'sound', 'light', 'frequency', 'vibrat', 'audio', 'तरंग', 'ध्वनि', 'आवाज'], 
         'wave_motion', 'Visualizing wave propagation'),
        
        (['energy', 'kinetic', 'potential', 'conserv', 'work', 'ऊर्जा', 'गतिज', 'स्थितिज'], 
         'energy_transfer', 'Showing energy transformation'),
        
        # Physics - Astronomy
        (['planet', 'solar', 'orbit', 'earth', 'moon', 'sun', 'space', 'star', 'ग्रह', 'पृथ्वी', 'चंद्रमा', 'सूर्य'], 
         'orbital_motion', 'Showing planetary orbits'),
        
        # Physics - Electricity
        (['electr', 'current', 'volt', 'circuit', 'battery', 'बिजली', 'विद्युत', 'करंट'], 
         'electric_flow', 'Visualizing electric current'),
        
        # Chemistry
        (['atom', 'molecul', 'element', 'chemi', 'bond', 'परमाणु', 'अणु', 'तत्व', 'रासायनिक'], 
         'molecular_motion', 'Showing molecular structure'),
        
        (['water', 'h2o', 'liquid', 'solid', 'gas', 'boil', 'freeze', 'evapor', 'पानी', 'तरल', 'ठोस', 'गैस'], 
         'state_change', 'Showing states of matter'),
        
        # Biology
        (['cell', 'dna', 'plant', 'animal', 'body', 'heart', 'blood', 'कोशिका', 'पौधा', 'जानवर', 'शरीर', 'दिल'], 
         'biology_visual', 'Biological visualization'),
        
        (['photosynthe', 'leaf', 'sun', 'oxygen', 'carbon', 'पत्ती', 'प्रकाश संश्लेषण'], 
         'photosynthesis', 'Showing photosynthesis process'),
        
        # Mathematics
        (['math', 'number', 'add', 'subtract', 'multipl', 'divid', 'गणित', 'संख्या', 'जोड़', 'घटाना', 'गुणा', 'भाग'], 
         'math_visual', 'Mathematical visualization'),
        
        (['circle', 'triangle', 'square', 'geometry', 'shape', 'angle', 'वृत्त', 'त्रिभुज', 'वर्ग', 'आकार'], 
         'geometry_visual', 'Showing geometric shapes'),
        
        (['graph', 'plot', 'function', 'equation', 'x', 'y', 'ग्राफ', 'समीकरण'], 
         'graph_visual', 'Mathematical graph'),
        
        (['fraction', 'percent', 'ratio', 'भिन्न', 'प्रतिशत', 'अनुपात'], 
         'fraction_visual', 'Showing fractions'),
    ]
    
    for keywords, vtype, desc in visuals:
        if any(kw in combined for kw in keywords):
            return vtype, desc
    
    # Default fallback
    return 'falling_object', 'Educational visual demonstration'


async def generate_llm_response(question: str, subject: str, provider: Optional[str] = None) -> dict:
    """Generate teaching response with separate spoken and visual parts"""
    
    # Determine which provider to use
    llm_to_use = provider or default_llm
    
    system_prompt = f"""You are a friendly AI teacher. Generate a response in JSON format.

IMPORTANT LANGUAGE RULE:
- If student asks in HINDI → Reply in HINDI
- If student asks in ENGLISH → Reply in ENGLISH  
- If student asks in MIXED (Hinglish) → Reply in MIXED (Hinglish)
- Match the EXACT language style of the student's question!

Response format:
1. "spoken" - SHORT simple explanation (1-2 sentences) that teacher will SPEAK. Use simple words.
2. "visual_type" - Choose EXACTLY ONE animation from this list that best explains the concept:
   - "falling_object" - Apple falling from tree (gravity, weight, mass, Newton)
   - "pendulum_swing" - Pendulum swinging (oscillation, time period, clock)
   - "wave_motion" - Wave moving (sound, light, frequency, vibration)
   - "spring_oscillation" - Spring bouncing (elastic, Hooke's law, compression)
   - "orbital_motion" - Planets orbiting sun (solar system, earth, moon, space)
   - "electric_flow" - Electric current in circuit (electricity, voltage, battery)
   - "molecular_motion" - Water molecule H2O (atoms, molecules, chemistry)
   - "force_motion" - Box being pushed (force, Newton's laws, friction)
   - "math_visual" - Number blocks 2+3=5 (addition, subtraction, counting)
   - "geometry_visual" - Rotating shapes (triangle, circle, square)
   - "energy_transfer" - Ball on ramp (kinetic energy, potential energy)
3. "visual_example" - Description of what the visual shows in SAME LANGUAGE as student.
4. "remember" - One key point to remember (1 sentence).

RESPOND ONLY IN THIS JSON FORMAT:
{{
  "spoken": "Your explanation in SAME LANGUAGE as student",
  "visual_type": "EXACTLY one from the list above",
  "visual_example": "Description of visual in SAME LANGUAGE",
  "remember": "Key point in SAME LANGUAGE as student"
}}

Subject: {subject}
Be warm, friendly, and use VERY simple words."""

    default_response = {
        "spoken": f"Let me explain {question} to you in a simple way.",
        "visual_example": "Watch this demonstration to understand better.",
        "remember": "This is an important concept in science!"
    }

    # Try Gemini first (default)
    if llm_to_use == "gemini" and gemini_model:
        try:
            prompt = f"{system_prompt}\n\nStudent asks: {question}"
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt
            )
            print(f"Gemini Response generated successfully")
            # Try to parse JSON from response
            try:
                import re
                text = response.text
                # Extract JSON from response
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # If no JSON, create structured response from text
                    return {"spoken": text, "visual_example": "", "remember": ""}
            except:
                return {"spoken": response.text, "visual_example": "", "remember": ""}
        except Exception as e:
            print(f"Gemini Error: {e}")
            # Fall back to OpenAI if Gemini fails
            if openai_client:
                llm_to_use = "openai"
            else:
                return default_response
    
    # Use OpenAI
    if llm_to_use == "openai" and openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=300,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            print(f"OpenAI Response generated successfully")
            try:
                return json.loads(response.choices[0].message.content)
            except:
                return {"spoken": response.choices[0].message.content, "visual_example": "", "remember": ""}
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return default_response
    
    # No LLM available
    return default_response


def generate_fallback_response(question: str) -> dict:
    """Generate educational fallback responses when LLM is unavailable"""
    q = question.lower()
    
    responses = {
        'newton': {
            "spoken": "Newton's First Law says that things like to stay as they are. If something is not moving, it stays still. If it's moving, it keeps moving until something stops it!",
            "visual_example": "Watch the ball - it stays still until I push it, then keeps rolling until friction stops it.",
            "remember": "Things don't change unless a force makes them change!"
        },
        'gravity': {
            "spoken": "Gravity is like an invisible magnet that pulls everything down towards the ground. It's why things fall when you drop them!",
            "visual_example": "Watch the apple fall from the tree - gravity pulls it straight down to the ground.",
            "remember": "Gravity always pulls things down towards Earth!"
        },
        'pendulum': {
            "spoken": "A pendulum is like a swing that goes back and forth. Gravity pulls it down, and it swings up on the other side!",
            "visual_example": "Watch the pendulum swing back and forth - gravity keeps pulling it down in the middle.",
            "remember": "Pendulums swing because of gravity!"
        },
        'wave': {
            "spoken": "Waves are like ripples in water. They carry energy from one place to another without moving the water itself!",
            "visual_example": "Watch the wave move across - see how the energy travels but the water just goes up and down.",
            "remember": "Waves carry energy, not matter!"
        },
        'spring': {
            "spoken": "A spring stores energy when you stretch or squeeze it. When you let go, it bounces back!",
            "visual_example": "Watch the spring stretch and bounce back - it stores energy and releases it.",
            "remember": "Springs store and release energy!"
        },
        'atom': {
            "spoken": "Atoms are tiny building blocks that make up everything around us. They're too small to see, but they're everywhere!",
            "visual_example": "Watch the atom model - electrons spin around the center like tiny planets.",
            "remember": "Everything is made of atoms!"
        },
        'force': {
            "spoken": "Force is a push or pull that makes things move. The harder you push, the faster things go!",
            "visual_example": "Watch when I push the box - a bigger push makes it move faster.",
            "remember": "Force makes things move or stop!"
        },
        'energy': {
            "spoken": "Energy is what makes things happen! It can change form but never disappears.",
            "visual_example": "Watch the ball roll down - it starts with stored energy and turns into moving energy.",
            "remember": "Energy changes form but is never lost!"
        }
    }
    
    for keyword, response in responses.items():
        if keyword in q:
            return response
    
    return {
        "spoken": f"That's a great question! Let me explain {question} in a simple way.",
        "visual_example": "Watch this demonstration to understand the concept better.",
        "remember": "Science helps us understand the world around us!"
    }


async def generate_elevenlabs_audio(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """Generate audio using ElevenLabs"""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    
    if not api_key:
        print("ElevenLabs API key not found")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"ElevenLabs Error: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f"ElevenLabs Exception: {e}")
        return None


def generate_lip_sync_data(text: str, audio_duration: float) -> dict:
    """Generate lip sync timing data based on text"""
    words = text.split()
    word_duration = audio_duration / max(len(words), 1)
    
    # Phoneme mapping for mouth shapes
    vowels = 'aeiouAEIOU'
    wide_consonants = 'mMbBpP'
    
    lip_sync = []
    current_time = 0
    
    for word in words:
        # Determine mouth shape based on word
        has_vowel = any(c in vowels for c in word)
        has_wide = any(c in wide_consonants for c in word)
        
        if has_vowel:
            shape = 'open'
        elif has_wide:
            shape = 'wide'
        else:
            shape = 'neutral'
        
        lip_sync.append({
            'word': word,
            'start': round(current_time, 2),
            'end': round(current_time + word_duration, 2),
            'shape': shape
        })
        current_time += word_duration
    
    return {
        'duration': audio_duration,
        'word_count': len(words),
        'frames': lip_sync
    }


@router.post("/ask", response_model=TeachingResponse)
async def teaching_pipeline(request: TeachingRequest):
    """
    Complete teaching pipeline:
    1. Question → LLM generates structured answer (spoken + visual_example)
    2. Voice: Teacher SPEAKS the simple answer
    3. Visual: SHOWS the example animation
    """
    start_time = time.time()
    
    # Step 1: Generate LLM response (returns dict with spoken, visual_example, remember)
    llm_response = await generate_llm_response(request.question, request.subject, request.llm_provider)
    
    # Extract parts
    spoken_answer = llm_response.get("spoken", "Let me explain this concept.")
    visual_example = llm_response.get("visual_example", "Watch this demonstration.")
    remember = llm_response.get("remember", "This is an important concept!")
    
    # Step 2: Get visual_type DIRECTLY from LLM response
    visual_type = llm_response.get("visual_type", "")
    
    # Validate visual_type - must be one of our supported animations
    valid_types = [
        "falling_object", "pendulum_swing", "wave_motion", "spring_oscillation",
        "orbital_motion", "electric_flow", "molecular_motion", "force_motion",
        "math_visual", "geometry_visual", "energy_transfer"
    ]
    
    if visual_type not in valid_types:
        # Fallback to keyword matching if LLM didn't provide valid type
        visual_type, _ = get_visual_type(request.question, visual_example)
    
    visual_description = visual_example  # Use LLM's description
    
    # Step 3: Generate audio ONLY for the spoken part (what teacher says)
    audio_bytes = None
    if request.include_avatar:
        audio_bytes = await generate_elevenlabs_audio(spoken_answer, request.voice_id)
    
    # Calculate audio duration (rough estimate: 150 words per minute)
    word_count = len(spoken_answer.split())
    estimated_duration = (word_count / 150) * 60  # seconds
    
    # Generate lip sync data for the spoken answer
    lip_sync_data = generate_lip_sync_data(spoken_answer, estimated_duration) if request.include_avatar else None
    
    processing_time = time.time() - start_time
    
    # Encode audio as base64 if available
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else None
    
    return TeachingResponse(
        question=request.question,
        spoken_answer=spoken_answer,
        visual_example=visual_example,
        remember=remember,
        audio_base64=audio_base64,
        visual_type=visual_type,
        visual_description=visual_description,
        lip_sync_data=lip_sync_data,
        processing_time=processing_time
    )


@router.post("/stream")
async def teaching_pipeline_stream(request: TeachingRequest):
    """
    Streaming teaching pipeline:
    - Voice: Teacher SPEAKS the simple answer
    - Visual: SHOWS the example animation
    """
    async def generate_events():
        start_time = time.time()
        llm_to_use = request.llm_provider or default_llm
        
        # Event: Start
        yield f"data: {json.dumps({'type': 'start', 'question': request.question, 'llm': llm_to_use})}\n\n"
        
        # Step 1: Get visual type immediately
        visual_type, visual_description = get_visual_type(request.question)
        yield f"data: {json.dumps({'type': 'visual', 'visual_type': visual_type, 'description': visual_description})}\n\n"
        
        # Step 2: Generate LLM response
        yield f"data: {json.dumps({'type': 'thinking', 'message': f'Using {llm_to_use.upper()} to generate explanation...'})}\n\n"
        
        llm_response = None
        
        # Use Gemini (default)
        if llm_to_use == "gemini" and gemini_model:
            try:
                prompt = f"""You are a friendly AI teacher. Generate a response in JSON format.

IMPORTANT LANGUAGE RULE:
- If student asks in HINDI → Reply in HINDI
- If student asks in ENGLISH → Reply in ENGLISH  
- If student asks in MIXED (Hinglish) → Reply in MIXED (Hinglish)

Choose EXACTLY ONE "visual_type" from this list based on what best explains the concept:
- "falling_object" - Apple falling (gravity, weight, Newton)
- "pendulum_swing" - Pendulum swinging (oscillation, clock)
- "wave_motion" - Wave moving (sound, light, frequency)
- "spring_oscillation" - Spring bouncing (elastic, Hooke's law)
- "orbital_motion" - Planets orbiting (solar system, earth, moon)
- "electric_flow" - Electric circuit (electricity, voltage)
- "molecular_motion" - Water molecule H2O (atoms, chemistry)
- "force_motion" - Box being pushed (force, Newton's laws)
- "math_visual" - Number blocks 2+3=5 (math, counting)
- "geometry_visual" - Rotating shapes (triangle, circle)
- "energy_transfer" - Ball on ramp (kinetic, potential energy)

{{
  "spoken": "SHORT explanation in SAME LANGUAGE as student",
  "visual_type": "EXACTLY one from above list",
  "visual_example": "Description of visual in SAME LANGUAGE",
  "remember": "Key point in SAME LANGUAGE"
}}

Student asks: {request.question}"""
                response = await asyncio.to_thread(gemini_model.generate_content, prompt)
                print(f"Gemini streaming response generated")
                
                # Parse JSON response
                import re
                text = response.text
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    llm_response = json.loads(json_match.group())
                else:
                    llm_response = {"spoken": text, "visual_example": "", "remember": "", "visual_type": "falling_object"}
            except Exception as e:
                print(f"Gemini Error: {e}")
                if openai_client:
                    llm_to_use = "openai"
                else:
                    llm_response = generate_fallback_response(request.question)
        
        # Use OpenAI
        if llm_to_use == "openai" and openai_client and not llm_response:
            try:
                response = await openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """You are a friendly AI teacher. Generate a response in JSON format.

IMPORTANT LANGUAGE RULE:
- If student asks in HINDI → Reply in HINDI
- If student asks in ENGLISH → Reply in ENGLISH  
- If student asks in MIXED (Hinglish) → Reply in MIXED (Hinglish)

Choose EXACTLY ONE "visual_type" from this list:
- "falling_object" - Apple falling (gravity, weight, Newton)
- "pendulum_swing" - Pendulum swinging (oscillation, clock)
- "wave_motion" - Wave moving (sound, light, frequency)
- "spring_oscillation" - Spring bouncing (elastic, Hooke's law)
- "orbital_motion" - Planets orbiting (solar system, earth, moon)
- "electric_flow" - Electric circuit (electricity, voltage)
- "molecular_motion" - Water molecule H2O (atoms, chemistry)
- "force_motion" - Box being pushed (force, Newton's laws)
- "math_visual" - Number blocks 2+3=5 (math, counting)
- "geometry_visual" - Rotating shapes (triangle, circle)
- "energy_transfer" - Ball on ramp (kinetic, potential energy)

{
  "spoken": "SHORT explanation in SAME LANGUAGE as student",
  "visual_type": "EXACTLY one from above list",
  "visual_example": "Description of visual in SAME LANGUAGE",
  "remember": "Key point"
}

Use VERY simple words."""},
                        {"role": "user", "content": request.question}
                    ],
                    max_tokens=300,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                llm_response = json.loads(response.choices[0].message.content)
            except Exception as e:
                print(f"OpenAI Error: {e}")
                llm_response = generate_fallback_response(request.question)
        
        # Fallback if still no response
        if not llm_response:
            llm_response = generate_fallback_response(request.question)
        
        # Extract parts from LLM response
        spoken_answer = llm_response.get("spoken", "Let me explain this concept.")
        visual_example = llm_response.get("visual_example", "Watch this demonstration.")
        remember = llm_response.get("remember", "This is important to remember!")
        
        # Get visual_type DIRECTLY from LLM response (LLM chooses the animation)
        visual_type = llm_response.get("visual_type", "")
        
        # Validate visual_type - must be one of our supported animations
        valid_types = [
            "falling_object", "pendulum_swing", "wave_motion", "spring_oscillation",
            "orbital_motion", "electric_flow", "molecular_motion", "force_motion",
            "math_visual", "geometry_visual", "energy_transfer"
        ]
        
        if visual_type not in valid_types:
            # Fallback to keyword matching if LLM didn't provide valid type
            visual_type, _ = get_visual_type(request.question, visual_example)
        
        visual_description = visual_example  # Use LLM's description
        
        # Send visual type chosen by LLM
        yield f"data: {json.dumps({'type': 'visual', 'visual_type': visual_type, 'description': visual_description})}\n\n"
        
        # Send the structured response
        yield f"data: {json.dumps({'type': 'spoken', 'content': spoken_answer})}\n\n"
        yield f"data: {json.dumps({'type': 'visual_example', 'content': visual_example})}\n\n"
        yield f"data: {json.dumps({'type': 'remember', 'content': remember})}\n\n"
        
        # Step 3: Generate audio ONLY for the spoken part
        yield f"data: {json.dumps({'type': 'generating_audio', 'message': 'Creating voice...'})}\n\n"
        
        audio_bytes = await generate_elevenlabs_audio(spoken_answer, request.voice_id)
        
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            # Calculate duration
            word_count = len(spoken_answer.split())
            estimated_duration = (word_count / 150) * 60
            
            # Generate lip sync for spoken answer
            lip_sync = generate_lip_sync_data(spoken_answer, estimated_duration)
            
            yield f"data: {json.dumps({'type': 'audio_ready', 'audio_base64': audio_base64, 'lip_sync': lip_sync})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'audio_fallback', 'message': 'Using browser TTS'})}\n\n"
        
        processing_time = time.time() - start_time
        yield f"data: {json.dumps({'type': 'complete', 'spoken_answer': spoken_answer, 'visual_example': visual_example, 'remember': remember, 'processing_time': processing_time})}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ============= DYNAMIC ANIMATION GENERATION =============

class DynamicAnimationRequest(BaseModel):
    question: str
    subject: Optional[str] = "general"
    voice_id: Optional[str] = None
    include_avatar: bool = True

ANIMATION_SYSTEM_PROMPT = """You are an AI teacher that creates educational animations. Generate a response with BOTH a spoken explanation AND a dynamic animation scene.

IMPORTANT LANGUAGE RULE:
- If student asks in HINDI → Reply in HINDI
- If student asks in ENGLISH → Reply in ENGLISH  
- If student asks in MIXED (Hinglish) → Reply in MIXED (Hinglish)

You must respond with a JSON object containing:
1. "spoken" - SHORT simple explanation (1-2 sentences) for voice
2. "animation" - A complete animation scene object

Animation Scene Format:
{
  "title": "Animation title",
  "description": "What this animation shows",
  "background": "#1a1a2e",
  "objects": [
    {
      "id": "unique_id",
      "type": "circle|rect|text|arrow|line",
      "x": number (0-400),
      "y": number (0-300),
      "radius": number (for circles),
      "width": number (for rects),
      "height": number (for rects),
      "fill": "#color",
      "color": "#color",
      "text": "text content" (for text type),
      "fontSize": number,
      "endX": number (for arrow/line),
      "endY": number (for arrow/line)
    }
  ],
  "actions": [
    {
      "objectId": "id of object to animate",
      "type": "move|rotate|bounce|swing|wave|fade|appear",
      "duration": milliseconds,
      "delay": milliseconds (optional),
      "toX": number (for move),
      "toY": number (for move),
      "toRotation": degrees (for rotate),
      "amplitude": number (for bounce/swing/wave),
      "frequency": number (for swing/wave),
      "toOpacity": 0-1 (for fade),
      "easing": "linear|easeIn|easeOut|easeInOut|bounce",
      "repeat": true/false
    }
  ],
  "labels": [
    {"text": "label", "x": number, "y": number, "color": "#fff"}
  ],
  "formula": "Mathematical formula if relevant"
}

ANIMATION EXAMPLES:

1. For GRAVITY (apple falling):
- Create tree (rect for trunk, circle for leaves)
- Create apple (red circle) at top
- Create ground (green rect)
- Create arrow showing force direction
- Action: move apple from top to ground with easeIn (accelerating fall)

2. For PENDULUM:
- Create pivot point (small circle at top)
- Create string (line from pivot)
- Create bob (circle at end)
- Action: swing the bob left-right with repeat

3. For WAVES:
- Create multiple particles (circles in a row)
- Action: wave each particle up-down with different delays

4. For MATH (2+3=5):
- Create colored blocks for numbers
- Create + and = text
- Action: appear blocks one by one

Canvas size is 400x300 pixels. Keep objects within these bounds.
Colors should be vibrant: #E53935 (red), #3498db (blue), #2ecc71 (green), #FFC107 (yellow), #9b59b6 (purple)

RESPOND ONLY IN THIS JSON FORMAT:
{
  "spoken": "Your explanation in student's language",
  "remember": "Key point to remember",
  "animation": { ...animation scene object... }
}"""


async def generate_dynamic_animation(question: str, subject: str) -> dict:
    """Generate a dynamic animation scene using LLM"""
    
    if not gemini_model:
        return None
    
    try:
        prompt = f"""{ANIMATION_SYSTEM_PROMPT}

Subject: {subject}
Student asks: {question}

Create an appropriate educational animation that visually demonstrates the concept."""

        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text
        
        # Extract JSON from response
        import re
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*"animation"[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            return result
        
        return None
    except Exception as e:
        print(f"Dynamic animation generation error: {e}")
        return None


@router.post("/stream-dynamic")
async def teaching_pipeline_dynamic(request: DynamicAnimationRequest):
    """
    Dynamic Teaching Pipeline - LLM generates custom animations in real-time
    """
    async def generate_events():
        start_time = time.time()
        
        yield f"data: {json.dumps({'type': 'start', 'question': request.question})}\n\n"
        yield f"data: {json.dumps({'type': 'thinking', 'message': 'Creating custom animation...'})}\n\n"
        
        # Generate dynamic animation from LLM
        llm_response = await generate_dynamic_animation(request.question, request.subject)
        
        if llm_response and 'animation' in llm_response:
            spoken_answer = llm_response.get('spoken', 'Let me explain this with an animation.')
            remember = llm_response.get('remember', 'This is an important concept!')
            animation_scene = llm_response.get('animation', {})
            
            # Send animation scene
            yield f"data: {json.dumps({'type': 'animation_scene', 'scene': animation_scene})}\n\n"
            yield f"data: {json.dumps({'type': 'spoken', 'content': spoken_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'remember', 'content': remember})}\n\n"
            
            # Generate audio
            if request.include_avatar:
                yield f"data: {json.dumps({'type': 'generating_audio', 'message': 'Creating voice...'})}\n\n"
                audio_bytes = await generate_elevenlabs_audio(spoken_answer, request.voice_id)
                
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    word_count = len(spoken_answer.split())
                    estimated_duration = (word_count / 150) * 60
                    lip_sync = generate_lip_sync_data(spoken_answer, estimated_duration)
                    yield f"data: {json.dumps({'type': 'audio_ready', 'audio_base64': audio_base64, 'lip_sync': lip_sync})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'audio_fallback', 'message': 'Using browser TTS'})}\n\n"
            
            processing_time = time.time() - start_time
            yield f"data: {json.dumps({'type': 'complete', 'spoken_answer': spoken_answer, 'remember': remember, 'has_animation': True, 'processing_time': processing_time})}\n\n"
        else:
            # Fallback to predefined animation
            yield f"data: {json.dumps({'type': 'fallback', 'message': 'Using predefined animation'})}\n\n"
            
            # Use the regular streaming endpoint logic as fallback
            visual_type, visual_description = get_visual_type(request.question, "")
            yield f"data: {json.dumps({'type': 'visual', 'visual_type': visual_type, 'description': visual_description})}\n\n"
            
            # Generate basic response
            llm_response = await generate_llm_response(request.question, request.subject)
            spoken_answer = llm_response.get("spoken", "Let me explain this concept.")
            remember = llm_response.get("remember", "This is important!")
            
            yield f"data: {json.dumps({'type': 'spoken', 'content': spoken_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'remember', 'content': remember})}\n\n"
            
            processing_time = time.time() - start_time
            yield f"data: {json.dumps({'type': 'complete', 'spoken_answer': spoken_answer, 'remember': remember, 'has_animation': False, 'processing_time': processing_time})}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )
