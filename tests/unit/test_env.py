from pathlib import Path
import pytest
from scripts.env import load_env, ENV_PATH


def make_env_file(root: Path, content: str) -> Path:
    env_file = root / ENV_PATH
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(content)
    return env_file


def test_missing_file_returns_empty_dict(tmp_path):
    result = load_env(root=tmp_path)
    assert result == {}


def test_normal_key_value_pairs(tmp_path):
    make_env_file(tmp_path, "FOO=bar\nBAZ=qux\n")
    result = load_env(root=tmp_path)
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_comment_lines_skipped(tmp_path):
    make_env_file(tmp_path, "# this is a comment\nKEY=value\n")
    result = load_env(root=tmp_path)
    assert result == {"KEY": "value"}


def test_blank_lines_skipped(tmp_path):
    make_env_file(tmp_path, "\n\nKEY=value\n\n")
    result = load_env(root=tmp_path)
    assert result == {"KEY": "value"}


def test_double_quoted_values_stripped(tmp_path):
    make_env_file(tmp_path, 'KEY="hello world"\n')
    result = load_env(root=tmp_path)
    assert result == {"KEY": "hello world"}


def test_single_quoted_values_stripped(tmp_path):
    make_env_file(tmp_path, "KEY='hello world'\n")
    result = load_env(root=tmp_path)
    assert result == {"KEY": "hello world"}


def test_malformed_line_skipped(tmp_path):
    make_env_file(tmp_path, "NOEQUALS\nGOOD=value\n")
    result = load_env(root=tmp_path)
    assert result == {"GOOD": "value"}


def test_custom_root_path(tmp_path):
    custom_root = tmp_path / "custom"
    custom_root.mkdir()
    make_env_file(custom_root, "CUSTOM=yes\n")
    result = load_env(root=custom_root)
    assert result == {"CUSTOM": "yes"}
