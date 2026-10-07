"""
security/ratelimit.py — slowapi rate limiting.
"""
from __future__ import annotations

from slowapi import Limiter  # type: ignore
from slowapi.util import get_remote_address  # type: ignore

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
