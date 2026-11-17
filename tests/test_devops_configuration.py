from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from tara_app.runtime import RuntimeConfigurationError, _omniroute_settings
from tara_app.webapp import _allowed_hosts


class DevOpsConfigurationTests(unittest.TestCase):
    def test_allowed_hosts_default_to_loopback_only(self) -> None:
        with patch.dict(os.environ, {"SITA_ALLOWED_HOSTS": ""}):
            self.assertEqual(
                _allowed_hosts(8765),
                {"127.0.0.1:8765", "localhost:8765"},
            )

    def test_allowed_hosts_accept_only_explicit_values(self) -> None:
        with patch.dict(
            os.environ,
            {"SITA_ALLOWED_HOSTS": "localhost:8765, 127.0.0.1:8765"},
        ):
            self.assertEqual(
                _allowed_hosts(8765),
                {"localhost:8765", "127.0.0.1:8765"},
            )

    def test_allowed_hosts_fail_closed_for_malformed_values(self) -> None:
        for configured in (
            "https://localhost:8765",
            "localhost:8765/path",
            "user@localhost:8765",
            "   ",
        ):
            with self.subTest(configured=configured):
                with patch.dict(os.environ, {"SITA_ALLOWED_HOSTS": configured}):
                    self.assertEqual(_allowed_hosts(8765), set())

    def test_omniroute_accepts_docker_host_gateway(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TARA_OMNIROUTE_BASE_URL": "http://host.docker.internal:20128/v1",
                "TARA_OMNIROUTE_API_KEY": "",
            },
        ):
            settings = _omniroute_settings({"models": {}})

        self.assertEqual(
            settings["chat"]["TARA_OMNIROUTE_BASE_URL"],
            "http://host.docker.internal:20128/v1",
        )

    def test_omniroute_still_rejects_nonlocal_gateway(self) -> None:
        with patch.dict(
            os.environ,
            {"TARA_OMNIROUTE_BASE_URL": "https://example.com/v1"},
        ):
            with self.assertRaises(RuntimeConfigurationError):
                _omniroute_settings({"models": {}})


if __name__ == "__main__":
    unittest.main()
