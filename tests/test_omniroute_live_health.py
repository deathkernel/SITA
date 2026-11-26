from __future__ import annotations
import json, os, unittest
from unittest.mock import patch
from tara_app.omniroute_health import check_gateway, diagnose_gateway
from tara_chat.app_adapter import handle_request as handle_chat
from tara_models.__main__ import handle_request as handle_models


def request(module):
    return {"schema_version":"1.0","request_id":module+"-health","module":module,"action":"health","inputs":{}}


class GeminiHealthTests(unittest.TestCase):
    def test_probe_uses_google_models_endpoint_and_api_key_header(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,size=-1): return b'{"models":[]}'
        class Opener:
            def open(self,req,timeout): self.request=req;self.timeout=timeout;return Response()
        opener=Opener()
        with patch("tara_chat.gemini_provider.build_opener",return_value=opener):
            self.assertTrue(check_gateway(api_key="safe-key"))
        self.assertEqual(opener.request.full_url,"https://generativelanguage.googleapis.com/v1beta/models?pageSize=1")
        self.assertEqual(opener.request.get_header("X-goog-api-key"),"safe-key")
        self.assertEqual(opener.timeout,8.0)
    def test_missing_key_diagnostic_is_specific(self):
        self.assertIn("GEMINI_API_KEY",diagnose_gateway(api_key=""))
    def test_auth_failure_does_not_leak_key(self):
        from urllib.error import HTTPError
        class Opener:
            def open(self,req,timeout): raise HTTPError(req.full_url,401,"Unauthorized",{},None)
        with patch("tara_chat.gemini_provider.build_opener",return_value=Opener()):
            message=diagnose_gateway(api_key="very-secret")
        self.assertIn("rejected",message.lower());self.assertNotIn("very-secret",message)
    def test_chat_health_fails_closed_when_gemini_unavailable(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","TARA_LLM_BACKEND":"gemini"},clear=True),patch("tara_chat.gemini_provider.GeminiProvider.health_diagnostic",return_value="Gemini API is unavailable"):
            r=handle_chat(request("chat"))
        self.assertEqual(r["status"],"unavailable");self.assertNotIn("test-key",json.dumps(r))
    def test_model_hub_health_fails_closed_when_gemini_unavailable(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True),patch("tara_chat.gemini_provider.GeminiProvider.health_diagnostic",return_value="Gemini API is unavailable"):
            r=handle_models(request("models"))
        self.assertEqual(r["status"],"unavailable");self.assertNotIn("test-key",json.dumps(r))


if __name__=="__main__": unittest.main()
