from datetime import date, datetime
from pathlib import Path

import frontmatter


_DEFAULT_DIR = Path(__file__).parent.parent / "learnings"


def read_all(learnings_dir: Path | None = None) -> list[dict]:
    directory = learnings_dir or _DEFAULT_DIR
    entries = []
    for path in sorted(directory.glob("*.md")):
        post = frontmatter.load(str(path))
        entry = dict(post.metadata)
        entry["body"] = post.content
        entry["path"] = path
        entries.append(entry)
    return entries


def filter_pending(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("status") == "pending"]


def group_by_type(entries: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        key = entry.get("type", "")
        groups.setdefault(key, []).append(entry)
    return groups


def count_pending_older_than(entries: list[dict], days: int) -> int:
    cutoff = date.today().toordinal() - days
    count = 0
    for entry in filter_pending(entries):
        raw = entry.get("date", "")
        try:
            entry_date = datetime.fromisoformat(str(raw)).date()
        except (ValueError, TypeError):
            continue
        if entry_date.toordinal() < cutoff:
            count += 1
    return count
