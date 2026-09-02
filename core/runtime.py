from __future__ import annotations

from typing import Optional, Tuple

from core.config import get_settings
from core.db import get_client
from core.local_store import has_local_data, is_local_forced


def active_mode() -> str:
    """Returns LOCAL, SUPABASE or EMPTY."""
    settings = get_settings()
    if has_local_data() and (is_local_forced() or not settings.database_configured):
        return "LOCAL"
    if settings.database_configured:
        return "SUPABASE"
    if has_local_data():
        return "LOCAL"
    return "EMPTY"


def optional_client():
    settings = get_settings()
    if not settings.database_configured:
        return None
    try:
        return get_client(settings.supabase_url, settings.supabase_key)
    except Exception:
        return None
