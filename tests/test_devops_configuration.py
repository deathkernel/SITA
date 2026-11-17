from __future__ import annotations

import pytest

from tara_app.runtime import RuntimeConfigurationError, _omniroute_settings
from tara_app.webapp import _allowed_hosts


def test_allowed_hosts_default_to_loopback_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SITA_ALLOWED_HOSTS", raising=False)

    assert _allowed_hosts(8765) == {"127.0.0.1:8765", "localhost:8765"}


def test_allowed_hosts_accept_only_explicit_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITA_ALLOWED_HOSTS", "localhost:8765, 127.0.0.1:8765")

    assert _allowed_hosts(8765) == {"localhost:8765", "127.0.0.1:8765"}


@pytest.mark.parametrize(
    "configured",
    ["https://localhost:8765", "localhost:8765/path", "user@localhost:8765", "   "],
)
def test_allowed_hosts_fail_closed_for_malformed_values(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
) -> None:
    monkeypatch.setenv("SITA_ALLOWED_HOSTS", configured)

    assert _allowed_hosts(8765) == set()


def test_omniroute_accepts_docker_host_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TARA_OMNIROUTE_BASE_URL",
        "http://host.docker.internal:20128/v1",
    )
    monkeypatch.delenv("TARA_OMNIROUTE_API_KEY", raising=False)

    settings = _omniroute_settings({"models": {}})

    assert settings["chat"]["TARA_OMNIROUTE_BASE_URL"] == (
        "http://host.docker.internal:20128/v1"
    )


def test_omniroute_still_rejects_nonlocal_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TARA_OMNIROUTE_BASE_URL",
        "https://example.com/v1",
    )

    with pytest.raises(RuntimeConfigurationError):
        _omniroute_settings({"models": {}})
