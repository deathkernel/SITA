from __future__ import annotations
import os, unittest
from unittest.mock import patch
from tara_models.__main__ import handle_request


def req(action,inputs=None):
    return {"schema_version":"1.0","request_id":"model-test","module":"models","action":action,"inputs":inputs or {}}


class ModelHubGeminiTests(unittest.TestCase):
    def setUp(self): self.env={"GEMINI_API_KEY":"test-key","TARA_MODELS_MODEL":"gemini-2.5-flash"}
    def test_health_calls_gemini_models_endpoint(self):
        with patch.dict(os.environ,self.env,clear=True),patch("tara_chat.gemini_provider.GeminiProvider.health_diagnostic",return_value=None):
            result=handle_request(req("health"))
        self.assertEqual(result["status"],"success");self.assertEqual(result["data"]["provider"],"gemini")
    def test_catalog_filters_models_to_generate_content(self):
        models=[{"id":"gemini-2.5-flash","label":"Flash"},{"id":"gemini-2.5-pro","label":"Pro"}]
        with patch.dict(os.environ,self.env,clear=True),patch("tara_chat.gemini_provider.GeminiProvider.list_models",return_value=models):
            result=handle_request(req("catalog"))
        self.assertEqual(result["status"],"success");self.assertEqual(result["data"]["provider"],"gemini")
        self.assertEqual([x["id"] for x in result["data"]["models"]],["gemini-2.5-flash","gemini-2.5-pro"])
        self.assertIn("Gemini Model Hub",result["data"]["text"])
    def test_generate_calls_selected_gemini_model(self):
        with patch.dict(os.environ,self.env,clear=True),patch("tara_chat.gemini_provider.GeminiProvider.complete",return_value="Hello from Gemini") as complete:
            result=handle_request(req("generate",{"question":"Say hello","model":"gemini-2.5-pro"}))
        self.assertEqual(result["status"],"success");self.assertEqual(result["data"]["provider"],"gemini")
        self.assertEqual(result["data"]["model"],"gemini-2.5-pro");complete.assert_called_once()
    def test_model_can_be_selected_from_question(self):
        with patch.dict(os.environ,self.env,clear=True),patch("tara_chat.gemini_provider.GeminiProvider.complete",return_value="Hello"):
            result=handle_request(req("generate",{"question":"Use model gemini-2.5-pro: say hello"}))
        self.assertEqual(result["status"],"success");self.assertEqual(result["data"]["model"],"gemini-2.5-pro")
    def test_invalid_question_rejected_before_key_lookup(self):
        with patch.dict(os.environ,{},clear=True):
            result=handle_request(req("generate",{"question":" "}))
        self.assertEqual(result["status"],"invalid_request")
    def test_missing_key_does_not_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            result=handle_request(req("catalog"))
        self.assertEqual(result["status"],"unavailable");self.assertIn("GEMINI_API_KEY",result["error"])


if __name__=="__main__": unittest.main()
