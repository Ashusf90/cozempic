"""Tests for model detection and context window logic."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cozempic.helpers import msg_bytes
from cozempic.tokens import (
    DEFAULT_CONTEXT_WINDOW,
    MODEL_CONTEXT_WINDOWS,
    detect_context_window,
    detect_model,
    estimate_session_tokens,
    get_context_window_override,
)


def make_message(line_idx: int, msg: dict) -> tuple[int, dict, int]:
    return (line_idx, msg, msg_bytes(msg))


def make_assistant_with_model(line_idx: int, model: str, input_tokens: int = 1000) -> tuple[int, dict, int]:
    msg = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": "response"}],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": 100,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }
    return make_message(line_idx, msg)


class TestDetectModel(unittest.TestCase):

    def test_detects_model_from_assistant(self):
        messages = [make_assistant_with_model(0, "claude-opus-4-6")]
        self.assertEqual(detect_model(messages), "claude-opus-4-6")

    def test_uses_last_assistant(self):
        messages = [
            make_assistant_with_model(0, "claude-sonnet-4-5"),
            make_assistant_with_model(1, "claude-opus-4-6"),
        ]
        self.assertEqual(detect_model(messages), "claude-opus-4-6")

    def test_skips_sidechain(self):
        sidechain = make_assistant_with_model(1, "claude-haiku-4-5")
        sidechain_msg = sidechain[1]
        sidechain_msg["isSidechain"] = True
        messages = [
            make_assistant_with_model(0, "claude-opus-4-6"),
            (1, sidechain_msg, sidechain[2]),
        ]
        self.assertEqual(detect_model(messages), "claude-opus-4-6")

    def test_returns_none_for_empty(self):
        self.assertIsNone(detect_model([]))

    def test_returns_none_for_no_model(self):
        msg = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "hi"}],
            },
        }
        messages = [make_message(0, msg)]
        self.assertIsNone(detect_model(messages))


class TestDetectContextWindow(unittest.TestCase):

    def test_opus_46_is_200k(self):
        messages = [make_assistant_with_model(0, "claude-opus-4-6")]
        self.assertEqual(detect_context_window(messages), 200_000)

    def test_sonnet_46_is_200k(self):
        messages = [make_assistant_with_model(0, "claude-sonnet-4-6")]
        self.assertEqual(detect_context_window(messages), 200_000)

    def test_unknown_model_falls_back(self):
        messages = [make_assistant_with_model(0, "claude-future-99")]
        self.assertEqual(detect_context_window(messages), DEFAULT_CONTEXT_WINDOW)

    def test_prefix_match(self):
        """Versioned model IDs like claude-opus-4-6-20260301 should match."""
        messages = [make_assistant_with_model(0, "claude-opus-4-6-20260301")]
        self.assertEqual(detect_context_window(messages), 200_000)

    def test_env_override(self):
        messages = [make_assistant_with_model(0, "claude-opus-4-6")]
        with patch.dict(os.environ, {"COZEMPIC_CONTEXT_WINDOW": "1000000"}):
            self.assertEqual(detect_context_window(messages), 1_000_000)

    def test_env_override_beats_model(self):
        messages = [make_assistant_with_model(0, "claude-sonnet-4-6")]
        with patch.dict(os.environ, {"COZEMPIC_CONTEXT_WINDOW": "500000"}):
            self.assertEqual(detect_context_window(messages), 500_000)

    def test_invalid_env_override_ignored(self):
        messages = [make_assistant_with_model(0, "claude-opus-4-6")]
        with patch.dict(os.environ, {"COZEMPIC_CONTEXT_WINDOW": "not_a_number"}):
            self.assertEqual(detect_context_window(messages), 200_000)


class TestGetContextWindowOverride(unittest.TestCase):

    def test_returns_none_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_context_window_override())

    def test_returns_int_when_set(self):
        with patch.dict(os.environ, {"COZEMPIC_CONTEXT_WINDOW": "1000000"}):
            self.assertEqual(get_context_window_override(), 1_000_000)

    def test_returns_none_for_invalid(self):
        with patch.dict(os.environ, {"COZEMPIC_CONTEXT_WINDOW": "abc"}):
            self.assertIsNone(get_context_window_override())


class TestEstimateSessionTokensWithModel(unittest.TestCase):

    def test_includes_model_in_result(self):
        messages = [make_assistant_with_model(0, "claude-opus-4-6", input_tokens=50000)]
        te = estimate_session_tokens(messages)
        self.assertEqual(te.model, "claude-opus-4-6")
        self.assertEqual(te.context_window, 200_000)
        self.assertEqual(te.total, 50000)
        self.assertEqual(te.context_pct, 25.0)

    def test_context_pct_uses_detected_window(self):
        """100K tokens on a 200K window should be 50%."""
        messages = [make_assistant_with_model(0, "claude-sonnet-4-6", input_tokens=100000)]
        te = estimate_session_tokens(messages)
        self.assertEqual(te.context_pct, 50.0)


if __name__ == "__main__":
    unittest.main()
