# AI Teacher Python Backend

🎓 An intelligent educational backend that provides **real-time live teaching** with AI-powered explanations, visual demonstrations, and interactive avatar responses.

## ✨ Features

- **🔴 Live Teaching**: Real-time streaming responses word-by-word like a live teacher
- **🤖 AI-Powered Explanations**: Uses GPT-4 to generate comprehensive, grade-appropriate explanations
- **🎬 Visual Demonstrations**: Automatic generation of animations (using Manim), images, and diagrams
- **👤 Avatar Responses**: Interactive avatar videos with text-to-speech (ElevenLabs + D-ID/HeyGen)
- **📚 Learning History**: Track questions and learning progress
- **🔐 Authentication**: JWT-based authentication with role support (student/teacher/admin)
- **💬 WebSocket Support**: Real-time bi-directional communication for live classrooms

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Question                              │
│                    "What is gravity?"                             │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Question Processor                              │
├─────────────────────────────────────────────────────────────────┤
│  1. Analyze Question (determine subject, topic, difficulty)      │
│  2. Generate Explanation (GPT-4)                                 │
│  3. Generate Visual (Manim animations / AI images)               │
│  4. Generate Avatar Video (ElevenLabs TTS + D-ID/HeyGen)         │
└───────────┬───────────────────┬───────────────────┬─────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌───────────────────┐ ┌─────────────────┐ ┌───────────────────┐
│  AI Explanation   │ │  Visual Service │ │  Avatar Service   │
│    Service        │ │                 │ │                   │
│                   │ │  - Manim        │ │  - ElevenLabs TTS │
│  - OpenAI GPT-4   │ │  - Stability AI │ │  - D-ID / HeyGen  │
│  - Analysis       │ │  - Templates    │ │  - gTTS fallback  │
│  - Explanation    │ │                 │ │                   │
└───────────────────┘ └─────────────────┘ └───────────────────┘
            │                   │                   │
            └───────────────────┴───────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Response                                   │
│  - Text explanation                                               │
│  - Visual demonstration (animation/image URL)                     │
│  - Avatar video URL                                               │
│  - Related concepts & follow-up questions                         │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- MongoDB
- Redis (optional, for caching/queues)
- API Keys for:
  - OpenAI (required)
  - ElevenLabs (optional, for high-quality TTS)
  - D-ID or HeyGen (optional, for avatar videos)
  - Stability AI or Replicate (optional, for image generation)

### Installation

1. **Clone and navigate to the backend**
   ```bash
   cd backend-ai-teacher-python
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the server**
   ```bash
   python run.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the API**
   - API Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health
   - **Live Demo**: http://localhost:8000/static/live_classroom.html

## 🔴 Real-Time Live Teaching

The backend supports **real-time streaming** for a live teaching experience:

### WebSocket Connection

```javascript
// Connect to live classroom
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/classroom/my-session');

ws.onopen = () => {
    // Ask a question
    ws.send(JSON.stringify({
        type: 'ask_question',
        question: 'What is gravity?',
        subject: 'physics'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'text':
            // Word-by-word streaming
            console.log(data.content);
            break;
        case 'visual_cue':
            // Show animation/visual
            console.log('Show visual:', data.action, data.data);
            break;
        case 'emphasis':
            // Highlight important word
            console.log('Important:', data.word);
            break;
        case 'complete':
            // Teaching finished
            console.log('Full explanation:', data.full_text);
            break;
    }
};
```

### HTTP Streaming (SSE)

```javascript
// Alternative: Server-Sent Events for simpler clients
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
    
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const event = JSON.parse(line.slice(6));
            console.log(event);
        }
    }
}
```

## API Endpoints

### Questions (Batch Processing)
- `POST /api/v1/questions/ask` - Ask question & get complete response
- `GET /api/v1/questions/{id}` - Get question response
- `GET /api/v1/questions/{id}/status` - Check processing status

### 🔴 Live Teaching (Real-Time)
- `WebSocket /api/v1/ws/classroom/{session_id}` - Join live classroom
- `WebSocket /api/v1/ws/teach` - Quick one-on-one teaching
- `POST /api/v1/sessions/create` - Create new classroom session
- `GET /api/v1/sessions/{id}/status` - Get session status

