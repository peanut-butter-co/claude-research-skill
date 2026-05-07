import re
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify


_DEFAULT_DIR = Path(__file__).parent.parent / "learnings"


def next_id(learnings_dir: Path) -> str:
    today = date.today().isoformat()
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}-.*\.md$")
    existing = [
        p for p in learnings_dir.glob(f"{today}-*.md")
        if pattern.match(p.name)
    ]
    seq = len(existing) + 1
    return f"{today}-{seq:03d}"


def write_learning(
    trigger: str,
    context: str,
    type_: str,
    body: str,
    learnings_dir: Path | None = None,
    today: str | None = None,
) -> Path:
    directory = learnings_dir or _DEFAULT_DIR
    directory.mkdir(parents=True, exist_ok=True)

    iso_today = today or date.today().isoformat()
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}-.*\.md$")
    existing = [
        p for p in directory.glob(f"{iso_today}-*.md")
        if pattern.match(p.name)
    ]
    seq = len(existing) + 1
    entry_id = f"{iso_today}-{seq:03d}"

    slug = slugify(context, max_length=40, separator="-")
    filename = f"{entry_id}-{slug}.md"

    metadata = {
        "id": entry_id,
        "date": iso_today,
        "trigger": trigger,
        "context": context,
        "type": type_,
        "status": "pending",
    }
    post = frontmatter.Post(body, **metadata)
    path = directory / filename
    path.write_text(frontmatter.dumps(post))
    return path


def update_status(entry_path: Path, new_status: str) -> None:
    post = frontmatter.load(str(entry_path))
    post.metadata["status"] = new_status
    entry_path.write_text(frontmatter.dumps(post))
