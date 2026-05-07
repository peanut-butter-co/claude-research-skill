from pathlib import Path

ENV_PATH = ".config/research-skill/.env"

_REPO_ROOT = Path(__file__).parent.parent


def load_env(root: Path | None = None) -> dict[str, str]:
    root = root if root is not None else _REPO_ROOT
    env_file = root / ENV_PATH

    if not env_file.exists():
        return {}

    result: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            result[key] = value

    return result
