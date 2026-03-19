"""Tests for session module path helpers."""

from __future__ import annotations

import json

from pathlib import Path
from unittest.mock import patch

from cozempic.session import MAX_LINE_BYTES, get_claude_dir, get_claude_json_path, load_messages


class TestGetClaudeDir:
    def test_default(self):
        with patch.dict("os.environ", {}, clear=True):
            assert get_claude_dir() == Path.home() / ".claude"

    def test_with_config_dir(self, tmp_path):
        with patch.dict("os.environ", {"CLAUDE_CONFIG_DIR": str(tmp_path)}):
            assert get_claude_dir() == tmp_path


class TestGetClaudeJsonPath:
    def test_default(self):
        with patch.dict("os.environ", {}, clear=True):
            assert get_claude_json_path() == Path.home() / ".claude.json"

    def test_with_config_dir(self, tmp_path):
        with patch.dict("os.environ", {"CLAUDE_CONFIG_DIR": str(tmp_path)}):
            assert get_claude_json_path() == tmp_path / ".claude.json"

    def test_not_inside_claude_dir(self):
        """Default .claude.json is at ~/.claude.json, not ~/.claude/.claude.json."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_claude_json_path() != get_claude_dir() / ".claude.json"


class TestLoadMessagesLimits:
    def test_skips_oversized_lines(self, tmp_path):
        """Lines exceeding MAX_LINE_BYTES are silently skipped."""
        jsonl = tmp_path / "test.jsonl"
        normal = json.dumps({"role": "user", "content": "hello"})
        oversized = json.dumps({"role": "user", "content": "x" * (MAX_LINE_BYTES + 1)})
        jsonl.write_text(normal + "\n" + oversized + "\n")
        messages = load_messages(jsonl)
        assert len(messages) == 1
        assert messages[0][1]["content"] == "hello"

    def test_normal_lines_unaffected(self, tmp_path):
        """Normal-sized lines parse correctly."""
        jsonl = tmp_path / "test.jsonl"
        lines = [
            json.dumps({"role": "user", "content": "first"}),
            json.dumps({"role": "assistant", "content": "second"}),
        ]
        jsonl.write_text("\n".join(lines) + "\n")
        messages = load_messages(jsonl)
        assert len(messages) == 2
        assert messages[0][1]["content"] == "first"
        assert messages[1][1]["content"] == "second"
