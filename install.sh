#!/usr/bin/env bash
set -euo pipefail

# install.sh — install research-skill into Claude Code
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/peanut-butter-co/claude-research-skill/main/install.sh | bash
#   curl -fsSL ... | bash -s -- --project   # project-level only
#   curl -fsSL ... | bash -s -- --force     # overwrite existing skills
#   bash install.sh                         # from a local clone

REPO_URL="https://github.com/peanut-butter-co/claude-research-skill"
RAW_URL="https://raw.githubusercontent.com/peanut-butter-co/claude-research-skill/main"
SKILLS=("research" "research-deep" "research-report" "research-consolidate")
LIB_DIR="_lib"

MODE="system"   # system | project
FORCE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --project) MODE="project" ;;
    --force)   FORCE=true ;;
    --help|-h)
      echo "Usage: bash install.sh [--project] [--force]"
      echo ""
      echo "  --project   Install into .claude/skills/ in the current directory"
      echo "              (default: ~/.claude/skills/ system-wide)"
      echo "  --force     Overwrite existing skills without prompting"
      exit 0
      ;;
    *) echo "Unknown option: $arg  (use --help)"; exit 1 ;;
  esac
done

# ── Resolve target directory ───────────────────────────────────────────────────
if [[ "$MODE" == "project" ]]; then
  TARGET_DIR="$(pwd)/.claude/skills"
else
  TARGET_DIR="${HOME}/.claude/skills"
fi

echo ""
echo "research-skill installer"
echo "  mode   : $MODE"
echo "  target : $TARGET_DIR"
echo ""

# ── Check for conflicts ────────────────────────────────────────────────────────
CONFLICTS=()
for skill in "${SKILLS[@]}"; do
  if [[ -e "$TARGET_DIR/$skill" ]]; then
    CONFLICTS+=("$skill")
  fi
done

if [[ ${#CONFLICTS[@]} -gt 0 ]] && [[ "$FORCE" == false ]]; then
  echo "⚠  The following skills already exist in $TARGET_DIR:"
  for c in "${CONFLICTS[@]}"; do
    echo "   • $c"
  done
  echo ""
  echo "Re-run with --force to overwrite, or remove them manually first."
  echo "Note: --force will NOT touch existing _lib/data/ files (your learned"
  echo "      source tiers and mode-detection rules are preserved)."
  exit 1
fi

# ── Resolve source: local clone or download ───────────────────────────────────
if [[ -n "$SCRIPT_DIR" && -d "$SCRIPT_DIR/.claude/skills" ]]; then
  SOURCE_DIR="$SCRIPT_DIR/.claude/skills"
  echo "Installing from local clone at $SCRIPT_DIR"
else
  echo "Downloading from $REPO_URL ..."
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  if command -v git &>/dev/null; then
    git clone --quiet --depth 1 "$REPO_URL.git" "$TMP_DIR/repo"
  else
    echo "git not found — please install git and retry."
    exit 1
  fi
  SOURCE_DIR="$TMP_DIR/repo/.claude/skills"
fi

# ── Install skills ─────────────────────────────────────────────────────────────
mkdir -p "$TARGET_DIR"

for skill in "${SKILLS[@]}"; do
  DEST="$TARGET_DIR/$skill"
  if [[ -e "$DEST" ]]; then
    echo "  overwriting $skill ..."
    rm -rf "$DEST"
  else
    echo "  installing $skill ..."
  fi
  cp -r "$SOURCE_DIR/$skill" "$DEST"
done

# ── Install _lib (merge carefully) ────────────────────────────────────────────
DEST_LIB="$TARGET_DIR/$LIB_DIR"
SOURCE_LIB="$SOURCE_DIR/$LIB_DIR"

if [[ ! -d "$DEST_LIB" ]]; then
  echo "  installing _lib ..."
  cp -r "$SOURCE_LIB" "$DEST_LIB"
else
  echo "  updating _lib/scripts/ (preserving _lib/data/) ..."
  # Always overwrite scripts (code updates)
  rm -rf "$DEST_LIB/scripts"
  cp -r "$SOURCE_LIB/scripts" "$DEST_LIB/scripts"
  # Merge data files: only add files that don't exist yet (never overwrite user-modified data)
  for src_file in "$SOURCE_LIB/data/"*; do
    fname="$(basename "$src_file")"
    dest_file="$DEST_LIB/data/$fname"
    if [[ ! -e "$dest_file" ]]; then
      echo "    + adding new data file: $fname"
      cp "$src_file" "$dest_file"
    else
      echo "    ~ skipping existing:    $fname (run --force-data to overwrite)"
    fi
  done
fi

# ── Install Python dependencies ────────────────────────────────────────────────
echo ""
echo "Installing Python dependencies ..."
if command -v pip3 &>/dev/null; then
  pip3 install --quiet requests PyYAML python-frontmatter python-slugify
elif command -v pip &>/dev/null; then
  pip install --quiet requests PyYAML python-frontmatter python-slugify
else
  echo "⚠  pip not found. Install manually:"
  echo "   pip install requests PyYAML python-frontmatter python-slugify"
fi

# ── Project-level: create learnings dir ───────────────────────────────────────
if [[ "$MODE" == "project" ]]; then
  if [[ ! -d "learnings" ]]; then
    mkdir learnings
    touch learnings/.gitkeep
    echo "  created learnings/ in current directory"
  fi
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "✓ research-skill installed."
echo ""
echo "Available slash commands:"
echo "  /research \"<topic>\"    — plan a research session"
echo "  /research-deep          — run parallel agents"
echo "  /research-report        — synthesize report"
echo "  /research-consolidate   — consolidate learnings"
echo ""
if [[ "$MODE" == "system" ]]; then
  echo "Installed system-wide. Available in all Claude Code projects."
else
  echo "Installed project-level. Only available in this directory."
fi
