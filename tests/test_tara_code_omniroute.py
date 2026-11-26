from __future__ import annotations
import base64, json, os, unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO
from tara_code import __main__ as code


class Response:
    def __init__(self, body): self.body=json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,size=-1): return self.body if size<0 else self.body[:size]


class Opener:
    def __init__(self,body=None,error=None): self.response=Response(body or {});self.error=error;self.request=None;self.timeout=None
    def open(self,request,timeout): self.request=request;self.timeout=timeout
    # no-op


class GeminiCodeTests(unittest.TestCase):
    def request(self):
        return {"schema_version":"1.0","request_id":"code-test","module":"code","action":"plan","inputs":{"question":"Review this function"}}
    def test_generate_uses_gemini_header_and_native_request(self):
        class Fake:
            def open(self,request,timeout):
                self.request=request;self.timeout=timeout
                return Response({"candidates":[{"content":{"parts":[{"text":"Review plan"}]}}]})
        fake=Fake()
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","TARA_CODE_MODEL":"gemini-3.8-flash"},clear=True),patch.object(code,"_gemini_opener",return_value=fake):
            result=code.handle_request(self.request())
        self.assertEqual(result["status"],"success")
        self.assertEqual(result["data"]["provider"],"gemini")
        self.assertEqual(result["data"]["text"],"Review plan")
        self.assertEqual(fake.request.full_url,"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent")
        self.assertEqual(fake.request.get_header("X-goog-api-key"),"test-key")
        body=json.loads(fake.request.data)
        self.assertIn("contents",body)
        self.assertNotIn("messages",body)
        self.assertEqual(fake.timeout,150)
    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ,{},clear=True),patch.object(code,"_gemini_opener") as opener:
            result=code.handle_request(self.request())
        self.assertEqual(result["status"],"unavailable")
        opener.assert_not_called()
    def test_health_uses_gemini_model_list(self):
        class Fake:
            def open(self,request,timeout):
                self.request=request; return Response({"models":[]})
        fake=Fake(); req=self.request();req["action"]="health"
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True),patch.object(code,"_gemini_opener",return_value=fake):
            result=code.handle_request(req)
        self.assertEqual(result["status"],"success")
        self.assertTrue(fake.request.full_url.endswith("/v1beta/models?pageSize=1"))
        self.assertEqual(fake.request.get_header("X-goog-api-key"),"test-key")
    def test_error_body_does_not_leak(self):
        class Fake:
            def open(self,request,timeout): raise HTTPError(request.full_url,401,"Unauthorized",{},BytesIO(b"secret response"))
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True),patch.object(code,"_gemini_opener",return_value=Fake()):
            result=code.handle_request(self.request())
        self.assertEqual(result["status"],"unavailable")
        self.assertNotIn("secret response",result["error"])
    def test_source_attachments_remain_bounded(self):
        encoded=base64.b64encode(b"print('safe')").decode()
        self.assertIn("print('safe')",code._read_attachments([{"name":"example.py","content_base64":encoded}]))
        with self.assertRaises(ValueError): code._read_attachments([{"name":"passwords.txt","content_base64":encoded}])


if __name__=="__main__": unittest.main()
