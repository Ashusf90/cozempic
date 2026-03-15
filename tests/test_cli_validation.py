"""Tests for CLI argument validation (BMAD R4-12)."""

from __future__ import annotations

import os
from unittest.mock import patch

from cozempic.cli import _prescan_argv


class TestPrescanArgvValidation:
    def test_invalid_context_window_ignored(self):
        """Non-numeric --context-window is ignored with a warning."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)
            _prescan_argv(["treat", "current", "--context-window", "abc"])
            assert "COZEMPIC_CONTEXT_WINDOW" not in os.environ

    def test_negative_context_window_ignored(self):
        """Negative --context-window is ignored."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)
            _prescan_argv(["treat", "current", "--context-window", "-500"])
            assert "COZEMPIC_CONTEXT_WINDOW" not in os.environ

    def test_zero_context_window_ignored(self):
        """Zero --context-window is ignored."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)
            _prescan_argv(["treat", "current", "--context-window", "0"])
            assert "COZEMPIC_CONTEXT_WINDOW" not in os.environ

    def test_valid_context_window_set(self):
        """Valid positive --context-window is accepted."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)
            _prescan_argv(["treat", "current", "--context-window", "1000000"])
            assert os.environ["COZEMPIC_CONTEXT_WINDOW"] == "1000000"
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)

    def test_invalid_system_overhead_tokens_ignored(self):
        """Non-numeric --system-overhead-tokens is ignored."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_SYSTEM_OVERHEAD_TOKENS", None)
            _prescan_argv(["treat", "current", "--system-overhead-tokens", "xyz"])
            assert "COZEMPIC_SYSTEM_OVERHEAD_TOKENS" not in os.environ

    def test_valid_system_overhead_tokens_set(self):
        """Valid positive --system-overhead-tokens is accepted."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_SYSTEM_OVERHEAD_TOKENS", None)
            _prescan_argv(["treat", "current", "--system-overhead-tokens", "25000"])
            assert os.environ["COZEMPIC_SYSTEM_OVERHEAD_TOKENS"] == "25000"
            os.environ.pop("COZEMPIC_SYSTEM_OVERHEAD_TOKENS", None)

    def test_invalid_context_window_equals_form_ignored(self):
        """--context-window=abc (equals form) is ignored."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COZEMPIC_CONTEXT_WINDOW", None)
            _prescan_argv(["treat", "current", "--context-window=notanumber"])
            assert "COZEMPIC_CONTEXT_WINDOW" not in os.environ
