from __future__ import annotations
import os, unittest
from unittest.mock import patch
from tara_creative.service import _gemini_config, execute


class GeminiCreativeTests(unittest.TestCase):
    def setUp(self): self.env={"GEMINI_API_KEY":"test-key","TARA_CREATIVE_MODEL":"gemini-2.5-flash"}
    def test_creative_generation_uses_gemini_and_marks_remote_transfer(self):
        with patch.dict(os.environ,self.env,clear=True),patch("tara_creative.service._generate",return_value=("A polished draft","gemini-2.5-flash")):
            status,data,error=execute("write",{"brief":"Write an introduction"})
        self.assertEqual(status,"success");self.assertIsNone(error)
        self.assertEqual(data["provider"],"gemini");self.assertEqual(data["model"],"gemini-2.5-flash")
        self.assertTrue(data["remote_data_transfer"])
    def test_invalid_gemini_model_is_rejected(self):
        with patch.dict(os.environ,{**self.env,"TARA_CREATIVE_MODEL":"../bad"},clear=True):
            with self.assertRaises(ValueError): _gemini_config()
    def test_missing_key_fails_without_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            status,data,error=execute("write",{"brief":"Write an introduction"})
        self.assertEqual(status,"unavailable");self.assertEqual(data,{})
        self.assertIn("GEMINI_API_KEY",error)


if __name__=="__main__": unittest.main()
