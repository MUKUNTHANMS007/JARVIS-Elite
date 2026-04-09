import redis
import json
import os
import hashlib
from typing import Optional, Any

class RedisCache:
    """
    JARVIS Neural Cache: High-performance caching for semantic queries and tool results.
    Targeting <10ms retrieval for repetitive intelligence lookups.
    """
    def __init__(self):
        host = os.getenv("REDIS_HOST", "127.0.0.1")
        port = int(os.getenv("REDIS_PORT", 6379))
        password = os.getenv("REDIS_PASSWORD", None)
        
        # --- NEURAL SHIELD: Private Network Enforcement ---
        is_private = host == "127.0.0.1" or host == "localhost" or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.")
        if not is_private:
            print("[Neural Shield] BLOCK: Attempted connection to non-private Redis host. Isolation enforced.")
            self.client = None
            return

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Safe ping without exposing credentials
            self.client.ping()
            print(f"[Neural Cache] Secure Link Active: {host}:{port}")
        except Exception as e:
            print(f"[Neural Cache] Connection drift: {e}")
            self.client = None

    def _generate_key(self, namespace: str, key_content: str) -> str:
        hashed = hashlib.sha256(key_content.encode()).hexdigest()
        return f"jarvis:{namespace}:{hashed}"

    def get_semantic_match(self, query: str) -> Optional[dict]:
        if not self.client: return None
        try:
            key = self._generate_key("semantic", query)
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception: pass
        return None

    def set_semantic_match(self, query: str, response: dict, ttl: int = 3600):
        if not self.client: return
        try:
            key = self._generate_key("semantic", query)
            self.client.setex(key, ttl, json.dumps(response))
        except Exception: pass

    def cache_tool_result(self, tool_name: str, args: dict, result: Any, ttl: int = 300):
        if not self.client: return
        try:
            arg_str = json.dumps(args, sort_keys=True)
            key = self._generate_key(f"tool:{tool_name}", arg_str)
            self.client.setex(key, ttl, json.dumps(result))
        except Exception: pass

    def get_tool_result(self, tool_name: str, args: dict) -> Optional[Any]:
        if not self.client: return None
        try:
            arg_str = json.dumps(args, sort_keys=True)
            key = self._generate_key(f"tool:{tool_name}", arg_str)
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception: pass
        return None

# Singleton instance
neural_cache = RedisCache()
