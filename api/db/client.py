# api/db/client.py
import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
    return create_client(url, key)
