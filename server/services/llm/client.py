import requests
import json
import os
import subprocess

class GeminiCLIClient:
    def __init__(self, model_name=None):
        self.model_name = model_name

    def generate_content(self, prompt):
        print(f"[GEMINI CLI] Generating content with model {self.model_name if self.model_name else 'default'}")
        try:
            cmd = ["gemini", prompt, "-o", "json"]
            if self.model_name:
                cmd.extend(["-m", self.model_name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = json.loads(result.stdout)
            text = output.get("response", "")
            return LocalLLMResponse(text)
        except Exception as e:
            print(f"[GEMINI CLI] Error: {e}")
            if hasattr(e, 'stderr'):
                print(f"[GEMINI CLI] Stderr: {e.stderr}")
            return None

class OllamaClient:
    def __init__(self, model_name="qwen2.5:7b", url="http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.url = url
        print(f"[OLLAMA] Initialized with model {self.model_name} at {self.url}")

    def generate_content(self, prompt):
        print(f"[OLLAMA] Generating content with model {self.model_name}")
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json" # Ollama support for JSON mode
            }
            response = requests.post(self.url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            text = data.get("response", "")
            return LocalLLMResponse(text)
        except Exception as e:
            print(f"[OLLAMA] Error: {e}")
            return None

class LocalLLMResponse:
    def __init__(self, text):
        self.candidates = [LocalLLMCandidate(text)]
        self.prompt_feedback = "Local LLM Feedback"

class LocalLLMCandidate:
    def __init__(self, text):
        self.content = LocalLLMContent(text)
        self.finish_reason = 'STOP'
        self.safety_ratings = []

class LocalLLMContent:
    def __init__(self, text):
        self.parts = [LocalLLMPart(text)]

class LocalLLMPart:
    def __init__(self, text):
        self.text = text
