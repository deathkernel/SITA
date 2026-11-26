"""Gemini model catalogue and generation adapter for SITA."""
from __future__ import annotations
import json, os, re, sys, time
from collections.abc import Mapping
from typing import Any
from tara_chat.gemini_provider import GeminiProvider

MAX_REQUEST=64_000
_MODEL_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _provider(model: str|None=None) -> GeminiProvider:
    api_key=os.environ.get("GEMINI_API_KEY","")
    selected=model or os.environ.get("TARA_MODELS_MODEL",os.environ.get("TARA_GEMINI_MODEL","gemini-2.5-flash"))
    if not isinstance(selected,str) or not _MODEL_RE.fullmatch(selected):
        raise ValueError("Gemini model ID is invalid")
    return GeminiProvider(api_key=api_key,model=selected)


def _generate(provider: GeminiProvider, question: str) -> str:
    return provider.complete(question,system="You are SITA, a helpful assistant. Answer clearly and directly. State uncertainty and never invent sources.",max_completion_tokens=4096,temperature=0.4)


def handle_request(request: Any) -> dict[str,Any]:
    started=time.monotonic()
    def result(rid,status,data=None,error=None):
        return {"schema_version":"1.0","request_id":rid,"status":status,"data":data or {},"error":error,"duration_ms":max(0,int((time.monotonic()-started)*1000))}
    allowed={"schema_version","request_id","session_id","module","action","inputs","workspace_root","timeout_seconds","approval_token"}
    if not isinstance(request,dict) or set(request)-allowed: return result("unknown","invalid_request",error="request shape is invalid")
    rid=request.get("request_id")
    if not isinstance(rid,str) or not rid.strip() or len(rid)>128: return result("unknown","invalid_request",error="request_id is invalid")
    if request.get("schema_version")!="1.0" or request.get("module")!="models": return result(rid,"invalid_request",error="module or schema version is invalid")
    inputs=request.get("inputs",{})
    if not isinstance(inputs,dict): return result(rid,"invalid_request",error="model inputs are invalid")
    action=request.get("action")
    if action not in {"health","catalog","generate"}: return result(rid,"permission_denied",error="unsupported model capability")
    question=inputs.get("question")
    if action=="generate" and (not isinstance(question,str) or not question.strip() or len(question)>20_000):
        return result(rid,"invalid_request",error="question is invalid")
    try:
        provider=_provider()
        if action=="health":
            diagnostic=provider.health_diagnostic()
            if diagnostic: return result(rid,"unavailable",error=diagnostic)
            return result(rid,"success",{"healthy":True,"provider":"gemini","model":provider.model})
        if action=="catalog":
            models=provider.list_models()
            if not any(item["id"]==provider.model for item in models):
                models.insert(0,{"id":provider.model,"provider":"gemini","label":provider.model,"owned_by":"Google","availability":"Configured default model; availability is checked on generation."})
            lines=["# Gemini Model Hub","Models available to the configured Gemini API key:",""]
            lines.extend(f"- {item['id']} — {item.get('label') or 'Gemini model'}" for item in models)
            lines.extend(["","Model availability, quotas, and billing depend on the Google AI project and API key."])
            return result(rid,"success",{"text":"\n".join(lines),"models":models,"provider":"gemini","remote_data_transfer":False})
        selected=inputs.get("model")
        if selected is None:
            selection=re.match(r"^\s*(?:please\s+)?(?:use|switch to|try|ask|run with)\s+(?:model\s+)?(?P<model>[A-Za-z0-9][A-Za-z0-9._-]{0,127})\s*[:,-]?\s*",question,re.I)
            if selection and _MODEL_RE.fullmatch(selection.group("model")):
                selected=selection.group("model")
                question=question[selection.end():].strip() or question
            else: selected=provider.model
        if not isinstance(selected,str) or not _MODEL_RE.fullmatch(selected): return result(rid,"invalid_request",error="Gemini model ID is invalid")
        provider=_provider(selected)
        answer=_generate(provider,question.strip())
        return result(rid,"success",{"text":answer,"provider":"gemini","model":selected,"remote_data_transfer":True})
    except (OSError,RuntimeError,TimeoutError,ValueError) as exc:
        return result(rid,"unavailable",error=str(exc)[:500] or "Gemini API is unavailable")


def main() -> int:
    raw=sys.stdin.buffer.read(MAX_REQUEST+1)
    if len(raw)>MAX_REQUEST:
        response={"schema_version":"1.0","request_id":"unknown","status":"invalid_request","data":{},"error":"request exceeds the size limit","duration_ms":0}
    else:
        try: request=json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError): response={"schema_version":"1.0","request_id":"unknown","status":"invalid_request","data":{},"error":"request must be UTF-8 JSON","duration_ms":0}
        else: response=handle_request(request)
    sys.stdout.write(json.dumps(response,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n")
    return 0

if __name__=="__main__": raise SystemExit(main())
