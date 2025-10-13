#!/bin/bash
# Test script for Docker deployment

set -e

echo "=================================="
echo "Texas Childcare Docker Test Script"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not available"
    echo "Please install Docker Desktop and enable WSL 2 integration"
    exit 1
fi

print_success "Docker is available"

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    print_error ".env.docker file not found"
    echo "Creating from example..."
    cp .env.docker.example .env.docker
    print_info "Please edit .env.docker with your API keys before running containers"
    exit 1
fi

print_success ".env.docker file exists"

# Build containers
echo ""
print_info "Building Docker images..."
docker compose build

print_success "Docker images built successfully"

# Start containers
echo ""
print_info "Starting containers..."
docker compose up -d

print_success "Containers started"

# Wait for backend to be ready
echo ""
print_info "Waiting for backend to be ready..."
sleep 10

# Test backend health endpoint
echo ""
print_info "Testing backend health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/health || echo "failed")

if [[ $HEALTH_RESPONSE == *"ok"* ]]; then
    print_success "Backend health check passed"
else
    print_error "Backend health check failed"
    echo "Response: $HEALTH_RESPONSE"
    docker compose logs backend
    exit 1
fi

# Test backend chat endpoint
echo ""
print_info "Testing chatbot query..."
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"question": "What is the income limit for CCAP?"}' || echo "failed")

if [[ $CHAT_RESPONSE == *"answer"* ]]; then
    print_success "Chatbot query successful"
    echo "Sample answer: $(echo $CHAT_RESPONSE | grep -o '"answer":"[^"]*"' | head -c 100)..."
else
    print_error "Chatbot query failed"
    echo "Response: $CHAT_RESPONSE"
    exit 1
fi

# Test frontend accessibility
echo ""
print_info "Testing frontend accessibility..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "failed")

if [[ $FRONTEND_RESPONSE == "200" ]]; then
    print_success "Frontend is accessible"
else
    print_error "Frontend check failed (HTTP $FRONTEND_RESPONSE)"
fi

# Show container status
echo ""
print_info "Container status:"
docker compose ps

# Summary
echo ""
echo "=================================="
echo "✓ All tests passed!"
echo "=================================="
echo ""
echo "Services running at:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "To view logs:     docker compose logs -f"
echo "To stop:          docker compose down"
echo "To restart:       docker compose restart"
echo ""
