from datetime import date, timedelta
from pathlib import Path

import frontmatter
import pytest

from scripts.learnings_index import (
    count_pending_older_than,
    filter_pending,
    group_by_type,
    read_all,
)
from scripts.learnings_write import next_id, update_status, write_learning


def _make_md(path: Path, **kwargs) -> None:
    meta = {
        "id": kwargs.get("id", "2026-01-01-001"),
        "date": kwargs.get("date", "2026-01-01"),
        "trigger": kwargs.get("trigger", "self-detection"),
        "context": kwargs.get("context", "test context"),
        "type": kwargs.get("type", "domain-fact"),
        "status": kwargs.get("status", "pending"),
    }
    body = kwargs.get("body", "Test body text.")
    post = frontmatter.Post(body, **meta)
    path.write_text(frontmatter.dumps(post))


def test_read_all_parses_frontmatter_and_body(tmp_path):
    _make_md(tmp_path / "entry.md", id="2026-01-01-001", body="Some content.")
    entries = read_all(tmp_path)
    assert len(entries) == 1
    e = entries[0]
    assert e["id"] == "2026-01-01-001"
    assert e["body"] == "Some content."
    assert e["path"] == tmp_path / "entry.md"


def test_filter_pending_returns_only_pending(tmp_path):
    _make_md(tmp_path / "a.md", status="pending")
    _make_md(tmp_path / "b.md", status="consolidated")
    _make_md(tmp_path / "c.md", status="discarded")
    entries = read_all(tmp_path)
    pending = filter_pending(entries)
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_group_by_type(tmp_path):
    _make_md(tmp_path / "a.md", type="domain-fact")
    _make_md(tmp_path / "b.md", type="scoring-rule")
    _make_md(tmp_path / "c.md", type="domain-fact")
    entries = read_all(tmp_path)
    groups = group_by_type(entries)
    assert len(groups["domain-fact"]) == 2
    assert len(groups["scoring-rule"]) == 1


def test_count_pending_older_than(tmp_path):
    old_date = (date.today() - timedelta(days=10)).isoformat()
    recent_date = (date.today() - timedelta(days=2)).isoformat()
    _make_md(tmp_path / "old_pending.md", date=old_date, status="pending")
    _make_md(tmp_path / "recent_pending.md", date=recent_date, status="pending")
    _make_md(tmp_path / "old_consolidated.md", date=old_date, status="consolidated")
    entries = read_all(tmp_path)
    assert count_pending_older_than(entries, 7) == 1
    assert count_pending_older_than(entries, 1) == 2


def test_write_learning_filename_pattern(tmp_path):
    path = write_learning(
        trigger="user-feedback",
        context="research query",
        type_="query-strategy",
        body="Learned something.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    assert path.name.startswith("2026-05-07-001-")
    assert path.name.endswith(".md")
    assert path.exists()


def test_write_learning_frontmatter_fields_present(tmp_path):
    path = write_learning(
        trigger="session-close",
        context="search command topic",
        type_="source-classification",
        body="Relevant observation.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    post = frontmatter.load(str(path))
    for field in ("id", "date", "trigger", "context", "type", "status"):
        assert field in post.metadata, f"missing field: {field}"
    assert post.metadata["status"] == "pending"
    assert post.metadata["trigger"] == "session-close"


def test_next_id_increments_on_same_date(tmp_path):
    today = date.today().isoformat()
    write_learning(
        trigger="self-detection",
        context="ctx one",
        type_="domain-fact",
        body="First.",
        learnings_dir=tmp_path,
        today=today,
    )
    id1 = next_id(tmp_path)
    assert id1 == f"{today}-002"
    write_learning(
        trigger="self-detection",
        context="ctx two",
        type_="domain-fact",
        body="Second.",
        learnings_dir=tmp_path,
        today=today,
    )
    id2 = next_id(tmp_path)
    assert id2 == f"{today}-003"


def test_update_status_changes_field_preserves_others(tmp_path):
    path = write_learning(
        trigger="user-feedback",
        context="some context",
        type_="process-improvement",
        body="Body text.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    update_status(path, "consolidated")
    post = frontmatter.load(str(path))
    assert post.metadata["status"] == "consolidated"
    assert post.metadata["trigger"] == "user-feedback"
    assert post.metadata["context"] == "some context"
    assert post.metadata["type"] == "process-improvement"
