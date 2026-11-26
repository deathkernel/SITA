"""Gemini-only provider factory for SITA."""
from __future__ import annotations
import os
from .gemini_provider import GeminiProvider

def provider_from_env() -> GeminiProvider:
    backend=os.getenv("TARA_LLM_BACKEND","gemini").strip().lower()
    if backend!="gemini":
        raise ValueError("SITA supports Gemini only; set TARA_LLM_BACKEND=gemini")
    return GeminiProvider.from_env()

__all__=["provider_from_env"]