### Streaming (SSE)
- `POST /api/v1/stream/ask` - Stream answer via SSE
- `GET /api/v1/stream/ask` - Stream answer (GET method)
- `POST /api/v1/stream/ask-with-audio` - Stream with audio chunks

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `PUT /api/v1/auth/me` - Update profile

### Avatars
- `GET /api/v1/avatars/options` - Get available avatars/voices
- `POST /api/v1/avatars/preview` - Preview avatar with sample text
- `POST /api/v1/avatars/generate-audio` - Generate audio only

### Visuals
- `POST /api/v1/visuals/generate` - Generate a visual
- `GET /api/v1/visuals/{visual_id}` - Get visual by ID
- `GET /api/v1/visuals/search/concept` - Search visuals by concept
- `GET /api/v1/visuals/templates/list` - List visual templates

## Example Usage

### Ask a Question

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/questions/ask",
    json={
        "question": "What is gravity?",
        "subject": "physics",
        "include_visual": True,
        "include_avatar": True
    }
)

result = response.json()
print(f"Explanation: {result['explanation']}")
print(f"Visual URL: {result['visual_url']}")
print(f"Avatar Video: {result['avatar_video_url']}")
```

### Response Example

```json
{
  "question_id": "65f1234567890abcdef12345",
  "question": "What is gravity?",
  "explanation": "Gravity is a fundamental force of nature that attracts objects with mass toward each other. On Earth, gravity pulls everything toward the center of the planet at approximately 9.8 m/s²...",
  "visual_type": "animation",
  "visual_url": "/media/animations/GravityScene.mp4",
  "visual_description": "An animation showing an apple falling from a tree to demonstrate gravity",
  "avatar_video_url": "/media/video/gravity_avatar.mp4",
  "audio_url": "/media/audio/gravity_explanation.mp3",
  "keywords": ["gravity", "force", "mass", "acceleration", "Newton"],
  "related_concepts": ["Newton's Laws", "Free Fall", "Weight vs Mass"],
  "follow_up_questions": [
    "How does gravity work on the Moon?",
    "Why do objects fall at the same speed regardless of mass?",
    "What is the difference between weight and mass?"
  ],
  "status": "completed"
}
```

## Project Structure

```
backend-ai-teacher-python/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings/configuration
│   │   ├── database.py      # MongoDB connection
│   │   └── security.py      # Authentication
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   ├── question.py      # Question models
│   │   ├── visual.py        # Visual models
│   │   └── course.py        # Course models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── question.py      # Request/Response schemas
│   │   └── user.py          # User schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_explanation.py    # GPT-4 integration
│   │   ├── visual_generation.py # Manim/image generation
│   │   ├── avatar_service.py    # TTS & avatar video
│   │   └── question_processor.py # Main orchestrator
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           ├── questions.py
│           ├── auth.py
│           ├── avatars.py
│           └── visuals.py
├── media/                   # Generated media files
├── logs/                    # Application logs
├── requirements.txt
├── run.py
├── .env.example
└── README.md
```

## Visual Generation

The backend supports multiple types of visual demonstrations:

### 1. Manim Animations (Recommended for Physics/Math)
- Pre-built templates for common concepts (gravity, pendulum, waves, etc.)
- AI-generated custom Manim code for specific concepts
- High-quality mathematical animations

### 2. AI-Generated Images
- Uses Stability AI or Replicate for image generation
- Suitable for diagrams, illustrations, and static visuals

### 3. Template-Based Visuals
- Pre-defined visual templates for common educational concepts
- Customizable parameters for specific use cases

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `MONGO_URI` | MongoDB connection string | Yes |
| `JWT_SECRET` | Secret key for JWT tokens | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | No |
| `DID_API_KEY` | D-ID API key for avatar videos | No |
| `HEYGEN_API_KEY` | HeyGen API key for avatar videos | No |
| `STABILITY_API_KEY` | Stability AI for image generation | No |
| `REPLICATE_API_TOKEN` | Replicate for image generation | No |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
