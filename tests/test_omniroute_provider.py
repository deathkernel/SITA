from __future__ import annotations
import os, unittest
from unittest.mock import patch
from tara_chat.gemini_provider import GeminiProvider
from tara_chat.llm_provider_factory import provider_from_env


class GeminiProviderFactoryTests(unittest.TestCase):
    def test_factory_selects_gemini_when_explicitly_enabled(self):
        with patch.dict(os.environ,{"TARA_LLM_BACKEND":"gemini","GEMINI_API_KEY":"test-key"},clear=True):
            provider=provider_from_env()
        self.assertIsInstance(provider,GeminiProvider)
        self.assertEqual(provider.model,"gemini-3.8-flash")
    def test_factory_defaults_to_gemini(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True):
            provider=provider_from_env()
        self.assertIsInstance(provider,GeminiProvider)
        self.assertEqual(provider.model,"gemini-3.8-flash")
    def test_factory_rejects_non_gemini_backend(self):
        with patch.dict(os.environ,{"TARA_LLM_BACKEND":"omniroute","GEMINI_API_KEY":"test-key"},clear=True):
            with self.assertRaisesRegex(ValueError,"Gemini only"): provider_from_env()


if __name__=="__main__": unittest.main()
