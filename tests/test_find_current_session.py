"""Tests for find_current_session strict mode."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cozempic.session import find_current_session


def _write_session(proj_dir: Path, session_id: str, content: str = "") -> Path:
    proj_dir.mkdir(parents=True, exist_ok=True)
    p = proj_dir / f"{session_id}.jsonl"
    p.write_text(content or json.dumps({"message": {"role": "user", "content": "hi"}}) + "\n",
                 encoding="utf-8")
    return p


class TestStrictMode:
    def test_strict_returns_none_when_only_fallback_available(self, tmp_path):
        """With no process or CWD match, strict=True returns None instead of guessing."""
        proj = tmp_path / "projects" / "-some-other-path"
        _write_session(proj, "aaaa1111-0000-0000-0000-000000000000")

        with (
            patch("cozempic.session.get_projects_dir", return_value=tmp_path / "projects"),
            patch("cozempic.session._session_id_from_process", return_value=None),
        ):
            result = find_current_session(cwd="/unrelated/path", strict=True)

        assert result is None

    def test_non_strict_returns_fallback(self, tmp_path):
        """With no process or CWD match, strict=False still returns most recent session."""
        proj = tmp_path / "projects" / "-some-other-path"
        _write_session(proj, "aaaa1111-0000-0000-0000-000000000000")

        with (
            patch("cozempic.session.get_projects_dir", return_value=tmp_path / "projects"),
            patch("cozempic.session._session_id_from_process", return_value=None),
        ):
            result = find_current_session(cwd="/unrelated/path", strict=False)

        assert result is not None
        assert result["session_id"] == "aaaa1111-0000-0000-0000-000000000000"

    def test_strict_succeeds_when_process_detected(self, tmp_path):
        """Process-based detection (Strategy 1) satisfies strict mode."""
        session_id = "bbbb2222-0000-0000-0000-000000000000"
        proj = tmp_path / "projects" / "-some-path"
        _write_session(proj, session_id)

        with (
            patch("cozempic.session.get_projects_dir", return_value=tmp_path / "projects"),
            patch("cozempic.session._session_id_from_process", return_value=session_id),
        ):
            result = find_current_session(strict=True)

        assert result is not None
        assert result["session_id"] == session_id

    def test_strict_succeeds_on_cwd_slug_match(self, tmp_path):
        """CWD slug match (Strategy 3) satisfies strict mode."""
        cwd = "/Users/foo/myproject"
        slug = cwd.replace("/", "-")
        proj = tmp_path / "projects" / slug
        session_id = "cccc3333-0000-0000-0000-000000000000"
        _write_session(proj, session_id)

        with (
            patch("cozempic.session.get_projects_dir", return_value=tmp_path / "projects"),
            patch("cozempic.session._session_id_from_process", return_value=None),
        ):
            result = find_current_session(cwd=cwd, strict=True)

        assert result is not None
        assert result["session_id"] == session_id

    def test_no_sessions_returns_none_regardless_of_strict(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()

        with (
            patch("cozempic.session.get_projects_dir", return_value=projects),
            patch("cozempic.session._session_id_from_process", return_value=None),
        ):
            assert find_current_session(strict=True) is None
            assert find_current_session(strict=False) is None


class TestSlugRoundTrip:
    def test_simple_path_round_trips(self):
        from cozempic.session import cwd_to_project_slug, project_slug_to_path
        path = "/Users/foo/myproject"
        slug = cwd_to_project_slug(path)
        assert project_slug_to_path(slug) == path

    @pytest.mark.xfail(
        reason=(
            "Hyphenated directory names are ambiguous: "
            "'/Users/foo/my-project' and '/Users/foo/my/project' "
            "produce the same slug '-Users-foo-my-project'. "
            "Fix requires encoding hyphens in directory names during slug generation."
        ),
        strict=True,
    )
    def test_hyphenated_directory_name_round_trips(self):
        from cozempic.session import cwd_to_project_slug, project_slug_to_path
        path = "/Users/foo/my-project"
        slug = cwd_to_project_slug(path)
        assert project_slug_to_path(slug) == path
