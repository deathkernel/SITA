"""Read-only client for the n8n public REST API.

The adapter deliberately exposes no workflow mutation or execution methods.
"""
from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass, field
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from tara_app.http import NoRedirectHandler


_MAX_RESPONSE_BYTES = 1_048_576
_DEFAULT_TIMEOUT_SECONDS = 8.0
_MAX_PAGE_SIZE = 100


class N8nConfigurationError(ValueError):
    """Raised when n8n connection settings are missing or unsafe."""


class N8nApiError(RuntimeError):
    """Raised when the n8n API cannot provide a valid response."""


@dataclass(frozen=True)
class N8nSettings:
    """Connection settings. API keys are intentionally hidden from repr()."""

    base_url: str
    api_key: str = field(repr=False)
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> "N8nSettings":
        """Load credentials from process environment; never from committed config."""
        source = os.environ if environ is None else environ
        base_url = source.get("TARA_N8N_BASE_URL", "").strip()
        api_key = source.get("TARA_N8N_API_KEY", "").strip()
        if not base_url or not api_key:
            raise N8nConfigurationError(
                "Set TARA_N8N_BASE_URL and TARA_N8N_API_KEY to enable n8n access"
            )
        timeout_raw = source.get("TARA_N8N_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS))
        try:
            timeout = float(timeout_raw)
        except (TypeError, ValueError):
            raise N8nConfigurationError("TARA_N8N_TIMEOUT_SECONDS must be a number") from None
        if not 1 <= timeout <= 30:
            raise N8nConfigurationError("TARA_N8N_TIMEOUT_SECONDS must be between 1 and 30")
        normalized_url = _validate_base_url(base_url)
        return cls(normalized_url, api_key, timeout)


def _validate_base_url(value: str) -> str:
    """Allow HTTPS endpoints, or plain HTTP only for loopback development."""
    if len(value) > 2048:
        raise N8nConfigurationError("n8n base URL is too long")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise N8nConfigurationError("n8n base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise N8nConfigurationError("n8n base URL must not contain credentials, query, or fragment")
    if parsed.scheme == "http":
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 80, type=socket.SOCK_STREAM)
        except OSError:
            raise N8nConfigurationError("n8n HTTP endpoint could not be resolved") from None
        if not addresses or any(not item[4][0].startswith(("127.", "::1")) for item in addresses):
            raise N8nConfigurationError("Plain HTTP is allowed only for loopback n8n instances")
    path = parsed.path.rstrip("/")
    if not path.endswith("/api/v1"):
        path = f"{path}/api/v1" if path else "/api/v1"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


class N8nReadOnlyClient:
    """Bounded read-only access to n8n workflows and executions."""

    def __init__(self, settings: N8nSettings) -> None:
        self._settings = settings
        self._opener = build_opener(NoRedirectHandler())

    def _get(self, resource: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
        if resource not in {"workflows", "executions"}:
            raise N8nApiError("unsupported n8n resource")
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self._settings.base_url}/{resource}{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-N8N-API-KEY": self._settings.api_key,
                "User-Agent": "TARA-App-n8n-adapter/1.0",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self._settings.timeout_seconds) as response:
                payload = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise N8nApiError(f"n8n API returned HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise N8nApiError("n8n API connection failed or timed out") from None
        if len(payload) > _MAX_RESPONSE_BYTES:
            raise N8nApiError("n8n API response exceeded the 1 MiB limit")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise N8nApiError("n8n API returned invalid JSON") from None
        if not isinstance(data, dict):
            raise N8nApiError("n8n API response must be a JSON object")
        return data

    @staticmethod
    def _records(payload: dict[str, Any], resource: str) -> list[dict[str, Any]]:
        records = payload.get("data")
        if not isinstance(records, list):
            raise N8nApiError(f"n8n {resource} response is missing a data list")
        if len(records) > _MAX_PAGE_SIZE:
            raise N8nApiError(f"n8n {resource} response exceeded the requested page size")
        return [item for item in records if isinstance(item, dict)]

    def connection_status(self) -> dict[str, Any]:
        """Verify API connectivity using a minimal read-only workflow query."""
        payload = self._get("workflows", {"limit": 1})
        self._records(payload, "workflows")
        return {"status": "connected", "provider": "n8n", "access": "read_only"}

    def list_workflows(self, *, limit: int = 50, cursor: str | None = None) -> dict[str, Any]:
        """List one bounded page of workflow metadata; workflow bodies are omitted."""
        if type(limit) is not int or not 1 <= limit <= _MAX_PAGE_SIZE:
            raise ValueError("limit must be an integer between 1 and 100")
        params: dict[str, str | int] = {"limit": limit}
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor or len(cursor) > 512:
                raise ValueError("cursor must be a non-empty string up to 512 characters")
            params["cursor"] = cursor
        payload = self._get("workflows", params)
        records = self._records(payload, "workflows")
        workflows = []
        for item in records:
            workflows.append({
                "id": str(item.get("id", ""))[:128],
                "name": str(item.get("name", ""))[:256],
                "active": item.get("active") if isinstance(item.get("active"), bool) else None,
                "created_at": str(item.get("createdAt", ""))[:64],
                "updated_at": str(item.get("updatedAt", ""))[:64],
            })
        next_cursor = payload.get("nextCursor")
        return {
            "status": "available",
            "workflows": workflows,
            "next_cursor": next_cursor if isinstance(next_cursor, str) and len(next_cursor) <= 512 else None,
        }

    def list_executions(
        self,
        *,
        limit: int = 20,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        """List bounded execution metadata without retrieving execution payloads."""
        if type(limit) is not int or not 1 <= limit <= _MAX_PAGE_SIZE:
            raise ValueError("limit must be an integer between 1 and 100")
        params: dict[str, str | int] = {"limit": limit}
        if workflow_id is not None:
            if not isinstance(workflow_id, str) or not workflow_id.strip() or len(workflow_id) > 128:
                raise ValueError("workflow_id must be a non-empty string up to 128 characters")
            params["workflowId"] = workflow_id
        payload = self._get("executions", params)
        records = self._records(payload, "executions")
        executions = []
        for item in records:
            executions.append({
                "id": str(item.get("id", ""))[:128],
                "workflow_id": str(item.get("workflowId", ""))[:128],
                "status": str(item.get("status", ""))[:32],
                "started_at": str(item.get("startedAt", ""))[:64],
                "stopped_at": str(item.get("stoppedAt", ""))[:64],
                "finished": item.get("finished") if isinstance(item.get("finished"), bool) else None,
            })
        return {"status": "available", "executions": executions}
