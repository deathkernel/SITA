from __future__ import annotations
import os, unittest
from unittest.mock import patch
from tara_chat.gemini_provider import GeminiProvider
from tara_chat.llm_provider_factory import provider_from_env


class GeminiProviderTests(unittest.TestCase):
    def test_native_generate_content_and_usage_metadata(self):
        calls=[]
        def transport(url,**kwargs):
            calls.append((url,kwargs))
            return {"candidates":[{"content":{"parts":[{"text":"Gemini says hello"}]},"finishReason":"STOP"}],
                    "usageMetadata":{"promptTokenCount":12,"candidatesTokenCount":7,"totalTokenCount":19}}
        p=GeminiProvider(api_key="safe-test-key",transport=transport)
        self.assertEqual(p.complete("Hi",system="You are SITA",max_completion_tokens=64),"Gemini says hello")
        url,kw=calls[0]
        self.assertTrue(url.endswith("/models/gemini-3.8-flash:generateContent"))
        self.assertEqual(kw["api_key"],"safe-test-key")
        self.assertEqual(kw["payload"]["systemInstruction"],{"parts":[{"text":"You are SITA"}]})
        self.assertEqual(p.last_usage,{"prompt_tokens":12,"completion_tokens":7,"total_tokens":19})
    def test_catalog_lists_only_generate_content_capable_models(self):
        p=GeminiProvider(api_key="safe-test-key",transport=lambda *a,**k:{"models":[
            {"name":"models/gemini-3.8-flash","displayName":"Gemini Flash","supportedGenerationMethods":["generateContent"]},
            {"name":"models/embedding-001","supportedGenerationMethods":["embedContent"]}]})
        self.assertEqual([x["id"] for x in p.list_models()],["gemini-3.8-flash"])
    def test_health_performs_authenticated_model_list(self):
        seen={}
        def transport(url,**kwargs): seen.update(url=url,**kwargs);return {"models":[]}
        p=GeminiProvider(api_key="safe-key",transport=transport)
        self.assertTrue(p.health())
        self.assertIn("/models?pageSize=1",seen["url"])
        self.assertEqual(seen["api_key"],"safe-key")
    def test_invalid_key_model_timeout_rejected(self):
        with self.assertRaises(ValueError): GeminiProvider(api_key="")
        with self.assertRaises(ValueError): GeminiProvider(api_key="x",model="../bad")
        with self.assertRaises(ValueError): GeminiProvider(api_key="x",timeout=0)
    def test_factory_selects_gemini(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True):
            p=provider_from_env()
        self.assertIsInstance(p,GeminiProvider)
        self.assertEqual(p.model,"gemini-3.8-flash")
    def test_factory_rejects_non_gemini_backend(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","TARA_LLM_BACKEND":"other-provider"},clear=True):
            with self.assertRaisesRegex(ValueError,"Gemini only"): provider_from_env()


if __name__=="__main__": unittest.main()
