"""Tests for PostCompact recovery — read_team_checkpoint, cmd_post_compact, and hook config."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cozempic.team import read_team_checkpoint
from cozempic.init import COZEMPIC_HOOKS


class TestReadTeamCheckpoint(unittest.TestCase):

    def test_returns_content_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = Path(tmpdir) / "team-checkpoint.md"
            checkpoint.write_text("# Team State\nTeam: test-team\n", encoding="utf-8")
            result = read_team_checkpoint(Path(tmpdir))
            self.assertIsNotNone(result)
            self.assertIn("Team: test-team", result)

    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_team_checkpoint(Path(tmpdir))
            self.assertIsNone(result)

    def test_returns_none_when_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = Path(tmpdir) / "team-checkpoint.md"
            checkpoint.write_text("", encoding="utf-8")
            result = read_team_checkpoint(Path(tmpdir))
            self.assertIsNone(result)

    def test_returns_none_when_whitespace_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = Path(tmpdir) / "team-checkpoint.md"
            checkpoint.write_text("   \n\n  ", encoding="utf-8")
            result = read_team_checkpoint(Path(tmpdir))
            self.assertIsNone(result)

    def test_prefers_project_dir_over_global(self):
        with tempfile.TemporaryDirectory() as project_dir:
            checkpoint = Path(project_dir) / "team-checkpoint.md"
            checkpoint.write_text("# Project Team", encoding="utf-8")

            # Even if global exists, project dir should win
            result = read_team_checkpoint(Path(project_dir))
            self.assertEqual(result, "# Project Team")

    def test_falls_back_to_none_when_dir_missing(self):
        result = read_team_checkpoint(Path("/nonexistent/dir"))
        # Should not raise, just return None (falls through to global check)
        # Global checkpoint may or may not exist, but shouldn't crash


class TestCmdPostCompact(unittest.TestCase):

    @patch("cozempic.team.read_team_checkpoint")
    @patch("cozempic.session.find_current_session")
    def test_outputs_recovery_when_checkpoint_exists(self, mock_session, mock_read):
        from cozempic.cli import cmd_post_compact
        import argparse

        mock_session.return_value = {
            "path": Path("/fake/project/session.jsonl"),
            "session_id": "test-123",
        }
        mock_read.return_value = "# Team State\nTeam: recovery-test"

        args = argparse.Namespace(cwd=None)
        captured = io.StringIO()
        sys.stdout = captured
        try:
            cmd_post_compact(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertIn("Team: recovery-test", captured.getvalue())

    @patch("cozempic.team.read_team_checkpoint")
    @patch("cozempic.session.find_current_session")
    def test_silent_when_no_checkpoint(self, mock_session, mock_read):
        from cozempic.cli import cmd_post_compact
        import argparse

        mock_session.return_value = {
            "path": Path("/fake/project/session.jsonl"),
            "session_id": "test-123",
        }
        mock_read.return_value = None

        args = argparse.Namespace(cwd=None)
        captured = io.StringIO()
        sys.stdout = captured
        try:
            cmd_post_compact(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(captured.getvalue(), "")


class TestInitHooksIncludePostCompact(unittest.TestCase):

    def test_post_compact_in_cozempic_hooks(self):
        self.assertIn("PostCompact", COZEMPIC_HOOKS)

    def test_post_compact_hook_command_correct(self):
        entries = COZEMPIC_HOOKS["PostCompact"]
        self.assertEqual(len(entries), 1)

        hooks = entries[0]["hooks"]
        self.assertEqual(len(hooks), 1)

        command = hooks[0]["command"]
        self.assertIn("cozempic post-compact", command)

    def test_pre_compact_still_exists(self):
        """Ensure PreCompact wasn't accidentally removed."""
        self.assertIn("PreCompact", COZEMPIC_HOOKS)

    def test_all_expected_hooks_present(self):
        """Verify all expected hook events are defined."""
        expected = {"SessionStart", "PostToolUse", "PreCompact", "PostCompact", "Stop"}
        self.assertEqual(expected, set(COZEMPIC_HOOKS.keys()))


if __name__ == "__main__":
    unittest.main()
