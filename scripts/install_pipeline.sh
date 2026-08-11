#!/usr/bin/env bash
set -e

# Turnkey automated installation script for digital-pipeline-repo

# Refuse to run inside digital-pipeline-repo itself
if [ -e ./.pipeline/upstream ]; then
  echo "Error: Cannot run installer inside digital-pipeline-repo itself."
  exit 1
fi

DEFAULT_UPSTREAM_REPO="https://github.com/gintatkinson/DEAP-spec-core.git"
REPO_URL="${DEAP_UPSTREAM_REPO:-$DEFAULT_UPSTREAM_REPO}"
PROFILE=""
WITH_UI=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      if [ -n "$2" ] && [[ "$2" != --* ]]; then
        REPO_URL="$2"
        shift 2
      else
        echo "Error: Option --repo requires a non-empty URL argument."
        exit 1
      fi
      ;;
    --profile)
      if [ -n "$2" ] && [[ "$2" != --* ]]; then
        PROFILE="$2"
        shift 2
      else
        echo "Error: Option --profile requires a profile name argument."
        exit 1
      fi
      ;;
    --with-ui)
      WITH_UI=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--repo <url>] [--profile <name>] [--with-ui]"
      echo "Profiles: ros2_cpp, px4_module, spark_ada, embedded_c, flutter, react"
      exit 0
      ;;
    *)
      echo "Error: Unknown option: $1"
      exit 1
      ;;
  esac
done

# Defensive Pre-Execution Validation: git CLI availability
if ! command -v git &> /dev/null; then
  echo "Error: git CLI is not installed or not found in PATH."
  exit 1
fi

# Defensive Pre-Execution Validation: remote repository reachability
echo "==> Validating remote repository reachability ($REPO_URL)..."
if ! git ls-remote --exit-code "$REPO_URL" HEAD &> /dev/null; then
  echo "Error: Remote repository '$REPO_URL' is unreachable or invalid."
  exit 1
fi

TMP_DIR=".tmp-pipeline-install"

echo "==> Preparing digital pipeline installation..."

# Cleanup old temp directory if exists
rm -rf "$TMP_DIR"

echo "==> Cloning latest pipeline from $REPO_URL..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

echo "==> Copying pipeline directories and configurations..."
FORK_DIRS=("skills/" "rules/" ".pipeline/" ".agents/" "scripts/")

if [ "$WITH_UI" = true ] || [ "$PROFILE" = "flutter" ] || [ "$PROFILE" = "react" ] || [ "$PROFILE" = "flutter_mobile" ] || [ "$PROFILE" = "react_web" ]; then
  FORK_DIRS+=("app_flutter/" "web_react/")
fi

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

echo "==> Initializing clean downstream docs directory structure..."
DOCS_SUBDIRS=("epics" "features" "use-cases" "user-stories" "architecture" "decisions" "reports" "requirements")
for subdir in "${DOCS_SUBDIRS[@]}"; do
  mkdir -p "docs/$subdir"
  touch "docs/$subdir/.gitkeep"
done

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
