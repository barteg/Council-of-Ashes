import requests
import json
import os

class LocalLLMResponse:
    def __init__(self, text):
        self.candidates = [LocalLLMCandidate(text)]
        self.prompt_feedback = "Local LLM - No feedback"

    def __repr__(self):
        return f"LocalLLMResponse(text={self.candidates[0].content.parts[0].text[:50]}...)"

class LocalLLMCandidate:
    def __init__(self, text):
        self.content = LocalLLMContent(text)
        self.finish_reason = "STOP"
        self.safety_ratings = []

class LocalLLMContent:
    def __init__(self, text):
        self.parts = [LocalLLMPart(text)]

class LocalLLMPart:
    def __init__(self, text):
        self.text = text

class LocalLLMClient:
    def __init__(self, model_name=None, api_url=None, api_type="ollama"):
        """
        api_type: 'ollama' or 'openai'
        """
        self.model_name = model_name or os.getenv("LOCAL_LLM_MODEL", "llama3")
        self.api_url = api_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
        self.api_type = api_type or os.getenv("LOCAL_LLM_TYPE", "ollama")
        print(f"[LOCAL LLM] Initialized with {self.api_type} at {self.api_url} using model {self.model_name}")

    def generate_content(self, prompt):
        if self.api_type == "ollama":
            return self._call_ollama(prompt)
        elif self.api_type == "openai":
            return self._call_openai(prompt)
        else:
            print(f"[LOCAL LLM] Unknown API type: {self.api_type}")
            return None

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            text = result.get("response", "")
            return LocalLLMResponse(text)
        except Exception as e:
            print(f"[LOCAL LLM] Ollama Error: {e}")
            return None

    def _call_openai(self, prompt):
        # API URL for OpenAI type should typically end in /v1/chat/completions
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": { "type": "json_object" }
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            text = result['choices'][0]['message']['content']
            return LocalLLMResponse(text)
        except Exception as e:
            print(f"[LOCAL LLM] OpenAI-Compatible Error: {e}")
            return None
