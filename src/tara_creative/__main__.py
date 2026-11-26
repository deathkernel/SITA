"""One-request JSON-over-stdio adapter for SITA Creative."""
from __future__ import annotations
import json, sys, time
from .service import MODULE_ID, _gemini_config, execute
from tara_chat.gemini_provider import GeminiProvider

MAX_REQUEST_BYTES=1_000_000
_ALLOWED={"schema_version","request_id","session_id","module","action","inputs","workspace_root","timeout_seconds","approval_token"}


def _reply(request_id,status,data=None,error=None,duration_ms=0):
    sys.stdout.write(json.dumps({"schema_version":"1.0","request_id":request_id,"status":status,"data":data or {},"error":error,"duration_ms":duration_ms},ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n")


def main():
    raw=sys.stdin.buffer.read(MAX_REQUEST_BYTES+1)
    if len(raw)>MAX_REQUEST_BYTES:
        _reply("unknown","invalid_request",error="request exceeds the size limit"); return 0
    try: request=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError):
        _reply("unknown","invalid_request",error="request must be UTF-8 JSON"); return 0
    if not isinstance(request,dict) or set(request)-_ALLOWED:
        _reply("unknown","invalid_request",error="request shape is invalid"); return 0
    rid=request.get("request_id")
    if not isinstance(rid,str) or not rid.strip() or len(rid)>128:
        _reply("unknown","invalid_request",error="request_id is invalid"); return 0
    if request.get("schema_version")!="1.0" or request.get("module")!=MODULE_ID:
        _reply(rid,"invalid_request",error="module or schema version is invalid"); return 0
    action,inputs=request.get("action"),request.get("inputs",{})
    if not isinstance(action,str) or not isinstance(inputs,dict):
        _reply(rid,"invalid_request",error="action or inputs are invalid"); return 0
    if action=="health":
        try:
            key,model=_gemini_config()
            provider=GeminiProvider(api_key=key,model=model)
            diagnostic=provider.health_diagnostic()
        except (ValueError,RuntimeError) as exc:
            _reply(rid,"unavailable",error=str(exc)[:500]); return 0
        if diagnostic:
            _reply(rid,"unavailable",error=diagnostic); return 0
        _reply(rid,"success",{"healthy":True,"provider":"gemini","model":model}); return 0
    start=time.monotonic()
    try:
        status,data,error=execute(action,inputs,approval_token=request.get("approval_token"))
        if not isinstance(data,dict): raise ValueError("module returned invalid result data")
    except ValueError as exc: status,data,error="invalid_request",{},str(exc)[:500]
    except Exception: status,data,error="failed",{},"module operation failed"
    _reply(rid,status,data,error,max(0,int((time.monotonic()-start)*1000)))
    return 0

if __name__=="__main__": raise SystemExit(main())
