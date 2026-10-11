"""OCI capacity runner with deterministic retry logic.

The runner prefers to drive Terraform so that state stays authoritative.  It
classifies command output / exceptions and retries according to the policy
from docs/AUDIT.md.
"""

from __future__ import annotations

import json
import logging
import random
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from oci.exceptions import ServiceError  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

CAPACITY_MESSAGE = "Out of host capacity"
RATE_LIMIT_MESSAGES = ("TooManyRequests", "429")
QUOTA_CODE = "LimitExceeded"
AUTH_STATUSES = {401, 403, 404}
CAPACITY_STATUS = 500
RATE_LIMIT_STATUS = 429
QUOTA_STATUS = 400


class CapacityError(Exception):
    """Base class for capacity-runner failures."""


class OutOfHostCapacityError(CapacityError):
    """OCI has no host capacity in the target availability domain."""


class RateLimitError(CapacityError):
    """OCI rate-limited the request."""


class QuotaExceededError(CapacityError):
    """OCI service limit (quota) exceeded."""


class AuthError(CapacityError):
    """Authentication or authorization error."""


class MaxRuntimeExceededError(CapacityError):
    """Maximum runtime was reached before success."""


ERROR_MAP: dict[type[CapacityError], str] = {
    OutOfHostCapacityError: "out_of_host_capacity",
    RateLimitError: "rate_limit",
    QuotaExceededError: "quota_exceeded",
    AuthError: "auth_error",
    MaxRuntimeExceededError: "max_runtime_exceeded",
}


def classify_exception(exc: BaseException) -> CapacityError:
    """Classify an OCI SDK exception into a capacity-runner error."""
    if isinstance(exc, ServiceError):
        message = (getattr(exc, "message", "") or "").lower()
        status = getattr(exc, "status", 0)
        code = getattr(exc, "code", "") or ""

        if status == CAPACITY_STATUS and CAPACITY_MESSAGE.lower() in message:
            return OutOfHostCapacityError(str(exc))
        if status == RATE_LIMIT_STATUS or code in RATE_LIMIT_MESSAGES:
            return RateLimitError(str(exc))
        if status == QUOTA_STATUS and code == QUOTA_CODE:
            return QuotaExceededError(str(exc))
        if status in AUTH_STATUSES:
            return AuthError(str(exc))

    return CapacityError(str(exc))


def classify_output(stdout: str, stderr: str) -> CapacityError | None:
    """Classify terraform/oci-cli output into a capacity-runner error.

    Returns ``None`` when no known error pattern is found.
    """
    combined = f"{stdout}\n{stderr}".lower()
    lower_capacity = CAPACITY_MESSAGE.lower()

    if lower_capacity in combined:
        return OutOfHostCapacityError("Out of host capacity detected in command output")
    if "429" in combined or "too many requests" in combined:
        return RateLimitError("Rate limit detected in command output")
    if "LimitExceeded".lower() in combined:
        return QuotaExceededError("Quota exceeded detected in command output")
    if any(status in combined for status in ("401", "403", "404")):
        return AuthError("Auth error detected in command output")

    return None


def rotate_ad(current: str, ads: list[str]) -> str:
    """Return the next availability domain in the list."""
    if not ads:
        raise CapacityError("No availability domains configured")
    try:
        idx = ads.index(current)
    except ValueError:
        return ads[0]
    return ads[(idx + 1) % len(ads)]


def jittered_sleep(base_seconds: float, max_jitter: float) -> None:
    """Sleep for ``base_seconds`` plus a random jitter up to ``max_jitter``."""
    duration = base_seconds + random.uniform(0, max_jitter)
    time.sleep(duration)


def exponential_backoff(attempt: int, base: float = 1.0, cap: float = 900.0) -> float:
    """Return backoff seconds for a rate-limit retry."""
    return min(base * (2**attempt), cap)


