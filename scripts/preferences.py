from datetime import datetime, timezone
from pathlib import Path

import yaml


_DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / ".config" / "research-skill"
_PREFS_FILE = "preferences.yaml"
_EMPTY: dict = {"never_suggest": []}


def _config_path(config_dir: Path | None) -> Path:
    return (config_dir or _DEFAULT_CONFIG_DIR) / _PREFS_FILE


def load_preferences(config_dir: Path | None = None) -> dict:
    path = _config_path(config_dir)
    if not path.exists():
        return {"never_suggest": []}
    with path.open() as f:
        data = yaml.safe_load(f)
    if not data:
        return {"never_suggest": []}
    data.setdefault("never_suggest", [])
    return data


def save_preferences(prefs: dict, config_dir: Path | None = None) -> None:
    path = _config_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(prefs, f, default_flow_style=False, allow_unicode=True)


def add_never_suggest(
    signature: list[str],
    integration_id: str,
    config_dir: Path | None = None,
) -> None:
    prefs = load_preferences(config_dir)
    prefs["never_suggest"].append(
        {
            "signature": sorted(signature),
            "integration_id": integration_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_preferences(prefs, config_dir)


def is_never_suggest(
    signature: list[str],
    config_dir: Path | None = None,
) -> bool:
    prefs = load_preferences(config_dir)
    target = sorted(signature)
    return any(
        sorted(entry.get("signature", [])) == target
        for entry in prefs.get("never_suggest", [])
    )
