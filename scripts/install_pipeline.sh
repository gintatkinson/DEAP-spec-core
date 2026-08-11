#!/usr/bin/env bash
set -e

# Turnkey automated installation script for digital-pipeline-repo

# Refuse to run inside digital-pipeline-repo itself
if [ -e ./.pipeline/upstream ]; then
  echo "Error: Cannot run installer inside digital-pipeline-repo itself."
  exit 1
fi

REPO_URL="https://github.com/gintatkinson/DEAP-spec-core.git"
TMP_DIR=".tmp-pipeline-install"

echo "==> Preparing digital pipeline installation..."

# Cleanup old temp directory if exists
rm -rf "$TMP_DIR"

echo "==> Cloning latest DEAP-spec-core..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

echo "==> Copying pipeline directories and configurations..."
FORK_DIRS=("skills/" "rules/" ".pipeline/" ".agents/" "scripts/")

for dir in "${FORK_DIRS[@]}"; do
  clean_dir="${dir%/}"
  if [ -d "$TMP_DIR/$clean_dir" ]; then
    mkdir -p "$clean_dir"
    (cd "$TMP_DIR/$clean_dir" && tar --exclude="./upstream" -cf - .) | (cd "$clean_dir" && tar xf -)
  fi
done

# Automatically generate clean, standardized AGENTS.md if not present
if [ ! -f AGENTS.md ]; then
  if [ -f "$TMP_DIR/.agents/AGENTS.md" ]; then
    cp "$TMP_DIR/.agents/AGENTS.md" AGENTS.md
  else
    echo "# Project-Scoped Rules" > AGENTS.md
  fi
fi

# Merge or create .gitignore
if [ ! -f .gitignore ]; then
  if [ -f "$TMP_DIR/.gitignore" ]; then
    cp "$TMP_DIR/.gitignore" .gitignore
  else
    touch .gitignore
  fi
fi

# Ensure .tmp-pipeline-install is in .gitignore if not present
if ! grep -q ".tmp-pipeline-install" .gitignore 2>/dev/null; then
  echo ".tmp-pipeline-install" >> .gitignore
fi

echo "==> Setting up git hooks and tracker labels..."
if [ -f scripts/setup_git_hooks.py ]; then
  python3 scripts/setup_git_hooks.py || true
fi

if [ -f skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py ]; then
  python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py || true
elif [ -f .agents/skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py ]; then
  python3 .agents/skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py || true
fi

echo "==> Cleaning up temporary installation files..."
rm -rf "$TMP_DIR"

echo ""
echo "=========================================================================="
echo " Digital Pipeline Installation Complete!"
echo " 0 manual steps remaining."
echo "=========================================================================="
