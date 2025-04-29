import json
import hashlib
import time
from pathlib import Path


class CachedLLM:
    """
    A caching wrapper around LangChain's ChatOpenAI to reduce API calls
    """

    def __init__(self, llm_instance, cache_dir="cache", ttl=86400):
        """
        Initialize the cached LLM wrapper

        Args:
            llm_instance: LangChain ChatOpenAI instance
            cache_dir: Directory to store cached responses
            ttl: Time-to-live for cache entries in seconds (default: 24 hours)
        """
        self.llm = llm_instance
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl
        self.cache_hits = 0
        self.cache_misses = 0

    @staticmethod
    def _get_cache_key(messages):
        """Generate a unique cache key based on input parameters"""
        # Create a string representation of the messages to hash
        message_str = ""
        for msg in messages:
            # For structured messages like HumanMessage, SystemMessage
            if hasattr(msg, "content") and hasattr(msg, "type"):
                message_str += f"{msg.type}:{msg.content}"
            # For plain strings or other formats
            else:
                message_str += str(msg)

        # Create hash of the message content
        return hashlib.md5(message_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key):
        """Get the file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"

    def invoke(self, messages):
        """
        Invoke the LLM with caching

        Args:
            messages: List of messages to send to the LLM

        Returns:
            The LLM response
        """
        cache_key = self._get_cache_key(messages)
        cache_path = self._get_cache_path(cache_key)

        # Check if we have a valid cache entry
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            cached_time = cache_data.get("timestamp", 0)
            if time.time() - cached_time < self.ttl:
                self.cache_hits += 1
                return cache_data.get("response")

        # No valid cache, request from API
        self.cache_misses += 1
        response = self.llm.invoke(messages)

        # Cache the response
        cache_data = {
            "response": response,
            "timestamp": time.time(),
        }

        # Serialize the response
        if hasattr(response, "model_dump"):
            # For Pydantic models
            cache_data["response"] = response.model_dump()
        elif hasattr(response, "to_dict"):
            # For objects with to_dict method
            cache_data["response"] = response.to_dict()
        elif hasattr(response, "__dict__"):
            # For objects with __dict__
            cache_data["response"] = response.__dict__

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
        except (TypeError, ValueError) as e:
            # If serialization fails, we'll just not cache this response
            print(f"Warning: Could not cache response: {str(e)}")

        return response

    def get_stats(self):
        """Return cache hit/miss statistics"""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total) * 100 if total > 0 else 0
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%"
        }
