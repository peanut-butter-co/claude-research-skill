import re
from pathlib import Path

import yaml


def detect_mode_fast(topic: str, data_dir: Path | None = None) -> dict:
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"

    config_path = data_dir / "mode-detection.yaml"
    with config_path.open() as f:
        config = yaml.safe_load(f)

    patterns = config["keywords"]["comparative"]
    for pattern in patterns:
        m = re.search(pattern, topic)
        if m:
            return {"mode": "comparative", "confidence": 1.0, "matched_pattern": pattern}

    return {"mode": None, "confidence": 0.0, "matched_pattern": None}
