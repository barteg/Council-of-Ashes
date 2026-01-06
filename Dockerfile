# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for TTS and other potential libraries
# (e.g., sound libraries, git for TTS cloning if needed, though we'll copy it directly)
RUN apt-get update && apt-get install -y \
    git \
    libsndfile1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . .

# Ensure the tts_models directory is present
# The model itself is large, so this will make the image large.
# This assumes 'tts_models' is in the root of your project directory.
COPY tts_models ./tts_models

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
