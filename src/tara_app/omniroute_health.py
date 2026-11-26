"""Compatibility helpers for checking Google Gemini API availability."""
from __future__ import annotations

import os
from tara_chat.gemini_provider import GeminiProvider


def diagnose_gemini(api_key: str | None = None, *, timeout: float = 5.0) -> str | None:
    key=os.getenv("GEMINI_API_KEY","") if api_key is None else api_key
    if not isinstance(key,str) or not key.strip():
        return "GEMINI_API_KEY is not set. Add a valid Gemini API key to the terminal environment used to launch SITA."
    try: provider=GeminiProvider(api_key=key,timeout=max(1.0,min(float(timeout),8.0)))
    except (TypeError,ValueError) as exc: return str(exc)
    diagnostic=provider.health_diagnostic()
    if diagnostic is None: return None
    if "HTTP 401" in diagnostic or "HTTP 403" in diagnostic:
        return "Gemini rejected the API key. Check that the key is active and Gemini API access is enabled."
    if "HTTP 429" in diagnostic:
        return "Gemini API rate limit or quota reached. Check project quota and billing settings."
    return diagnostic


def diagnose_gateway(base_url: str | None = None, api_key: str | None = None, *, timeout: float = 5.0) -> str | None:
    """Legacy function name retained for imports; only checks Gemini now."""
    return diagnose_gemini(api_key,timeout=timeout)


def check_gateway(base_url: str | None = None, api_key: str | None = None, *, timeout: float = 5.0) -> bool:
    return diagnose_gemini(api_key,timeout=timeout) is None
