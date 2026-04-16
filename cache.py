import time
from config import CACHE_TTL_SECONDS

_store = {}


def get_cached(key):
    entry = _store.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        del _store[key]
        return None
    return entry["data"]


def set_cache(key, data):
    _store[key] = {"data": data, "ts": time.time()}
