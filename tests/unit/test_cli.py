"""Tests for the CLI entry point."""

from hypercube.cli import main


def test_main_returns_zero() -> None:
    assert main() == 0
