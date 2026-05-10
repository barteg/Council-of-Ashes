#!/bin/bash

# 1. LLM Configuration
export USE_LOCAL_LLM=true
export LOCAL_LLM_MODEL="qwen2.5:3b"
# export LOCAL_LLM_URL="http://localhost:11434/api/generate"
export OLLAMA_MODELS="$(pwd)/models"

# 2. Flask Configuration
export FLASK_APP=app.py
export FLASK_ENV=development
export ENABLE_TTS=true
# Ensure you have your Gemini key set here
# export GEMINI_API_KEY="your_key_here"

# 3. Start Ollama
if ! pgrep -x "ollama" > /dev/null
then
    echo "[Ollama] Starting server using models in $(pwd)/models..."
    ollama serve > /dev/null 2>&1 &
    sleep 5
else
    echo "[Ollama] Server already running."
fi

# 4. Start the Flask application
echo "[Game] Starting The Council of Ashes with Local LLM..."
python app.py