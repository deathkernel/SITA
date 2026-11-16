"""Tests for the read-only n8n public API adapter."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tara_app.n8n_client import (  # noqa: E402
    N8nApiError,
    N8nConfigurationError,
    N8nReadOnlyClient,
    N8nSettings,
)


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size: int = -1) -> bytes:
        return self.payload[:size]


class N8nSettingsTests(unittest.TestCase):
    def test_requires_url_and_api_key(self) -> None:
        with self.assertRaises(N8nConfigurationError):
            N8nSettings.from_environment({})

    def test_normalizes_loopback_url_and_hides_api_key(self) -> None:
        settings = N8nSettings.from_environment({
            "TARA_N8N_BASE_URL": "http://127.0.0.1:5678",
            "TARA_N8N_API_KEY": "secret-value",
        })
        self.assertEqual(settings.base_url, "http://127.0.0.1:5678/api/v1")
        self.assertNotIn("secret-value", repr(settings))

    def test_rejects_plain_http_for_non_loopback(self) -> None:
        with self.assertRaises(N8nConfigurationError):
            N8nSettings.from_environment({
                "TARA_N8N_BASE_URL": "http://example.com",
                "TARA_N8N_API_KEY": "secret-value",
            })

    def test_rejects_url_credentials_and_query(self) -> None:
        for url in (
            "https://user:pass@example.com",
            "https://example.com?token=secret",
            "file:///tmp/n8n",
        ):
            with self.subTest(url=url), self.assertRaises(N8nConfigurationError):
                N8nSettings.from_environment({
                    "TARA_N8N_BASE_URL": url,
                    "TARA_N8N_API_KEY": "secret-value",
                })


class N8nReadOnlyClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = N8nReadOnlyClient(N8nSettings(
            "http://127.0.0.1:5678/api/v1",
            "test-api-key",
            3.0,
        ))

    @patch("tara_app.n8n_client.N8nReadOnlyClient._get")
    def test_connection_status_is_read_only(self, get) -> None:
        get.return_value = {"data": []}
        self.assertEqual(
            self.client.connection_status(),
            {"status": "connected", "provider": "n8n", "access": "read_only"},
        )
        get.assert_called_once_with("workflows", {"limit": 1})

    @patch("tara_app.n8n_client.N8nReadOnlyClient._get")
    def test_lists_only_safe_workflow_metadata(self, get) -> None:
        get.return_value = {
            "data": [{
                "id": "wf-1",
                "name": "Daily report",
                "active": True,
                "createdAt": "2026-11-16T10:00:00.000Z",
                "nodes": [{"parameters": {"secret": "do-not-return"}}],
            }],
            "nextCursor": "next-page",
        }
        result = self.client.list_workflows(limit=10)
        self.assertEqual(result["workflows"][0]["name"], "Daily report")
        self.assertNotIn("nodes", result["workflows"][0])
        self.assertEqual(result["next_cursor"], "next-page")

    @patch("tara_app.n8n_client.N8nReadOnlyClient._get")
    def test_lists_bounded_execution_metadata(self, get) -> None:
        get.return_value = {"data": [{
            "id": "ex-1",
            "workflowId": "wf-1",
            "status": "success",
            "startedAt": "2026-11-16T10:00:00.000Z",
            "finished": True,
            "data": {"resultData": {"runData": "not-returned"}},
        }]}
        result = self.client.list_executions(workflow_id="wf-1")
        self.assertEqual(result["executions"][0]["status"], "success")
        self.assertNotIn("data", result["executions"][0])
        get.assert_called_once_with("executions", {"limit": 20, "workflowId": "wf-1"})

    def test_rejects_invalid_limits_and_cursor(self) -> None:
        for limit in (0, 101, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.client.list_workflows(limit=limit)
        with self.assertRaises(ValueError):
            self.client.list_workflows(cursor="")

    @patch("tara_app.n8n_client.N8nReadOnlyClient._get")
    def test_rejects_malformed_response(self, get) -> None:
        get.return_value = {"data": "not-a-list"}
        with self.assertRaises(N8nApiError):
            self.client.list_workflows()

    @patch("tara_app.n8n_client.build_opener")
    def test_sends_api_key_header_and_get_only(self, build_opener) -> None:
        opener = build_opener.return_value
        opener.open.return_value = FakeResponse({"data": []})
        self.client._get("workflows", {"limit": 1})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.get_header("X-n8n-api-key"), "test-api-key")


if __name__ == "__main__":
    unittest.main()
