import json
from app.redis_client import redis_client
from redis.exceptions import RedisError

def get_cached_json(key: str):
    raw = redis_client.get(key)
    if raw is None:
        return None

    return json.loads(raw)

def set_cached_json(key: str, value: dict, ttl_seconds: int = 60):
    redis_client.set(
        key,
        json.dumps(value),
        ex=ttl_seconds,
    )

def delete_cache(key: str):
    redis_client.delete(key)

def safe_get_cache(key: str):
    try:
        return get_cached_json(key)
    except (RedisError, ValueError, TypeError):
        return None

def safe_set_cache(key:str, value: dict, ttl_seconds: int = 60):
    try:
        set_cached_json(key, value, ttl_seconds)
    except (RedisError, ValueError, TypeError):
        pass