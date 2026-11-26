from __future__ import annotations
import base64, os, unittest
from unittest.mock import patch
from tara_data.__main__ import handle_request as handle_data
from tara_vision.__main__ import _gemini_api_key, handle_request as handle_vision


class VisionGeminiTests(unittest.TestCase):
    def test_health_checks_gemini_models(self):
        class Fake:
            def open(self,req,timeout):
                self.request=req
                class Response:
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def read(self,n=-1): return b'{"models":[]}'
                return Response()
        fake=Fake()
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True),patch("tara_vision.__main__.build_opener",return_value=fake):
            r=handle_vision({"schema_version":"1.0","request_id":"v","module":"vision","action":"health","inputs":{}})
        self.assertEqual(r["status"],"success");self.assertEqual(r["data"]["provider"],"gemini")
        self.assertEqual(fake.request.get_header("X-goog-api-key"),"test-key")
    def test_invalid_image_rejected(self):
        r=handle_vision({"schema_version":"1.0","request_id":"v","module":"vision","action":"analyze","inputs":{"images":["%%%"]}})
        self.assertEqual(r["status"],"invalid_request")
    def test_vision_posts_inline_image_data_to_gemini(self):
        png=base64.b64encode(b"\x89PNG\r\n\x1a\n"+b"fake-png").decode()
        captured={}
        class Fake:
            def open(self,req,timeout):
                captured["request"]=req
                class Response:
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def read(self,n=-1): return b'{"candidates":[{"content":{"parts":[{"text":"A test image"}]}}]}'
                return Response()
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","TARA_VISION_MODEL":"gemini-2.5-flash"},clear=True),patch("tara_vision.__main__.build_opener",return_value=Fake()):
            r=handle_vision({"schema_version":"1.0","request_id":"v","module":"vision","action":"analyze","inputs":{"question":"Describe","images":[png]}})
        self.assertEqual(r["status"],"success");self.assertEqual(r["data"]["provider"],"gemini")
        self.assertTrue(r["data"]["images_sent_to_remote"])
        self.assertIn(":generateContent",captured["request"].full_url)
        content=__import__("json").loads(captured["request"].data)["contents"][0]["parts"]
        self.assertIn("inlineData",content[1])
    def test_key_validation(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError): _gemini_api_key()


class DataSpecialistTests(unittest.TestCase):
    def test_data_returns_bounded_numeric_and_missing_value_summaries(self):
        r=handle_data({"schema_version":"1.0","request_id":"d","module":"data","action":"analyze","inputs":{"csv_text":"name,score\nAri,2\nBea,4\nCam,\n"}})
        self.assertEqual(r["status"],"success");self.assertEqual(r["data"]["rows"],3)
        self.assertEqual(r["data"]["missing_values"]["score"],1);self.assertTrue(r["data"]["read_only"])
    def test_data_rejects_inconsistent_csv_rows(self):
        r=handle_data({"schema_version":"1.0","request_id":"d","module":"data","action":"analyze","inputs":{"csv_text":"name,score\nAri,2,extra\n"}})
        self.assertEqual(r["status"],"invalid_request")


if __name__=="__main__": unittest.main()
