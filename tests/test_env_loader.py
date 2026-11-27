from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tara_app.env_loader import load_env_file


class EnvLoaderTests(unittest.TestCase):
    def test_loads_values_and_preserves_existing_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                '# local secrets\nGEMINI_API_KEY="local-key"\nTARA_GEMINI_MODEL=gemini-3.8-flash\n',
                encoding="utf-8",
            )
            environ = {"GEMINI_API_KEY": "process-key"}
            loaded = load_env_file(env_file, environ)
        self.assertEqual(loaded, 1)
        self.assertEqual(environ["GEMINI_API_KEY"], "process-key")
        self.assertEqual(environ["TARA_GEMINI_MODEL"], "gemini-3.8-flash")

    def test_missing_file_is_a_noop(self):
        self.assertEqual(load_env_file("does-not-exist.env", {}), 0)

    def test_rejects_malformed_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("not-an-assignment\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_env_file(env_file, {})


if __name__ == "__main__":
    unittest.main()
