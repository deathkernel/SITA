from __future__ import annotations
import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tara_app.runtime import create_application


class GeminiRuntimeConfigTests(unittest.TestCase):
    def _make_config(self, root, allow=True):
        path=root/"sita.toml"
        path.write_text("""
[gemini]
model = "gemini-3.8-flash"
[gemini.models]
chat = "gemini-3.8-flash"
code = "gemini-3.8-flash"
vision = "gemini-3.8-flash"
creative = "gemini-3.8-flash"
models = "gemini-3.8-flash"
[router]
command = ["{python}", "-c", "pass"]
working_directory = "."
[[modules]]
id = "chat"
allow_remote = true
command = ["{python}", "-c", "pass"]
working_directory = "."
environment = ["TARA_LLM_BACKEND", "TARA_GEMINI_MODEL", "GEMINI_API_KEY"]
[[modules]]
id = "code"
allow_remote = true
command = ["{python}", "-c", "pass"]
working_directory = "."
environment = ["TARA_CODE_MODEL", "TARA_GEMINI_MODEL", "GEMINI_API_KEY"]
[[modules]]
id = "vision"
allow_remote = true
command = ["{python}", "-c", "pass"]
working_directory = "."
environment = ["TARA_VISION_MODEL", "TARA_GEMINI_MODEL", "GEMINI_API_KEY"]
[[modules]]
id = "creative"
allow_remote = true
command = ["{python}", "-c", "pass"]
working_directory = "."
environment = ["TARA_CREATIVE_MODEL", "TARA_GEMINI_MODEL", "GEMINI_API_KEY"]
[[modules]]
id = "models"
allow_remote = true
command = ["{python}", "-c", "pass"]
working_directory = "."
environment = ["TARA_MODELS_MODEL", "TARA_GEMINI_MODEL", "GEMINI_API_KEY"]
""",encoding="utf-8")
        return path
    def test_all_llm_specialists_receive_gemini_key_and_no_legacy_gateway_vars(self):
        with tempfile.TemporaryDirectory() as directory:
            config=self._make_config(Path(directory))
            with patch.dict(os.environ,{"GEMINI_API_KEY":"local-test-key","TARA_OMNIROUTE_API_KEY":"ignored","OLLAMA_HOST":"http://127.0.0.1:11434"},clear=True):
                app=create_application(config)
            for module in ("chat","code","vision","creative","models"):
                env=app.registry.adapter(module).environment
                self.assertEqual(env["GEMINI_API_KEY"],"local-test-key")
                self.assertEqual(env["TARA_GEMINI_MODEL"],"gemini-3.8-flash")
                self.assertFalse(any("OMNIROUTE" in k for k in env))
                self.assertFalse(any("OLLAMA" in k for k in env))
            self.assertEqual(app.registry.adapter("chat").environment["TARA_LLM_BACKEND"],"gemini")
            self.assertIsNone(app.model_catalog)
    def test_remote_specialist_opt_in_stays_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory)/"sita.toml"
            config.write_text('[router]\ncommand=["{python}","-c","pass"]\nworking_directory="."\n[[modules]]\nid="chat"\nallow_remote=false\ncommand=["{python}","-c","pass"]\nworking_directory="."\n',encoding="utf-8")
            with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key"},clear=True):
                app=create_application(config)
            self.assertIsNone(app.registry.adapter("chat"))
            self.assertIn("allow_remote = true",app.registry.disabled_modules()["chat"])
    def test_environment_can_override_model_id(self):
        with tempfile.TemporaryDirectory() as directory:
            config=self._make_config(Path(directory))
            with patch.dict(os.environ,{"GEMINI_API_KEY":"key","TARA_GEMINI_MODEL":"gemini-2.5-pro"},clear=True):
                app=create_application(config)
            self.assertEqual(app.registry.adapter("chat").environment["TARA_GEMINI_MODEL"],"gemini-2.5-pro")


if __name__=="__main__": unittest.main()
