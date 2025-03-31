# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py scheduler.py start.sh challenges.json ./

# Make start script executable
RUN chmod +x start.sh

# Create volume for persistent database storage
VOLUME /app/data

# Command to run the application
CMD ["./start.sh"]
