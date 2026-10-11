"""Shared pytest fixtures."""

import pytest

import hypercube.capacity as capacity


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable sleeps in the capacity runner so unit tests run quickly."""
    monkeypatch.setattr(capacity, "jittered_sleep", lambda _base, _jitter: None)
