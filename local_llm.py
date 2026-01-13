import requests
import json
import os
from duckduckgo_search import DDGS

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
        self.model_name = model_name or os.getenv("LOCAL_LLM_MODEL", "qwen2.5:3b")
        self.api_url = api_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
        self.api_type = api_type or os.getenv("LOCAL_LLM_TYPE", "ollama")
        self.ddgs = DDGS()
        print(f"[LOCAL LLM] Initialized with {self.api_type} at {self.api_url} using model {self.model_name}")

    def generate_content(self, prompt):
        # Basic check for search intent in prompt (rudimentary agentic behavior)
        # In a real agent, the model would request the tool. Here we just expose the capability.
        if "[SEARCH:" in prompt:
             # Extract query? For now, this is just a placeholder for future logic.
             pass

        if self.api_type == "ollama":
            return self._call_ollama(prompt)
        elif self.api_type == "openai":
            return self._call_openai(prompt)
        else:
            print(f"[LOCAL LLM] Unknown API type: {self.api_type}")
            return None

    def search_web(self, query, max_results=3):
        """
        Performs a web search and returns a formatted string of results.
        Useful for RAG (Retrieval Augmented Generation).
        """
        print(f"[LOCAL LLM] Searching web for: {query}")
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            
            formatted_results = "Search Results:\n"
            for i, res in enumerate(results):
                formatted_results += f"{i+1}. {res['title']}: {res['body']}\n"
            return formatted_results
        except Exception as e:
            print(f"[LOCAL LLM] Search Error: {e}")
            return f"Error searching web: {e}"

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
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
            # Handle potential different response structures
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
            else:
                text = json.dumps(result) # Fallback
            return LocalLLMResponse(text)
        except Exception as e:
            print(f"[LOCAL LLM] OpenAI-Compatible Error: {e}")
            return None
