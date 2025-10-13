# Texas Childcare Chatbot - Frontend

Modern, responsive web interface for the Texas Childcare assistance chatbot, built with Next.js 15, TypeScript, React 19, and Tailwind CSS.

## Quick Start

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Features

- Modern chat interface with message bubbles
- Real-time API responses with loading indicators
- Collapsible source citations
- Markdown rendering for formatted answers
- Full TypeScript type safety
- Responsive design (mobile, tablet, desktop)
- Error handling with retry functionality

## Technology Stack

- Next.js 15.5 with App Router and Turbopack
- React 19
- TypeScript
- Tailwind CSS
- react-markdown

## Project Structure

```
frontend/
├── app/              # Next.js App Router pages
├── components/       # React components
├── lib/             # API client, types, utilities
└── public/          # Static assets
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000` by default. Configure with `NEXT_PUBLIC_API_URL` in `.env.local`.

## Documentation

See detailed documentation in this README for:
- Component architecture
- API integration
- Styling guidelines
- Deployment instructions

For backend documentation, see `../backend/README.md`.
