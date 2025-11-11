"""
Model Backends - Support for multiple AI models (API and Local)
"""
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from django.core.exceptions import ValidationError

# ============================================================================
# BASE MODEL INTERFACE
# ============================================================================

class BaseModelBackend(ABC):
    """Abstract base class for all model backends"""
    
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if model is available"""
        pass


# ============================================================================
# GEMINI API BACKEND
# ============================================================================

class GeminiBackend(BaseModelBackend):
    """Google Gemini API backend"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = "gemini-2.0-flash"
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.genai = genai
                self._available = True
            except Exception as e:
                print(f"Gemini initialization failed: {e}")
                self._available = False
        else:
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        if not self.is_available():
            raise ValidationError("Gemini API is not available")
        
        try:
            model = self.genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=self.genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text.strip()
        except Exception as e:
            raise ValidationError(f"Gemini generation failed: {str(e)}")


# ============================================================================
# HUGGING FACE LOCAL MODEL BACKEND
# ============================================================================

class HuggingFaceBackend(BaseModelBackend):
    """Local Hugging Face model backend"""
    
    def __init__(self, model_name: str = "distilgpt2"):
        """
        Initialize with a Hugging Face model
        
        Recommended models:
        - "distilgpt2" (small, fast, 82MB)
        - "gpt2" (medium, 548MB)
        - "gpt2-medium" (large, 1.5GB)
        - "facebook/opt-350m" (350M params)
        - "EleutherAI/gpt-neo-125M" (125M params)
        """
        self.model_name = model_name
        self._available = False
        self.model = None
        self.tokenizer = None
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            print(f"Loading {model_name}... This may take a few minutes on first run.")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Use GPU if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            
            self._available = True
            print(f"✓ {model_name} loaded successfully on {self.device}")
        except ImportError:
            print("⚠ transformers library not installed. Run: pip install transformers torch")
        except Exception as e:
            print(f"✗ Failed to load {model_name}: {e}")
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        if not self.is_available():
            raise ValidationError("Hugging Face model is not available")
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the prompt from response
            if response.startswith(prompt):
                response = response[len(prompt):].strip()
            
            return response
        except Exception as e:
            raise ValidationError(f"Generation failed: {str(e)}")


# ============================================================================
# OLLAMA LOCAL MODEL BACKEND
# ============================================================================

class OllamaBackend(BaseModelBackend):
    """Ollama local model backend (requires Ollama installed)"""
    
    def __init__(self, model_name: str = "llama2"):
        """
        Initialize Ollama backend
        
        Popular models:
        - "llama2" (7B params)
        - "mistral" (7B params)
        - "codellama" (7B params, good for code)
        - "phi" (2.7B params, small and fast)
        """
        self.model_name = model_name
        self._available = False
        
        try:
            import requests
            self.requests = requests
            
            # Check if Ollama is running
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self._available = True
                print(f"✓ Ollama is running with model: {model_name}")
            else:
                print("⚠ Ollama server not responding")
        except ImportError:
            print("⚠ requests library not installed. Run: pip install requests")
        except Exception as e:
            print(f"⚠ Ollama not available: {e}")
            print("  Install Ollama from: https://ollama.ai/")
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        if not self.is_available():
            raise ValidationError("Ollama is not available. Install from https://ollama.ai/")
        
        try:
            response = self.requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                raise ValidationError(f"Ollama error: {response.status_code}")
        except Exception as e:
            raise ValidationError(f"Ollama generation failed: {str(e)}")


# ============================================================================
# OPENAI-COMPATIBLE API BACKEND
# ============================================================================

class OpenAIBackend(BaseModelBackend):
    """OpenAI API or compatible backends (LocalAI, LM Studio, etc.)"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com/v1"):
        """
        Initialize OpenAI-compatible backend
        
        For LocalAI: base_url = "http://localhost:8080/v1"
        For LM Studio: base_url = "http://localhost:1234/v1"
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url
        self._available = False
        
        if self.api_key or "localhost" in base_url:
            try:
                import openai
                self.openai = openai
                self.client = openai.OpenAI(api_key=self.api_key or "not-needed", base_url=base_url)
                self._available = True
                print(f"✓ OpenAI-compatible API configured at {base_url}")
            except ImportError:
                print("⚠ openai library not installed. Run: pip install openai")
            except Exception as e:
                print(f"✗ OpenAI backend initialization failed: {e}")
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        if not self.is_available():
            raise ValidationError("OpenAI API is not available")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # or your model name
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise ValidationError(f"OpenAI generation failed: {str(e)}")


