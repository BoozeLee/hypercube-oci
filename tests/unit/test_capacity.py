"""Tests for the OCI capacity runner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st
from oci.exceptions import ServiceError

from hypercube.capacity import (
    AuthError,
    CapacityError,
    CapacityRunner,
    CommandResult,
    MaxRuntimeExceededError,
    OutOfHostCapacityError,
    QuotaExceededError,
    RateLimitError,
    classify_exception,
    classify_output,
    exponential_backoff,
    rotate_ad,
)

Runner = Callable[[list[str]], CommandResult]


def fake_runner(responses: list[CommandResult]) -> Runner:
    """Return a runner that yields responses in order."""
    calls: list[list[str]] = []

    def runner(command: list[str]) -> CommandResult:
        calls.append(command)
        if not responses:
            raise RuntimeError("runner exhausted")
        return responses.pop(0)

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def make_service_error(status: int, code: str, message: str) -> ServiceError:
    return ServiceError(status=status, code=code, headers={}, message=message)


# ---------------------------------------------------------------------------
# classify_exception
# ---------------------------------------------------------------------------


def test_classify_out_of_host_capacity() -> None:
    exc = make_service_error(
        500, "InternalError", "Out of host capacity for shape VM.Standard.A1.Flex"
    )
    classified = classify_exception(exc)
    assert isinstance(classified, OutOfHostCapacityError)


def test_classify_rate_limit() -> None:
    exc = make_service_error(429, "TooManyRequests", "Too many requests")
    classified = classify_exception(exc)
    assert isinstance(classified, RateLimitError)


def test_classify_quota_exceeded() -> None:
    exc = make_service_error(400, "LimitExceeded", "Service limit reached")
    classified = classify_exception(exc)
    assert isinstance(classified, QuotaExceededError)


@pytest.mark.parametrize("status", [401, 403, 404])
def test_classify_auth_error(status: int) -> None:
    exc = make_service_error(status, "NotAuthenticated", "auth failed")
    classified = classify_exception(exc)
    assert isinstance(classified, AuthError)


def test_classify_unknown_service_error() -> None:
    exc = make_service_error(500, "InternalError", "some other error")
    classified = classify_exception(exc)
    assert type(classified) is CapacityError


@given(
    status=st.integers(min_value=100, max_value=599),
    code=st.sampled_from(["", "LimitExceeded", "TooManyRequests", "InternalError"]),
    message=st.text(),
)
def test_classify_exception_never_raises(status: int, code: str, message: str) -> None:
    exc = make_service_error(status, code, message)
    result = classify_exception(exc)
    assert isinstance(result, CapacityError)


# ---------------------------------------------------------------------------
# classify_output
# ---------------------------------------------------------------------------


def test_classify_output_capacity() -> None:
    err = classify_output("", "Error: Out of host capacity")
    assert isinstance(err, OutOfHostCapacityError)


def test_classify_output_rate_limit() -> None:
    err = classify_output("", "HTTP 429 Too Many Requests")
    assert isinstance(err, RateLimitError)


def test_classify_output_quota() -> None:
    err = classify_output("", "LimitExceeded: standard-a1 count")
    assert isinstance(err, QuotaExceededError)


def test_classify_output_auth() -> None:
    err = classify_output("", "401 NotAuthenticated")
    assert isinstance(err, AuthError)


def test_classify_output_none() -> None:
    assert classify_output("ok", "") is None


# ---------------------------------------------------------------------------
# rotate_ad
# ---------------------------------------------------------------------------


def test_rotate_ad_cycles() -> None:
    ads = ["AD-1", "AD-2", "AD-3"]
    assert rotate_ad("AD-1", ads) == "AD-2"
    assert rotate_ad("AD-3", ads) == "AD-1"


def test_rotate_ad_unknown_returns_first() -> None:
    assert rotate_ad("AD-X", ["AD-1", "AD-2"]) == "AD-1"


# ---------------------------------------------------------------------------
# exponential_backoff
# ---------------------------------------------------------------------------


def test_exponential_backoff_capped() -> None:
    assert exponential_backoff(0, base=1.0, cap=900.0) == 1.0
    assert exponential_backoff(10, base=1.0, cap=900.0) == 900.0


# ---------------------------------------------------------------------------
# CapacityRunner
# ---------------------------------------------------------------------------


def test_runner_success_first_attempt() -> None:
    runner = CapacityRunner(
        command=["echo", "hello"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=True,
        runner=fake_runner([CommandResult(0, "hello", "")]),
    )
    result = runner.run()
    assert result.returncode == 0
    assert result.attempts == 1
    assert result.final_ad == "AD-1"


def test_runner_retries_capacity_and_rotates_ad() -> None:
    responses = [
        CommandResult(1, "", "Out of host capacity"),
        CommandResult(1, "", "Out of host capacity"),
        CommandResult(0, "ok", ""),
    ]
    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1", "AD-2", "AD-3"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=fake_runner(responses),
    )
    result = runner.run()
    assert result.returncode == 0
    assert result.attempts == 3
    assert result.final_ad == "AD-3"


def test_runner_stops_on_quota() -> None:
    responses = [CommandResult(1, "", "LimitExceeded: cores")]
    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=fake_runner(responses),
    )
    with pytest.raises(QuotaExceededError):
        runner.run()


def test_runner_stops_on_auth() -> None:
    responses = [CommandResult(1, "", "401 NotAuthenticated")]
    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=fake_runner(responses),
    )
    with pytest.raises(AuthError):
        runner.run()


def test_runner_returns_unknown_failure() -> None:
    responses = [CommandResult(1, "", "random error")]
    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=fake_runner(responses),
    )
    result = runner.run()
    assert result.returncode == 1


def test_runner_classifies_oci_exception() -> None:
    def raising_runner(_command: list[str]) -> CommandResult:
        raise make_service_error(400, "LimitExceeded", "quota")

    runner = CapacityRunner(
        command=["oci"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=raising_runner,
    )
    with pytest.raises(QuotaExceededError):
        runner.run()


def test_classify_non_service_error() -> None:
    classified = classify_exception(RuntimeError("boom"))
    assert type(classified) is CapacityError


def test_classify_output_auth_403() -> None:
    err = classify_output("", "403 NotAuthorized")
    assert isinstance(err, AuthError)


def test_classify_output_auth_404() -> None:
    err = classify_output("", "404 NotFound")
    assert isinstance(err, AuthError)


def test_rotate_ad_empty_raises() -> None:
    with pytest.raises(CapacityError):
        rotate_ad("AD-1", [])


def test_runner_empty_ads_raises() -> None:
    with pytest.raises(CapacityError):
        CapacityRunner(command=["echo"], ads=[]).run()


def test_runner_builds_dry_run_command() -> None:
    calls: list[list[str]] = []

    def capturing_runner(command: list[str]) -> CommandResult:
        calls.append(command)
        return CommandResult(0, "", "")

    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=True,
        runner=capturing_runner,
    )
    runner.run()
    assert "-dry-run" in calls[0]
    assert "availability_domain=AD-1" in calls[0]


def test_runner_max_runtime_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hypercube.capacity.jittered_sleep",
        lambda _base, _jitter: None,
    )

    call_count = 0

    def slow_runner(_command: list[str]) -> CommandResult:
        nonlocal call_count
        call_count += 1
        return CommandResult(1, "", "Out of host capacity")

    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(seconds=0),
        dry_run=False,
        runner=slow_runner,
    )
    with pytest.raises(MaxRuntimeExceededError):
        runner.run()
    assert call_count == 0


def test_runner_rate_limit_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    def capture_sleep(base: float, **_kwargs: object) -> None:
        sleeps.append(base)

    monkeypatch.setattr(
        "hypercube.capacity.jittered_sleep",
        capture_sleep,
    )

    runner = CapacityRunner(
        command=["tf", "apply"],
        ads=["AD-1"],
        max_runtime=timedelta(minutes=5),
        dry_run=False,
        runner=fake_runner(
            [
                CommandResult(1, "", "429 Too Many Requests"),
                CommandResult(1, "", "429 Too Many Requests"),
                CommandResult(0, "ok", ""),
            ]
        ),
    )
    result = runner.run()
    assert result.returncode == 0
    assert sleeps == [1.0, 2.0]
