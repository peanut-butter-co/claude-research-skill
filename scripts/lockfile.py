import errno
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _lock_path(case_path: Path) -> Path:
    return case_path / ".lock"


def _parse_lock(lock_file: Path) -> tuple[int, datetime] | None:
    try:
        lines = lock_file.read_text().splitlines()
        pid = int(lines[0].split("=", 1)[1])
        start = datetime.fromisoformat(lines[1].split("=", 1)[1])
        return pid, start
    except Exception:
        return None


def acquire(case_path: Path) -> None:
    lock_file = _lock_path(case_path)
    if lock_file.exists():
        raise RuntimeError(f"Lockfile already exists: {lock_file}")
    now = datetime.now(timezone.utc).isoformat()
    lock_file.write_text(f"pid={os.getpid()}\nstart={now}\n")


def release(case_path: Path) -> None:
    lock_file = _lock_path(case_path)
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass


def check_stale(case_path: Path, ttl_seconds: int = 3600) -> bool:
    lock_file = _lock_path(case_path)
    if not lock_file.exists():
        return False

    parsed = _parse_lock(lock_file)
    if parsed is None:
        lock_file.unlink(missing_ok=True)
        return True

    pid, start = parsed
    now = datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    age = (now - start).total_seconds()

    if age <= ttl_seconds:
        return False

    if sys.platform == "win32":
        lock_file.unlink(missing_ok=True)
        return True

    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        lock_file.unlink(missing_ok=True)
        return True
    except PermissionError:
        return False
    except OSError as exc:
        if exc.errno not in (errno.ESRCH, errno.EPERM):
            lock_file.unlink(missing_ok=True)
            return True
        return False


def read_lock(case_path: Path) -> dict | None:
    lock_file = _lock_path(case_path)
    if not lock_file.exists():
        return None
    parsed = _parse_lock(lock_file)
    if parsed is None:
        return None
    pid, start = parsed
    return {"pid": pid, "start": start.isoformat()}
