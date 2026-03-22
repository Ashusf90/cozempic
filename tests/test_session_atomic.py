"""Tests for atomic write behaviour in save_messages."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from cozempic.session import load_messages, save_messages


def _make_messages(path: Path, n: int = 5) -> list:
    lines = [json.dumps({"message": {"role": "user", "content": f"msg {i}"}}) for i in range(n)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return load_messages(path)


class TestAtomicWrite:
    def test_no_tmp_left_on_success(self, tmp_path):
        """No .tmp file should remain after a successful save."""
        jsonl = tmp_path / "sess.jsonl"
        messages = _make_messages(jsonl)
        save_messages(jsonl, messages, create_backup=False)
        assert not (tmp_path / "sess.tmp").exists()

    def test_content_correct_after_save(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        messages = _make_messages(jsonl)
        save_messages(jsonl, messages, create_backup=False)
        reloaded = load_messages(jsonl)
        assert len(reloaded) == len(messages)
        for (_, orig, _), (_, reloaded_msg, _) in zip(messages, reloaded):
            assert orig == reloaded_msg

    def test_tmp_cleaned_on_fsync_error(self, tmp_path, monkeypatch):
        """If os.fsync raises, the .tmp file is deleted and the original untouched."""
        jsonl = tmp_path / "sess.jsonl"
        original_text = "\n".join(
            json.dumps({"message": {"role": "user", "content": f"original {i}"}}) for i in range(3)
        ) + "\n"
        jsonl.write_text(original_text, encoding="utf-8")
        messages = load_messages(jsonl)

        import os as _os
        real_fsync = _os.fsync

        def boom(fd):
            raise OSError("disk full")

        monkeypatch.setattr(_os, "fsync", boom)

        with pytest.raises(OSError):
            save_messages(jsonl, messages, create_backup=False)

        # Original file should be intact
        assert jsonl.read_text(encoding="utf-8") == original_text
        # .tmp should be cleaned up
        tmp_file = jsonl.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_concurrent_writer_produces_valid_jsonl(self, tmp_path):
        """A background thread appending lines while save_messages runs must not
        corrupt the file (atomic rename guarantees the reader sees either the
        old or new version, never a partial write)."""
        jsonl = tmp_path / "sess.jsonl"
        messages = _make_messages(jsonl, n=20)

        errors: list[str] = []
        stop = threading.Event()

        def _appender():
            """Simulates Claude appending new lines to the session file."""
            while not stop.is_set():
                try:
                    with open(jsonl, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"message": {"role": "user", "content": "appended"}}) + "\n")
                except OSError:
                    pass
                time.sleep(0.005)

        t = threading.Thread(target=_appender, daemon=True)
        t.start()

        # Run several save cycles while the appender is active
        for _ in range(10):
            try:
                save_messages(jsonl, messages, create_backup=False)
            except Exception as e:
                errors.append(str(e))
            time.sleep(0.01)

        stop.set()
        t.join(timeout=2)

        assert not errors, f"save_messages raised: {errors}"

        # Final file must be valid JSONL (no partial lines)
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)  # raises if corrupt

    def test_backup_created_with_timestamp(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        messages = _make_messages(jsonl)
        backup = save_messages(jsonl, messages, create_backup=True)
        assert backup is not None
        assert backup.exists()
        assert backup.suffix == ".bak"
        assert "jsonl" in backup.name

    def test_no_backup_when_disabled(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        messages = _make_messages(jsonl)
        backup = save_messages(jsonl, messages, create_backup=False)
        assert backup is None
