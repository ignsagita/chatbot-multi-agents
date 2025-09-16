from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import openai
from config import Config
import logging
import hashlib
import time
from utils.response_schema import AgentResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the customer support system"""
    
    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
        self.cache = {}
        
    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate cache key for the request"""
        cache_input = f"{prompt}_{str(kwargs)}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        if cache_key in self.cache:
            cached_time, response = self.cache[cache_key]
            if time.time() - cached_time < Config.CACHE_TTL:
                logger.info(f"Cache hit for {self.name}")
                return response
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache the response"""
        # Limit cache size
        if len(self.cache) >= Config.MAX_CACHE_SIZE:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
        
        self.cache[cache_key] = (time.time(), response)
    
    def _call_openai_api(self, messages: list, **kwargs) -> str:
        """Make API call to OpenAI with error handling"""
        if not self.client:
            return "Error: OpenAI API key not configured."
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=messages,
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error in {self.name}: {e}")
            return f"I apologize, but I'm experiencing technical difficulties. Please try again later."
    
    def _normalize_confidence(self, confidence) -> float:
        """Convert confidence to numeric value"""
        if isinstance(confidence, str):
            confidence_map = {"high": 0.8, "medium": 0.6, "low": 0.4}
            return confidence_map.get(confidence.lower(), 0.5)
        return float(confidence) if isinstance(confidence, (int, float)) else 0.5

    def process_with_cache(self, user_input: str, system_prompt: str, **kwargs) -> str:
        """Process input with caching support"""
        # Generate cache key
        cache_key = self._generate_cache_key(f"{system_prompt}_{user_input}", **kwargs)
        
        # Check cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Make API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = self._call_openai_api(messages, **kwargs)
        
        # Cache the response
        self._cache_response(cache_key, response)
        
        return response
    
    @abstractmethod
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user input and return response with metadata"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass