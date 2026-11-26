"""Direct Gemini API provider for SITA."""
from __future__ import annotations
import json, math, os, re
from threading import local
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from typing import Any

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, msg, headers, new_url):
        return None

def _request_json(url: str, *, api_key: str, method: str = "POST", payload: dict[str, Any] | None = None, timeout: float = 180.0) -> dict[str, Any]:
    raw = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    req = Request(url, data=raw, headers={"x-goog-api-key":api_key,"Content-Type":"application/json","Accept":"application/json","User-Agent":"SITA/0.2"}, method=method)
    try:
        with build_opener(ProxyHandler({}), _NoRedirect()).open(req, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Could not reach the Gemini API") from None
    if len(data) > MAX_RESPONSE_BYTES: raise RuntimeError("Gemini API response exceeded SITA's 8 MiB limit")
    try: result = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError): raise RuntimeError("Gemini API returned malformed JSON") from None
    if not isinstance(result, dict): raise RuntimeError("Gemini API returned an invalid response")
    return result

def _extract_text(data: dict[str, Any]) -> str:
    candidates=data.get("candidates"); first=candidates[0] if isinstance(candidates,list) and candidates else None
    content=first.get("content") if isinstance(first,dict) else None
    parts=content.get("parts") if isinstance(content,dict) else []
    text="\n".join(p.get("text") for p in parts or [] if isinstance(p,dict) and isinstance(p.get("text"),str)).strip()
    if not text:
        reason=first.get("finishReason") if isinstance(first,dict) else None
        raise RuntimeError(f"Gemini returned no text content{f' (finish reason: {reason})' if reason else ''}")
    return text

class GeminiProvider:
    """Gemini REST client with SITA's text completion and model-list contracts."""
    def __init__(self, *, api_key: str, model: str="gemini-2.5-flash", timeout: float=180.0, transport=None):
        if not isinstance(api_key,str) or not api_key.strip() or len(api_key)>4096 or any(ord(c)<33 or ord(c)==127 for c in api_key):
            raise ValueError("GEMINI_API_KEY must be a non-empty bounded value")
        if not isinstance(model,str) or not _MODEL_RE.fullmatch(model): raise ValueError("Gemini model ID is invalid")
        if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(float(timeout)) or not 1<=float(timeout)<=3600:
            raise ValueError("Gemini timeout must be between 1 and 3600 seconds")
        self.api_key,self.model,self.timeout=api_key.strip(),model,float(timeout)
        self._transport=transport or _request_json
        self._usage=local()
    @classmethod
    def from_env(cls):
        try: timeout=float(os.getenv("TARA_GEMINI_TIMEOUT_SECONDS","180").strip())
        except ValueError: raise ValueError("TARA_GEMINI_TIMEOUT_SECONDS must be numeric") from None
        return cls(api_key=os.getenv("GEMINI_API_KEY",""),model=os.getenv("TARA_GEMINI_MODEL","gemini-2.5-flash"),timeout=timeout)
    @property
    def last_usage(self):
        value=getattr(self._usage,"value",None)
        return dict(value) if isinstance(value,dict) else None
    def health_diagnostic(self):
        try:
            self._transport(f"{API_BASE}/models?pageSize=1",api_key=self.api_key,method="GET",timeout=min(self.timeout,8.0))
            return None
        except RuntimeError as exc: return str(exc)
    def health(self): return self.health_diagnostic() is None
    def list_models(self):
        data=self._transport(f"{API_BASE}/models?pageSize=100",api_key=self.api_key,method="GET",timeout=min(self.timeout,30.0))
        models=[]
        for item in data.get("models",[]):
            if isinstance(item,dict) and isinstance(item.get("name"),str) and item["name"].startswith("models/") and "generateContent" in item.get("supportedGenerationMethods",[]):
                mid=item["name"].split("/",1)[1]
                models.append({"id":mid,"provider":"gemini","label":item.get("displayName") or mid,"owned_by":"Google","availability":"Available to the configured Gemini API key."})
        return models
    def generate(self, contents, *, system=None, max_output_tokens=2048, temperature=0.4):
        body={"contents":contents,"generationConfig":{"maxOutputTokens":max_output_tokens,"temperature":float(temperature)}}
        if system and system.strip(): body["systemInstruction"]={"parts":[{"text":system.strip()}]}
        data=self._transport(f"{API_BASE}/models/{quote(self.model,safe='')}:generateContent",api_key=self.api_key,payload=body,timeout=self.timeout)
        usage=data.get("usageMetadata"); normalized={}
        if isinstance(usage,dict):
            for src,dst in (("promptTokenCount","prompt_tokens"),("candidatesTokenCount","completion_tokens"),("totalTokenCount","total_tokens")):
                n=usage.get(src)
                if type(n) is int and n>=0: normalized[dst]=n
        self._usage.value=normalized or None
        return _extract_text(data),data
    def complete(self,prompt,*,system=None,max_completion_tokens=512,temperature=0.6):
        if not isinstance(prompt,str) or not prompt.strip(): raise ValueError("prompt must not be empty")
        if type(max_completion_tokens) is not int or not 1<=max_completion_tokens<=8192: raise ValueError("max_completion_tokens must be between 1 and 8192")
        if isinstance(temperature,bool) or not isinstance(temperature,(int,float)) or not math.isfinite(float(temperature)) or not 0<=float(temperature)<=2: raise ValueError("temperature must be finite and between 0 and 2")
        text,_=self.generate([{"role":"user","parts":[{"text":prompt.strip()}]}],system=system,max_output_tokens=max_completion_tokens,temperature=temperature)
        return text

__all__=["GeminiProvider","API_BASE"]