# ============================================================================
# CUSTOM/FINE-TUNED MODEL BACKEND
# ============================================================================

class CustomModelBackend(BaseModelBackend):
    """Template for your own custom model"""
    
    def __init__(self, model_path: str):
        """Load your custom trained model"""
        self.model_path = model_path
        self._available = False
        
        try:
            # Load your custom model here
            # Example: self.model = load_my_model(model_path)
            print(f"Loading custom model from {model_path}...")
            
            # TODO: Implement your model loading logic
            # self.model = ...
            
            self._available = True
            print("✓ Custom model loaded successfully")
        except Exception as e:
            print(f"✗ Failed to load custom model: {e}")
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        if not self.is_available():
            raise ValidationError("Custom model is not available")
        
        # TODO: Implement your generation logic
        # result = self.model.generate(prompt, temperature, max_tokens)
        # return result
        
        raise NotImplementedError("Implement your custom model generation logic here")


# ============================================================================
# MODEL MANAGER - AUTO-SELECT BEST AVAILABLE MODEL
# ============================================================================

class ModelManager:
    """Manages multiple model backends and auto-selects the best available"""
    
    def __init__(self, preferred_backend: str = "auto"):
        """
        Initialize model manager
        
        Args:
            preferred_backend: "auto", "gemini", "huggingface", "ollama", "openai", "custom"
        """
        self.preferred_backend = preferred_backend
        self.backends = {}
        self.active_backend = None
        
        # Initialize all available backends
        self._init_backends()
        
        # Select active backend
        self._select_backend()
    
    def _init_backends(self):
        """Initialize all backends"""
        # Try Gemini
        try:
            gemini = GeminiBackend()
            if gemini.is_available():
                self.backends["gemini"] = gemini
        except:
            pass
        
        # Try Ollama FIRST (FREE local model)
        try:
            ollama = OllamaBackend("mistral")
            if ollama.is_available():
                self.backends["ollama"] = ollama
                print("✓ Ollama backend initialized successfully")
        except Exception as e:
            print(f"⚠ Ollama not available: {e}")
        
        # Try Hugging Face as fallback
        try:
            hf = HuggingFaceBackend("distilgpt2")
            if hf.is_available():
                self.backends["huggingface"] = hf
        except:
            pass
    
    def _select_backend(self):
        """Select the best available backend"""
        if self.preferred_backend != "auto" and self.preferred_backend in self.backends:
            self.active_backend = self.backends[self.preferred_backend]
            print(f"✓ Using preferred backend: {self.preferred_backend}")
        else:
            # Auto-select: Gemini FIRST (fast), then Ollama (free backup)
            priority = ["gemini", "ollama", "huggingface", "openai"]
            for backend_name in priority:
                if backend_name in self.backends:
                    self.active_backend = self.backends[backend_name]
                    print(f"✓ Auto-selected backend: {backend_name}")
                    break
        
        if not self.active_backend:
            raise ValidationError(
                "No AI model backend available. Please install Ollama:\n"
                "1. Download from: https://ollama.ai/download\n"
                "2. Install Ollama\n"
                "3. Run: ollama pull mistral\n"
                "4. Restart your Django server\n"
                "\nOllama is FREE and runs locally on your computer!"
            )
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """Generate text using active backend"""
        if not self.active_backend:
            raise ValidationError("No model backend available")
        
        return self.active_backend.generate(prompt, temperature, max_tokens)
    
    def get_backend_name(self) -> str:
        """Get name of active backend"""
        for name, backend in self.backends.items():
            if backend == self.active_backend:
                return name
        return "unknown"


# ============================================================================
# GLOBAL MODEL INSTANCE
# ============================================================================

# Initialize global model manager
# Use Gemini for SPEED, fallback to Ollama if API issues
MODEL_MANAGER = ModelManager(preferred_backend="gemini")


def get_model() -> ModelManager:
    """Get the global model manager instance"""
    return MODEL_MANAGER
