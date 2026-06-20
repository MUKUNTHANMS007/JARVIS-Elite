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
        
        # --- NEURAL SHIELD: Private Network Enforcement (RFC1918 only) ---
        def _is_private(h: str) -> bool:
            if h in ("127.0.0.1", "localhost"):
                return True
            if h.startswith("192.168.") or h.startswith("10."):
                return True
            # RFC1918: 172.16.0.0 – 172.31.255.255 only
            if h.startswith("172."):
                parts = h.split(".")
                if len(parts) >= 2:
                    try:
                        second = int(parts[1])
                        return 16 <= second <= 31
                    except ValueError:
                        pass
            return False

        if not _is_private(host):
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
