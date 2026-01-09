# PostQode Agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Set environment variables
ENV POSTQODE_MARKETPLACE_URL=http://host.docker.internal:8000
ENV POSTQODE_AGENT_PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run agent
CMD ["python", "agent.py"]
