# Texas Child Care Solutions - Web Frontend Design
**Phase:** Architecture & Design (Web Interface)
**Date:** October 12, 2025
**Status:** 📋 Design Phase - Ready for Implementation

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Backend API Design](#backend-api-design)
5. [Frontend Design](#frontend-design)
6. [Communication Patterns](#communication-patterns)
7. [Deployment Strategy](#deployment-strategy)
8. [Implementation Plan](#implementation-plan)
9. [Technical Decisions](#technical-decisions)
10. [Security Considerations](#security-considerations)
11. [Performance Targets](#performance-targets)
12. [Testing Strategy](#testing-strategy)

---

## Executive Summary

### Objective
Transform the existing CLI-based Texas Childcare Chatbot into a production-ready web application with a modern, responsive user interface.

### Current State
- ✅ **Working RAG Pipeline:** 3-stage pipeline (Retrieval → Reranking → Generation)
- ✅ **CLI Interface:** `interactive_chat.py` and `test_chatbot.py`
- ✅ **Multi-Provider Support:** GROQ (default) and OpenAI
- ✅ **Response Format:** `{'answer': str, 'sources': [...]}`
- ✅ **Performance:** 3-6 seconds average response time

### Target State
- 🎯 **Web Interface:** Modern chat UI accessible via browser
- 🎯 **REST API:** FastAPI backend exposing chatbot functionality
- 🎯 **Real-time Feedback:** Streaming responses with progress indicators
- 🎯 **Source Citations:** Interactive display of document sources
- 🎯 **Production Ready:** Deployed on Vercel (frontend) + Railway/Render (backend)

### Design Approach
**Decoupled Architecture** - Separate backend API server and frontend application for scalability, maintainability, and independent deployment.

### Key Deliverables
1. **FastAPI Backend** (`backend/`) - REST API wrapper around existing chatbot
2. **Next.js 15 Frontend** (`frontend/`) - Modern chat interface with TypeScript and React 19
3. **API Documentation** - Auto-generated OpenAPI/Swagger docs
4. **Deployment Configuration** - Production-ready deployment setup
5. **Testing Suite** - Backend and frontend test coverage

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER BROWSER                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Next.js 15 Frontend (Port 3000)              │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  UI Components                                   │  │  │
│  │  │  - ChatInterface.tsx                             │  │  │
│  │  │  - MessageList.tsx                               │  │  │
│  │  │  - InputBar.tsx                                  │  │  │
│  │  │  - SourceCard.tsx                                │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  State Management (React Hooks)                  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  API Client (lib/api.ts)                         │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────┬───────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS (REST API)
                         │ JSON Request/Response
                         │
┌────────────────────────▼────────────────────────────────────┐
│          FastAPI Backend Server (Port 8000)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Layer (backend/api/)                             │  │
│  │  - routes.py: POST /api/chat, GET /api/health        │  │
│  │  - models.py: Pydantic request/response schemas      │  │
│  │  - middleware.py: CORS, error handling               │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │  Service Layer (backend/services/)                    │  │
│  │  - chatbot_service.py: Singleton wrapper             │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │  Existing Chatbot Module (chatbot/)                   │  │
│  │  - TexasChildcareChatbot.ask(question: str)          │  │
│  │  - Retriever → Reranker → Generator                  │  │
│  └───────────────────────┬───────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
                         │ Vector Search
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Qdrant Vector Database                     │
│  Collection: tro-child-1 (3,722 chunks)                     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User types question in browser
   ↓
2. Frontend sends POST /api/chat {"question": "..."}
   ↓
3. FastAPI receives request, validates with Pydantic
   ↓
4. ChatbotService.ask() calls TexasChildcareChatbot.ask()
   ↓
5. RAG Pipeline: Search Qdrant → Rerank → Generate Answer
   ↓
6. Response: {"answer": "...", "sources": [...], "processing_time": 3.2}
   ↓
7. Frontend displays answer with source citations
```

---

## Technology Stack

### Backend (FastAPI + Python)

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| **Framework** | FastAPI | 0.104+ | Async support, auto-docs, fast, modern Python |
| **Server** | Uvicorn | 0.24+ | ASGI server for FastAPI, production-ready |
| **Validation** | Pydantic | 2.0+ | Built into FastAPI, type-safe request/response |
| **CORS** | fastapi.middleware.cors | Built-in | Enable cross-origin requests from frontend |
| **Environment** | python-dotenv | 1.0+ | Load environment variables |

**Rationale for FastAPI:**
- ✅ Async/await support (critical for 3-6 second LLM calls)
- ✅ Auto-generated OpenAPI/Swagger documentation
- ✅ Built-in request validation with Pydantic
- ✅ WebSocket support (future: streaming responses)
- ✅ High performance (comparable to Node.js)
- ✅ Native Python integration with existing chatbot code

**Alternative Considered:** Flask
- ❌ Synchronous by default (would block on long LLM calls)
- ❌ No built-in validation
- ❌ Manual API documentation

### Frontend (Next.js + TypeScript)

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| **Framework** | Next.js | 15.5+ | Server-side rendering, App Router, Turbopack, React 19 |
| **Language** | TypeScript | 5.0+ | Type safety, better DX, catch errors early |
| **React** | React | 19.0+ | Required by Next.js 15, improved performance |
| **UI Library** | Tailwind CSS | 3.4+ | Utility-first, fast development, small bundle |
| **Components** | shadcn/ui | Latest | Accessible, customizable, copy-paste components (React 19 compatible) |
| **HTTP Client** | Fetch API | Native | No extra dependency, modern standard |
| **Markdown** | react-markdown | 9.0+ | Render formatted answers |
| **Icons** | lucide-react | Latest | Modern icon set, tree-shakable |

**Rationale for Next.js 15:**
- ✅ Server-side rendering (SSR) for fast initial page load
- ✅ App Router with React Server Components
- ✅ Built-in optimization (images, fonts, code splitting)
- ✅ TypeScript support out of the box with typed routes (stable in 15.5)
- ✅ **Turbopack stable** - 2-5x faster builds than Webpack
- ✅ **React 19 support** - Latest React features and performance
- ✅ **Improved caching control** - Explicit opt-in caching (no longer cached by default)
- ✅ API routes (optional: proxy to Python backend)
- ✅ Excellent Vercel deployment integration
- ✅ Production-ready by default

**Rationale for Tailwind + shadcn/ui:**
- ✅ Rapid UI development with utility classes
- ✅ Accessible components (WCAG compliant)
- ✅ Customizable with copy-paste approach
- ✅ No heavy component library overhead
- ✅ Modern design system

**Alternatives Considered:**
- **Create React App**: ❌ No SSR, slower initial load, deprecated
- **Material UI**: ❌ Heavy bundle size, less customizable
- **Styled Components**: ❌ Runtime CSS-in-JS overhead

**Next.js 15 Key Updates (Released October 2024, Latest: 15.5 - August 2025):**
- **Turbopack Builds**: Production builds 2-5x faster (beta in 15.5)
- **React 19 Stable**: Full support with React Compiler optimization
- **Typed Routes**: Compile-time route type safety (stable in 15.5)
- **Async Request APIs**: `cookies()`, `headers()`, `params` now async (breaking change)
- **Caching Changes**: No longer cached by default - explicit opt-in for better control
- **Node.js Middleware**: Stable runtime support (15.5)

---

## Backend API Design

### API Endpoints

#### 1. Health Check Endpoint
```http
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "chatbot_initialized": true,
  "qdrant_connected": true,
  "timestamp": "2025-10-12T15:30:00Z"
}
```

**Purpose:** Monitor backend health, verify chatbot initialization

---

#### 2. Chat Query Endpoint
```http
POST /api/chat
Content-Type: application/json
```

**Request Body:**
```json
{
  "question": "What are the income limits for a family of 3 in BCY 2026?",
  "session_id": "optional-uuid-for-conversation-tracking"
}
```

**Request Schema (Pydantic):**
```python
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = None
```

**Response (Success - 200 OK):**
```json
{
  "answer": "For BCY 2026, a family of 3 has the following income limits...",
  "sources": [
    {
      "doc": "TWC_Income_Guidelines_2026.pdf",
      "page": 12,
      "url": "https://texaschildcaresolutions.org/files/TWC_Income_Guidelines_2026.pdf"
    },
    {
      "doc": "FAQ_Eligibility.pdf",
      "page": 3,
      "url": "https://texaschildcaresolutions.org/files/FAQ_Eligibility.pdf"
    }
  ],
  "processing_time": 3.24,
  "session_id": "uuid",
  "timestamp": "2025-10-12T15:30:05Z"
}
```

**Response Schema (Pydantic):**
```python
class Source(BaseModel):
    doc: str
    page: int
    url: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    processing_time: float
    session_id: str
    timestamp: str
```

**Response (Error - 400 Bad Request):**
```json
{
  "detail": "Question must be between 1 and 500 characters"
}
```

**Response (Error - 500 Internal Server Error):**
```json
{
  "detail": "Failed to generate response. Please try again.",
  "error_type": "ChatbotError"
}
```

---

#### 3. Future: Streaming Endpoint (Phase 2)
```http
GET /api/chat/stream?question=...
Accept: text/event-stream
```

**Response (Server-Sent Events):**
```
data: {"type": "status", "message": "Searching..."}

data: {"type": "status", "message": "Reranking..."}

data: {"type": "status", "message": "Generating..."}

data: {"type": "chunk", "content": "For BCY 2026, "}

data: {"type": "chunk", "content": "a family of 3 "}

data: {"type": "sources", "sources": [...]}

data: {"type": "done"}
```

**Purpose:** Progressive feedback, perceived faster response

---

### Backend Project Structure

```
backend/
├── main.py                    # FastAPI app entry point
├── api/
│   ├── __init__.py
│   ├── routes.py             # API endpoint definitions
│   ├── models.py             # Pydantic request/response schemas
│   └── middleware.py         # CORS, error handlers, logging
├── services/
│   ├── __init__.py
│   └── chatbot_service.py    # Singleton wrapper for chatbot
├── config.py                 # API server configuration
├── requirements.txt          # FastAPI dependencies
└── .env                      # Environment variables (not committed)
```

---

### Backend Implementation Details

#### main.py - FastAPI Application
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.middleware import error_handler_middleware
from services.chatbot_service import ChatbotService

# Initialize FastAPI app
app = FastAPI(
    title="Texas Childcare Chatbot API",
    description="REST API for Texas childcare assistance chatbot",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(error_handler_middleware)

# Include API routes
app.include_router(router, prefix="/api")

# Initialize chatbot on startup (singleton pattern)
@app.on_event("startup")
async def startup_event():
    ChatbotService.get_instance()
    print("✓ Chatbot initialized")

@app.get("/")
async def root():
    return {"message": "Texas Childcare Chatbot API", "docs": "/docs"}
```

#### services/chatbot_service.py - Singleton Wrapper
```python
from chatbot.chatbot import TexasChildcareChatbot
import time

class ChatbotService:
    """Singleton wrapper for TexasChildcareChatbot"""
    _instance = None
    _chatbot = None

    @classmethod
    def get_instance(cls):
        """Get or create singleton chatbot instance"""
        if cls._instance is None:
            cls._instance = cls()
            cls._chatbot = TexasChildcareChatbot()
            print("Chatbot instance created")
        return cls._instance

    def ask(self, question: str) -> dict:
        """
        Ask chatbot a question

        Returns:
            {
                'answer': str,
                'sources': [...],
                'processing_time': float
            }
        """
        start_time = time.time()
        result = self._chatbot.ask(question)
        processing_time = time.time() - start_time

        return {
            **result,
            'processing_time': round(processing_time, 2)
        }
```

#### api/routes.py - Endpoint Definitions
```python
from fastapi import APIRouter, HTTPException
from .models import ChatRequest, ChatResponse
from services.chatbot_service import ChatbotService
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        service = ChatbotService.get_instance()
        return {
            "status": "ok",
            "chatbot_initialized": service._chatbot is not None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - ask the chatbot a question
    """
    try:
        # Get chatbot service
        service = ChatbotService.get_instance()

        # Get response
        result = service.ask(request.question)

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Return response
        return ChatResponse(
            answer=result['answer'],
            sources=result['sources'],
            processing_time=result['processing_time'],
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to generate response. Please try again.",
                "error_type": type(e).__name__
            }
        )
```

#### api/models.py - Request/Response Schemas
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's question about Texas childcare assistance"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation tracking"
    )

class Source(BaseModel):
    doc: str = Field(..., description="Document filename")
    page: int = Field(..., description="Page number")
    url: str = Field(..., description="Source URL")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Generated answer")
    sources: List[Source] = Field(..., description="Source citations")
    processing_time: float = Field(..., description="Processing time in seconds")
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="Response timestamp (ISO 8601)")
```

---

## Frontend Design

### UI/UX Design Principles

1. **Conversational Interface** - Chat-style UI familiar to users
2. **Clear Source Attribution** - Always show where answers come from
3. **Responsive Design** - Works on mobile, tablet, desktop
4. **Accessible** - WCAG 2.1 AA compliance
5. **Progressive Disclosure** - Show sources on demand, not overwhelming
6. **Loading States** - Clear feedback during 3-6 second wait

### Frontend Project Structure

```
frontend/
├── app/
│   ├── layout.tsx               # Root layout (metadata, fonts)
│   ├── page.tsx                 # Home page (chat interface)
│   ├── globals.css              # Global styles (Tailwind)
│   └── api/                     # Optional: Next.js API routes (proxy)
│       └── chat/
│           └── route.ts
├── components/
│   ├── ChatInterface.tsx        # Main chat container
│   ├── MessageList.tsx          # Scrollable message history
│   ├── MessageBubble.tsx        # Individual message (user/bot)
│   ├── SourceCard.tsx           # Source citation display
│   ├── InputBar.tsx             # Question input + submit button
│   ├── LoadingIndicator.tsx    # "Thinking..." animation
│   └── ErrorMessage.tsx         # Error display component
├── lib/
│   ├── api.ts                   # API client functions
│   ├── types.ts                 # TypeScript interfaces
│   └── utils.ts                 # Utility functions
├── public/
│   └── assets/                  # Images, icons
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── .env.local                   # Environment variables (not committed)
```

### Key Frontend Components

#### 1. ChatInterface Component
**Purpose:** Main container managing chat state

**State:**
```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  timestamp: string
  processing_time?: number
}

const [messages, setMessages] = useState<Message[]>([])
const [isLoading, setIsLoading] = useState(false)
const [error, setError] = useState<string | null>(null)
```

**Key Features:**
- Manage conversation history
- Handle API calls
- Auto-scroll to latest message
- Error handling and retry

---

#### 2. MessageList Component
**Purpose:** Scrollable list of messages

**Features:**
- Auto-scroll to bottom on new message
- Virtualized rendering (if many messages)
- Keyboard navigation
- Copy message text

---

#### 3. MessageBubble Component
**Purpose:** Individual message display

**User Message:**
```tsx
<div className="flex justify-end">
  <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-[80%]">
    {message.content}
  </div>
</div>
```

**Bot Message:**
```tsx
<div className="flex justify-start">
  <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-[80%]">
    <ReactMarkdown>{message.content}</ReactMarkdown>
    {message.sources && <SourceList sources={message.sources} />}
    <span className="text-xs text-gray-500">
      {message.processing_time}s
    </span>
  </div>
</div>
```

---

#### 4. SourceCard Component
**Purpose:** Display document sources

**Features:**
- Collapsible/expandable source list
- Links to original documents (if available)
- Page numbers
- Document icons

**Example:**
```tsx
<div className="mt-2 border-t pt-2">
  <button onClick={() => setExpanded(!expanded)}>
    📚 {sources.length} sources
  </button>
  {expanded && (
    <ul className="mt-2 space-y-1">
      {sources.map(source => (
        <li key={source.doc}>
          <a href={source.url} className="text-blue-600 hover:underline">
            {source.doc}, Page {source.page}
          </a>
        </li>
      ))}
    </ul>
  )}
</div>
```

---

#### 5. InputBar Component
**Purpose:** Question input and submit

**Features:**
- Multi-line textarea (grows with content)
- Submit on Enter (Shift+Enter for new line)
- Disabled during loading
- Character counter (500 max)
- Clear button

**Example:**
```tsx
<form onSubmit={handleSubmit} className="border-t p-4">
  <div className="flex gap-2">
    <textarea
      value={input}
      onChange={(e) => setInput(e.target.value)}
      placeholder="Ask about Texas childcare assistance..."
      className="flex-1 resize-none rounded-lg border p-2"
      rows={1}
      maxLength={500}
      disabled={isLoading}
    />
    <button
      type="submit"
      disabled={!input.trim() || isLoading}
      className="bg-blue-600 text-white px-4 py-2 rounded-lg"
    >
      {isLoading ? '...' : 'Send'}
    </button>
  </div>
  <span className="text-xs text-gray-500">{input.length}/500</span>
</form>
```

---

### API Client Implementation

#### lib/api.ts
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ChatRequest {
  question: string
  session_id?: string
}

export interface Source {
  doc: string
  page: number
  url: string
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  processing_time: number
  session_id: string
  timestamp: string
}

export async function askQuestion(
  question: string,
  sessionId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get response')
  }

  return response.json()
}

export async function checkHealth(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/health`)
  return response.json()
}
```

---

## Communication Patterns

### Phase 1: Simple REST API (MVP)

**Flow:**
```
1. User types question
2. Frontend: setIsLoading(true)
3. Frontend: await askQuestion(question)
4. Backend: processes for 3-6 seconds
5. Frontend: displays loading spinner
6. Backend: returns complete response
7. Frontend: setIsLoading(false), display answer
```

**Pros:**
- ✅ Simple implementation
- ✅ Reliable
- ✅ Easy to debug
- ✅ Works with any deployment setup

**Cons:**
- ❌ No progressive feedback
- ❌ User waits without updates

---

### Phase 2: Server-Sent Events (Streaming)

**Flow:**
```
1. User types question
2. Frontend: open EventSource connection
3. Backend: streams status updates
   - "Searching..." (1s)
   - "Reranking..." (2s)
   - "Generating..." (3-6s)
4. Backend: streams answer token-by-token (if LLM supports)
5. Backend: sends sources
6. Frontend: displays progressively
```

**Pros:**
- ✅ Better perceived performance
- ✅ User sees progress
- ✅ More engaging UX

**Cons:**
- ❌ More complex implementation
- ❌ Requires streaming support from LLM

**Implementation:**
```typescript
// Frontend
const eventSource = new EventSource(
  `${API_URL}/api/chat/stream?question=${encodeURIComponent(question)}`
)

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)

  switch (data.type) {
    case 'status':
      setStatus(data.message)
      break
    case 'chunk':
      appendToAnswer(data.content)
      break
    case 'sources':
      setSources(data.sources)
      break
    case 'done':
      eventSource.close()
      setIsLoading(false)
      break
  }
}
```

---

## Deployment Strategy

### Development Environment

```bash
# Terminal 1: Backend
cd backend/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend/
npm install
npm run dev  # Port 3000

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production Deployment Options

#### Option 1: Separate Deployment (Recommended)

**Backend: Railway.app or Render.com**
- Deploy FastAPI backend
- Configure environment variables (QDRANT_API_URL, API keys)
- Automatic HTTPS
- Backend URL: https://api.yourdomain.com

**Frontend: Vercel**
- Deploy Next.js frontend
- Configure NEXT_PUBLIC_API_URL=https://api.yourdomain.com
- Automatic HTTPS, CDN, edge caching
- Frontend URL: https://yourdomain.com

**Pros:**
- ✅ Optimal for each stack (Vercel excels at Next.js)
- ✅ Independent scaling
- ✅ CDN for frontend assets
- ✅ Easy rollbacks

**Cons:**
- ❌ Requires CORS configuration
- ❌ Two separate services to manage

---

#### Option 2: Monorepo on Single Server

**Platform: DigitalOcean Droplet, AWS EC2, or similar**
- Host both backend and frontend on same machine
- Nginx reverse proxy: `/api/*` → FastAPI, `/*` → Next.js
- Single domain, no CORS issues

**Pros:**
- ✅ Simpler deployment (one service)
- ✅ No CORS configuration needed
- ✅ Lower cost (single server)

**Cons:**
- ❌ Manual server management
- ❌ Cannot scale independently
- ❌ No CDN optimization

---

#### Option 3: Containerized Deployment

**Platform: Docker + Docker Compose → Fly.io, Railway, or AWS ECS**

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - QDRANT_API_URL=${QDRANT_API_URL}
      - GROQ_API_KEY=${GROQ_API_KEY}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

**Pros:**
- ✅ Reproducible deployments
- ✅ Easy local development
- ✅ Portable across cloud providers

**Cons:**
- ❌ More complex setup
- ❌ Requires Docker knowledge

---

### Recommended Production Setup

**For MVP:**
- **Backend:** Railway.app (easy Python deployment, free tier available)
- **Frontend:** Vercel (best-in-class Next.js hosting, free tier available)

**Rationale:**
- Railway has excellent Python/FastAPI support
- Vercel is optimized for Next.js (automatic edge caching)
- Both have free tiers for testing
- Both provide automatic HTTPS
- Easy to upgrade as traffic grows

---

## Implementation Plan

### Phase 1: MVP - Core Functionality (2-3 days)

**Backend Tasks:**
1. Create `backend/` directory structure
2. Implement FastAPI app (`main.py`)
3. Create API routes (`api/routes.py`)
4. Define Pydantic models (`api/models.py`)
5. Create chatbot service wrapper (`services/chatbot_service.py`)
6. Add CORS middleware
7. Test endpoints with Swagger docs
8. Write unit tests for API endpoints

**Frontend Tasks:**
1. Initialize Next.js 15 project with TypeScript and React 19
2. Set up Tailwind CSS + shadcn/ui
3. Create ChatInterface component
4. Create MessageList component
5. Create MessageBubble component
6. Create InputBar component
7. Implement API client (`lib/api.ts`)
8. Wire up components with state management
9. Add loading states
10. Test end-to-end flow

**Deliverable:** Working web chatbot with same functionality as CLI

---

### Phase 2: UX Enhancements (1-2 days)

1. Add streaming responses (SSE)
2. Implement progressive status updates ("Searching...", "Reranking...", "Generating...")
3. Improve source citation display (collapsible cards with icons)
4. Add markdown rendering for formatted answers
5. Implement conversation history (localStorage)
6. Add "Copy to clipboard" for answers
7. Add "Clear conversation" button
8. Improve loading animations
9. Add error boundaries
10. Mobile responsiveness testing

**Deliverable:** Production-ready UX

---

### Phase 3: Deployment & Testing (1 day)

1. Deploy backend to Railway
2. Deploy frontend to Vercel
3. Configure environment variables
4. Set up custom domain (optional)
5. End-to-end testing in production
6. Performance testing (load times, API response times)
7. Cross-browser testing
8. Accessibility audit (Lighthouse, axe)
9. Write deployment documentation

**Deliverable:** Live production application

---

### Phase 4: Advanced Features (Optional - Future)

1. Multi-turn conversation with context memory
2. User authentication (NextAuth.js)
3. Conversation history saved to database
4. User feedback (thumbs up/down on answers)
5. Admin dashboard (usage analytics)
6. Export conversation as PDF
7. Rate limiting per user
8. Search conversation history
9. Share conversation via URL
10. Dark mode

---

## Technical Decisions

### 1. Why FastAPI over Flask?

| Feature | FastAPI | Flask |
|---------|---------|-------|
| Async support | ✅ Native | ❌ Requires extensions |
| Request validation | ✅ Pydantic | ❌ Manual or Flask-Pydantic |
| API documentation | ✅ Auto-generated | ❌ Manual or Swagger extension |
| Performance | ✅ High (Starlette) | ❌ Lower (WSGI) |
| WebSocket support | ✅ Built-in | ❌ Flask-SocketIO needed |
| Type hints | ✅ Required | ❌ Optional |

**Decision:** FastAPI - Better suited for async LLM calls, auto-docs, and future streaming

---

### 2. Why Next.js 15 over Create React App?

| Feature | Next.js 15 | Create React App |
|---------|-----------|------------------|
| SSR/SSG | ✅ Built-in | ❌ Client-only |
| API routes | ✅ Built-in | ❌ Separate backend |
| Production optimizations | ✅ Automatic | ❌ Manual |
| TypeScript | ✅ Zero-config + typed routes | ❌ Manual setup |
| Build speed | ✅ Turbopack (2-5x faster) | ❌ Webpack (slower) |
| Deployment | ✅ Vercel optimized | ❌ Generic static host |
| Image optimization | ✅ Built-in | ❌ Manual |
| React version | ✅ React 19 | ❌ React 18 (outdated) |
| Maintenance | ✅ Active development | ❌ Deprecated (2023) |

**Decision:** Next.js 15 - Production-ready, superior performance with Turbopack, active maintenance, React 19 support

---

### 3. Why Tailwind + shadcn/ui over Material UI?

| Feature | Tailwind + shadcn/ui | Material UI |
|---------|---------------------|-------------|
| Bundle size | ✅ Small (tree-shakable) | ❌ Large (~300KB) |
| Customization | ✅ Full control | ❌ Complex theming |
| Learning curve | ✅ Moderate | ❌ Steep |
| Design flexibility | ✅ Unlimited | ❌ Material Design patterns |
| Accessibility | ✅ Built-in (Radix) | ✅ Built-in |

**Decision:** Tailwind + shadcn/ui - Lightweight, customizable, modern

---

### 4. Why REST API first, then SSE?

**Phase 1 (REST):**
- ✅ Simple implementation (2-3 days)
- ✅ Easy to test and debug
- ✅ Works with any deployment
- ✅ Get MVP to users faster

**Phase 2 (SSE):**
- ✅ Better UX (progressive feedback)
- ✅ Not critical for MVP
- ✅ Can be added incrementally

**Decision:** Start simple (REST), enhance later (SSE)

---

### 5. Why separate backend/frontend deployment?

**Pros:**
- ✅ Independent scaling (frontend static, backend compute-heavy)
- ✅ Vercel's edge network for frontend (faster global access)
- ✅ Can upgrade backend without redeploying frontend
- ✅ Better separation of concerns

**Cons:**
- ❌ Requires CORS configuration (one-time setup)
- ❌ Two services to manage (mitigated by PaaS platforms)

**Decision:** Separate deployment - Benefits outweigh complexity

---

## Security Considerations

### Backend Security

1. **API Keys Never Exposed**
   - Store in backend environment variables only
   - Never send to frontend
   - Use server-side API calls only

2. **CORS Configuration**
   - Whitelist specific frontend domains
   - No wildcard `*` in production

3. **Rate Limiting** (Future)
   - Prevent abuse (e.g., 10 requests/minute per IP)
   - Use `slowapi` library

4. **Input Validation**
   - Pydantic validates all requests
   - Sanitize user input before sending to LLM

5. **Error Messages**
   - Don't expose internal errors to users
   - Log detailed errors server-side only

### Frontend Security

1. **Environment Variables**
   - Only `NEXT_PUBLIC_*` vars accessible in browser
   - Never store API keys in frontend

2. **Content Security Policy (CSP)**
   - Restrict script sources
   - Prevent XSS attacks

3. **XSS Prevention**
   - Use `react-markdown` for rendering (auto-escapes)
   - Never use `dangerouslySetInnerHTML`

4. **HTTPS Only**
   - Enforce HTTPS in production
   - Vercel provides automatic HTTPS

---

## Performance Targets

### Backend Performance

| Metric | Target | Notes |
|--------|--------|-------|
| API response time | 3-6 seconds | Chatbot processing time (not API overhead) |
| Health check | < 100ms | Simple status check |
| Memory usage | < 512MB | Chatbot instance + FastAPI |
| Concurrent requests | 10+ | FastAPI async handles multiple requests |

### Frontend Performance

| Metric | Target | Notes |
|--------|--------|-------|
| First Contentful Paint | < 1s | Initial page load |
| Time to Interactive | < 2s | Ready for user input |
| Bundle size (JS) | < 200KB | Code-splitting with Next.js |
| Lighthouse score | 90+ | Performance, Accessibility, Best Practices |

### Network Performance

| Metric | Target | Notes |
|--------|--------|-------|
| API payload size | < 50KB | Typical response with sources |
| Frontend asset size | < 500KB | Initial page load |
| CDN cache hit rate | > 90% | Vercel edge caching |

---

## Testing Strategy

### Backend Testing

**Unit Tests (pytest):**
```python
# test_routes.py
def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_chat_endpoint():
    response = client.post("/api/chat", json={
        "question": "What are income limits?"
    })
    assert response.status_code == 200
    assert "answer" in response.json()
    assert "sources" in response.json()

def test_chat_validation():
    response = client.post("/api/chat", json={
        "question": ""  # Empty question
    })
    assert response.status_code == 422  # Validation error
```

**Integration Tests:**
- Test chatbot service wrapper
- Test end-to-end flow with real Qdrant

**Load Tests (Locust):**
- Simulate 10 concurrent users
- Measure response time under load

---

### Frontend Testing

**Unit Tests (Jest + React Testing Library):**
```typescript
// MessageBubble.test.tsx
test('renders user message', () => {
  const message = {
    id: '1',
    role: 'user',
    content: 'Test question',
    timestamp: '2025-10-12T15:30:00Z'
  }

  render(<MessageBubble message={message} />)
  expect(screen.getByText('Test question')).toBeInTheDocument()
})

test('renders bot message with sources', () => {
  const message = {
    id: '2',
    role: 'assistant',
    content: 'Test answer',
    sources: [{ doc: 'test.pdf', page: 1, url: 'https://...' }],
    timestamp: '2025-10-12T15:30:05Z'
  }

  render(<MessageBubble message={message} />)
  expect(screen.getByText('Test answer')).toBeInTheDocument()
  expect(screen.getByText(/1 sources/)).toBeInTheDocument()
})
```

**E2E Tests (Playwright):**
```typescript
test('user can ask question and get answer', async ({ page }) => {
  await page.goto('http://localhost:3000')

  // Type question
  await page.fill('textarea', 'What are income limits?')
  await page.click('button[type="submit"]')

  // Wait for response
  await page.waitForSelector('.bot-message', { timeout: 10000 })

  // Verify answer and sources
  const answer = await page.textContent('.bot-message')
  expect(answer).toContain('income limits')

  const sources = await page.locator('.source-card').count()
  expect(sources).toBeGreaterThan(0)
})
```

**Accessibility Tests (axe-core):**
```typescript
test('chat interface is accessible', async () => {
  const { container } = render(<ChatInterface />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Backend API timeout | High | Add timeout handling, retry logic |
| LLM API failures | High | Graceful error messages, fallback responses |
| Slow response time | Medium | Loading indicators, streaming (Phase 2) |
| CORS issues | Medium | Test thoroughly before deployment |
| High traffic costs | Low | Monitor usage, implement rate limiting |

### User Experience Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| User expects instant response | Medium | Clear "Thinking..." indicator (3-6s is normal) |
| Confusing source citations | Low | Clear UI with document names and page numbers |
| Mobile usability | Medium | Responsive design, touch-friendly targets |
| Browser compatibility | Low | Next.js handles polyfills automatically |

---

## Success Metrics

### MVP Success Criteria

- ✅ User can ask questions and receive answers via web interface
- ✅ Source citations displayed for every answer
- ✅ Average response time < 10 seconds (3-6s chatbot + API overhead)
- ✅ Mobile-responsive design
- ✅ Error handling for failed requests
- ✅ Deployed to production (accessible via URL)

### Phase 2 Success Criteria

- ✅ Streaming responses with progressive status updates
- ✅ Lighthouse score > 90
- ✅ Conversation history persists in browser
- ✅ Accessibility audit passes (WCAG 2.1 AA)

---

## Maintenance Plan

### Monitoring

1. **Backend Monitoring:**
   - API response times (Railway/Render built-in metrics)
   - Error rates
   - Uptime monitoring (UptimeRobot or similar)

2. **Frontend Monitoring:**
   - Vercel Analytics (automatic)
   - Core Web Vitals
   - Error tracking (Sentry optional)

### Updates

1. **Dependency Updates:**
   - Monthly: `pip install --upgrade` (backend)
   - Monthly: `npm update` (frontend)
   - Review security advisories

2. **Content Updates:**
   - If PDFs change, re-run `load_pdf_qdrant.py`
   - No code changes needed for content updates

---

## Next Steps

### Immediate Actions (Before Coding)

1. ✅ Review and approve this design document
2. ⬜ Set up GitHub repository structure:
   ```
   TX/
   ├── backend/
   ├── frontend/
   ├── chatbot/  (existing)
   └── SPECS/
   ```
3. ⬜ Create feature branch: `git checkout -b feature/web-frontend`
4. ⬜ Initialize backend: `mkdir backend && cd backend && touch main.py`
5. ⬜ Initialize frontend:
   ```bash
   # Next.js 15 with TypeScript, Tailwind, App Router
   npx create-next-app@latest frontend --typescript --tailwind --app

   # OR specify exact version
   npx create-next-app@15 frontend --typescript --tailwind --app
   ```

### Phase 1 Kickoff (Day 1)

1. Backend: Implement basic FastAPI app with `/api/health` and `/api/chat`
2. Frontend: Create basic chat UI with MessageList and InputBar
3. Test API connection
4. Iterate on UI

---

## Appendix: Additional Resources

### Documentation Links

- **FastAPI:** https://fastapi.tiangolo.com/
- **Next.js 15:** https://nextjs.org/docs
- **Next.js 15 Blog:** https://nextjs.org/blog/next-15
- **React 19:** https://react.dev/blog/2024/12/05/react-19
- **Tailwind CSS:** https://tailwindcss.com/docs
- **shadcn/ui:** https://ui.shadcn.com/
- **Vercel Deployment:** https://vercel.com/docs
- **Railway Deployment:** https://docs.railway.app/

### Example Code Repositories

- FastAPI + Next.js Starter: https://github.com/tiangolo/full-stack-fastapi-template
- Next.js Chat UI: https://github.com/vercel/ai-chatbot

---

## Conclusion

This design provides a comprehensive roadmap for adding a production-ready web frontend to the existing Texas Childcare Chatbot. The decoupled architecture with FastAPI (backend) and Next.js 15 (frontend) ensures:

- **Scalability:** Independent scaling of compute-heavy backend and static frontend
- **Maintainability:** Clear separation of concerns, well-documented API
- **Performance:** Async backend, edge-cached frontend, streaming in Phase 2
- **User Experience:** Modern chat interface, source citations, responsive design
- **Developer Experience:** Type safety (TypeScript/Pydantic), auto-generated docs, fast local development

**Recommended Approach:** Start with Phase 1 MVP (REST API + basic UI) to validate the approach, then iterate with Phase 2 enhancements (streaming, UX polish) based on user feedback.

---

**Status:** Ready for implementation approval ✅

**Estimated Timeline:** 4-6 days (MVP + Enhancements + Deployment)

**Team Required:** 1 full-stack developer (Python + TypeScript)

---

*Last Updated: October 12, 2025*
