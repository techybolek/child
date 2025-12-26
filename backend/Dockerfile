FROM python:3.11-slim

WORKDIR /app

# Copy requirements file
COPY backend/requirements.txt ./requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary application code
COPY backend ./backend/
COPY chatbot ./chatbot/
COPY LOAD_DB ./LOAD_DB/

# Set Python path for imports
ENV PYTHONPATH=/app

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