@dataclass(frozen=True)
class CommandResult:
    """Minimal result returned by a runner command."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RunResult:
    """Result of a capacity-runner attempt."""

    returncode: int
    stdout: str
    stderr: str
    attempts: int
    duration_seconds: float
    final_ad: str


class CapacityRunner:
    """Retry terraform/OCI commands until success or a terminal error."""

    def __init__(
        self,
        *,
        command: list[str],
        ads: list[str],
        max_runtime: timedelta = timedelta(hours=2),
        dry_run: bool = True,
        runner: Callable[[list[str]], CommandResult] | None = None,
    ) -> None:
        self.command = list(command)
        self.ads = list(ads)
        self.max_runtime = max_runtime
        self.dry_run = dry_run
        self._runner = runner or self._default_runner
        self._start: datetime | None = None

    @staticmethod
    def _default_runner(command: list[str]) -> CommandResult:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        return CommandResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def _elapsed(self) -> float:
        if self._start is None:
            raise RuntimeError("Timer not started")
        return (datetime.now(UTC) - self._start).total_seconds()

    def _remaining(self) -> float:
        return max(0.0, self.max_runtime.total_seconds() - self._elapsed())

    def _build_command(self, ad: str) -> list[str]:
        cmd = list(self.command)
        if self.dry_run:
            cmd.append("-dry-run")
        return cmd + ["-var", f"availability_domain={ad}"]

    def _log_event(
        self,
        event: str,
        *,
        attempt: int,
        ad: str,
        error: str | None = None,
        sleep_seconds: float | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            "attempt": attempt,
            "ad": ad,
            "dry_run": self.dry_run,
        }
        if error is not None:
            payload["error"] = error
        if sleep_seconds is not None:
            payload["sleep_seconds"] = sleep_seconds
        logger.info(json.dumps(payload))

    def run(self) -> RunResult:
        """Run the command, retrying according to the capacity policy."""
        if not self.ads:
            raise CapacityError("No availability domains configured")

        self._start = datetime.now(UTC)
        current_ad = self.ads[0]
        attempt = 0
        rate_limit_attempts = 0

        while True:
            attempt += 1
            if self._elapsed() >= self.max_runtime.total_seconds():
                self._log_event(
                    "max_runtime_exceeded",
                    attempt=attempt,
                    ad=current_ad,
                )
                raise MaxRuntimeExceededError(
                    f"Max runtime {self.max_runtime} exceeded after {attempt} attempts"
                )

            cmd = self._build_command(current_ad)
            self._log_event("attempt", attempt=attempt, ad=current_ad)

            try:
                proc = self._runner(cmd)
            except Exception as exc:  # noqa: BLE001
                classified = classify_exception(exc)
                self._handle_error(
                    classified,
                    current_ad=current_ad,
                    attempt=attempt,
                    rate_limit_attempts=rate_limit_attempts,
                )
                if isinstance(classified, RateLimitError):
                    rate_limit_attempts += 1
                continue

            if proc.returncode == 0:
                self._log_event(
                    "success",
                    attempt=attempt,
                    ad=current_ad,
                )
                return RunResult(
                    returncode=0,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    attempts=attempt,
                    duration_seconds=self._elapsed(),
                    final_ad=current_ad,
                )

            error = classify_output(proc.stdout, proc.stderr)
            if error is None:
                return RunResult(
                    returncode=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    attempts=attempt,
                    duration_seconds=self._elapsed(),
                    final_ad=current_ad,
                )

            self._handle_error(
                error,
                current_ad=current_ad,
                attempt=attempt,
                rate_limit_attempts=rate_limit_attempts,
            )
            if isinstance(error, RateLimitError):
                rate_limit_attempts += 1
            elif isinstance(error, OutOfHostCapacityError):
                current_ad = rotate_ad(current_ad, self.ads)
                rate_limit_attempts = 0

    def _handle_error(
        self,
        error: CapacityError,
        *,
        current_ad: str,
        attempt: int,
        rate_limit_attempts: int,
    ) -> None:
        """Sleep and continue, or raise for terminal errors."""
        error_type = ERROR_MAP.get(type(error), "unknown")
        self._log_event(
            "error",
            attempt=attempt,
            ad=current_ad,
            error=error_type,
        )

        if isinstance(error, QuotaExceededError | AuthError):
            raise error

        if isinstance(error, OutOfHostCapacityError):
            sleep = min(120.0, self._remaining())
            jitter = min(60.0, self._remaining())
            if sleep > 0:
                self._log_event(
                    "sleep",
                    attempt=attempt,
                    ad=current_ad,
                    sleep_seconds=sleep,
                )
                jittered_sleep(sleep, jitter)
            return

        if isinstance(error, RateLimitError):
            backoff = exponential_backoff(rate_limit_attempts, base=1.0, cap=900.0)
            sleep = min(backoff, self._remaining())
            if sleep > 0:
                self._log_event(
                    "sleep",
                    attempt=attempt,
                    ad=current_ad,
                    sleep_seconds=sleep,
                )
                jittered_sleep(sleep, max_jitter=0.0)
            return

        raise error


def main() -> NoReturn:  # pragma: no cover - CLI entry point tested via integration tests
    """CLI entry point for manual capacity-runner usage."""
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
    runner = CapacityRunner(
        command=["terraform", "apply", "-input=false", "-auto-approve"],
        ads=["AD-1", "AD-2", "AD-3"],
        dry_run=True,
    )
    try:
        result = runner.run()
        print(json.dumps(result.__dict__))
        sys.exit(0)
    except CapacityError as exc:
        logger.error(json.dumps({"event": "fatal", "error": str(exc)}))
        sys.exit(1)
