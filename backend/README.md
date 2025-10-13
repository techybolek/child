# Texas Childcare Chatbot - Backend API

FastAPI-based REST API server that wraps the existing RAG chatbot with web-accessible endpoints.

## Features

- **RESTful API** with automatic OpenAPI/Swagger documentation
- **Async processing** for handling long-running LLM calls efficiently
- **CORS support** for frontend integration
- **Request validation** using Pydantic models
- **Singleton chatbot** instance for performance
- **Error handling** with detailed error messages

## Architecture

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration settings
├── api/
│   ├── routes.py          # API endpoints
│   ├── models.py          # Pydantic schemas
│   └── middleware.py      # CORS and error handling
├── services/
│   └── chatbot_service.py # Singleton wrapper for chatbot
└── requirements.txt       # Dependencies
```

## Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required environment variables:
- `QDRANT_API_URL` - Qdrant vector database URL
- `QDRANT_API_KEY` - Qdrant API key
- `OPENAI_API_KEY` - OpenAI API key (for embeddings)
- `GROQ_API_KEY` - GROQ API key (optional, but default LLM provider)

Optional:
- `LLM_PROVIDER` - LLM provider ('groq' or 'openai', default: 'groq')
- `RERANKER_PROVIDER` - Reranker provider ('groq' or 'openai', default: 'groq')

## Running the Server

### Development Mode (with auto-reload)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Or run directly:

```bash
cd backend
python main.py
```

### Production Mode

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will start at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "chatbot_initialized": true,
  "timestamp": "2025-10-12T15:30:00Z"
}
```

### 2. Chat Query

```http
POST /api/chat
Content-Type: application/json
```

**Request:**
```json
{
  "question": "What are the income limits for a family of 3?",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "answer": "For a family of 3, the income limits are...",
  "sources": [
    {
      "doc": "Income_Guidelines.pdf",
      "page": 12,
      "url": "https://example.com/doc.pdf"
    }
  ],
  "processing_time": 3.24,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-12T15:30:05Z"
}
```

## Testing

### Using Swagger UI

1. Start the server
2. Open http://localhost:8000/docs
3. Try the `/api/health` endpoint
4. Try the `/api/chat` endpoint with a sample question

### Using curl

```bash
# Health check
curl http://localhost:8000/api/health

# Chat query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the income limits?"}'
```

### Using Python requests

```python
import requests

# Health check
response = requests.get("http://localhost:8000/api/health")
print(response.json())

# Chat query
response = requests.post(
    "http://localhost:8000/api/chat",
    json={"question": "What are the income limits?"}
)
print(response.json())
```

## Performance

- **Initialization**: ~2-5 seconds (one-time on startup)
- **API response time**: 3-6 seconds average (chatbot processing time)
- **Concurrent requests**: Handled via async FastAPI (10+ concurrent requests)

## CORS Configuration

By default, CORS is configured to allow:
- `http://localhost:3000` (Next.js development)
- `http://127.0.0.1:3000`

To add more origins, edit `backend/config.py`:

```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "https://yourdomain.com",  # Add your production domain
]
```

## Error Handling

The API provides detailed error responses:

### Validation Error (422)
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "question"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Error (500)
```json
{
  "detail": {
    "message": "Failed to generate response. Please try again.",
    "error_type": "ChatbotError"
  }
}
```

## Troubleshooting

### Chatbot Not Initializing

**Error:** `Failed to initialize chatbot`

**Solutions:**
1. Check environment variables are set correctly
2. Verify Qdrant is accessible
3. Check API keys are valid
4. Ensure parent `requirements.txt` dependencies are installed

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'chatbot'`

**Solution:** Run from project root, not from `backend/` directory:
```bash
cd /path/to/TX  # Project root
python -m uvicorn backend.main:app --reload
```

Or set PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/TX"
cd backend
uvicorn main:app --reload
```

### CORS Errors

**Error:** `Access to fetch at ... has been blocked by CORS policy`

**Solution:** Add frontend URL to `CORS_ORIGINS` in `config.py`

## Deployment

See main project documentation for deployment instructions:
- **Railway.app** (recommended for backend)
- **Render.com**
- **AWS/GCP/Azure**

## Development

### Adding New Endpoints

1. Define Pydantic models in `api/models.py`
2. Create route handler in `api/routes.py`
3. FastAPI will auto-generate documentation

### Adding Middleware

Add middleware in `main.py`:

```python
app.add_middleware(YourMiddleware, config=...)
```

## License

Part of the Texas Child Care Solutions RAG Application project.
