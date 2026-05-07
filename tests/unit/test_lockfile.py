import errno
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.lockfile import acquire, check_stale, read_lock, release


def _lock_path(case_path: Path) -> Path:
    return case_path / ".lock"


def _write_lock(case_path: Path, pid: int, start: datetime) -> None:
    _lock_path(case_path).write_text(f"pid={pid}\nstart={start.isoformat()}\n")


def test_acquire_creates_lockfile_with_correct_format(tmp_path):
    acquire(tmp_path)
    lock_file = _lock_path(tmp_path)
    assert lock_file.exists()
    lines = lock_file.read_text().splitlines()
    assert lines[0] == f"pid={os.getpid()}"
    datetime.fromisoformat(lines[1].split("=", 1)[1])


def test_acquire_raises_if_lockfile_exists(tmp_path):
    acquire(tmp_path)
    with pytest.raises(RuntimeError):
        acquire(tmp_path)


def test_release_removes_lockfile(tmp_path):
    acquire(tmp_path)
    release(tmp_path)
    assert not _lock_path(tmp_path).exists()


def test_release_noop_if_missing(tmp_path):
    release(tmp_path)


def test_check_stale_returns_false_if_missing(tmp_path):
    assert check_stale(tmp_path) is False


def test_check_stale_returns_true_when_old_and_process_gone(tmp_path):
    old_start = datetime.now(timezone.utc) - timedelta(seconds=7200)
    _write_lock(tmp_path, pid=99999, start=old_start)

    with patch("scripts.lockfile.os.kill", side_effect=ProcessLookupError):
        result = check_stale(tmp_path, ttl_seconds=3600)

    assert result is True
    assert not _lock_path(tmp_path).exists()


def test_check_stale_returns_false_when_process_exists(tmp_path):
    old_start = datetime.now(timezone.utc) - timedelta(seconds=7200)
    _write_lock(tmp_path, pid=99999, start=old_start)

    with patch("scripts.lockfile.os.kill", side_effect=PermissionError):
        result = check_stale(tmp_path, ttl_seconds=3600)

    assert result is False
    assert _lock_path(tmp_path).exists()


def test_check_stale_age_only_fallback_unexpected_oserror(tmp_path):
    old_start = datetime.now(timezone.utc) - timedelta(seconds=7200)
    _write_lock(tmp_path, pid=99999, start=old_start)

    unexpected = OSError()
    unexpected.errno = errno.EACCES

    with patch("scripts.lockfile.os.kill", side_effect=unexpected):
        result = check_stale(tmp_path, ttl_seconds=3600)

    assert result is True
    assert not _lock_path(tmp_path).exists()


def test_check_stale_returns_false_when_age_within_ttl(tmp_path):
    recent_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    _write_lock(tmp_path, pid=99999, start=recent_start)

    result = check_stale(tmp_path, ttl_seconds=3600)

    assert result is False


def test_read_lock_returns_dict_when_valid(tmp_path):
    acquire(tmp_path)
    result = read_lock(tmp_path)
    assert isinstance(result, dict)
    assert result["pid"] == os.getpid()
    datetime.fromisoformat(result["start"])


def test_read_lock_returns_none_when_missing(tmp_path):
    assert read_lock(tmp_path) is None
