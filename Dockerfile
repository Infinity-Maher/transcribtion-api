# Use an official, lightweight Python image
FROM python:3.11-slim

# Ensures Python logs appear immediately in Google Cloud Console
ENV PYTHONUNBUFFERED=True

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Start the FastAPI server using Uvicorn
# Cloud Run automatically injects a dynamic $PORT variable
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}