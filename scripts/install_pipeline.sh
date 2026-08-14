#!/usr/bin/env bash
set -e

# Turnkey automated installation script for digital-pipeline-repo

# Directory context recovery: verify getcwd / PWD validity
if ! pwd -P &>/dev/null || [ ! -d "$PWD" ]; then
  echo "==> Warning: getcwd or PWD context lost. Recovering directory context..."
  REAL_PWD=$(git rev-parse --show-toplevel 2>/dev/null || pwd -P 2>/dev/null || echo "$PWD")
  if [ -n "$REAL_PWD" ] && [ -d "$REAL_PWD" ]; then
    cd "$REAL_PWD"
  fi
fi

# Refuse to run inside DEAP-spec-core template root itself
if [ "${ALLOW_UPSTREAM_INSTALL:-0}" != "1" ]; then
  REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || git remote get-url origin 2>/dev/null || echo "")
  CANONICAL_SLUG=$(echo "$REMOTE_URL" | sed -E 's#(git@|https://)([^/:]+)[:/]([^/]+)/([^/.]+)(\.git)?#\3/\4#')
  REPO_NAME=$(echo "$REMOTE_URL" | sed -E 's/\.git$//; s#^.*[/:]##')
  DIR_NAME=$(basename "$PWD")

  if [[ "$CANONICAL_SLUG" == *"DEAP-spec-core"* || "$REPO_NAME" == "DEAP-spec-core" ]] || \
     [[ -z "$REMOTE_URL" && "$DIR_NAME" == "DEAP-spec-core" ]]; then
    echo "Error: Cannot run installer inside DEAP-spec-core template root itself."
    exit 1
  fi
fi

# Graceful recovery for nested sub-directories of parent repository
PARENT_GIT_DIR=$(git -C .. rev-parse --show-toplevel 2>/dev/null || echo "")
CURRENT_GIT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$PARENT_GIT_DIR" ] && [ "$PARENT_GIT_DIR" != "$CURRENT_GIT_DIR" ]; then
  PARENT_REMOTE=$(git -C "$PARENT_GIT_DIR" config --get remote.origin.url 2>/dev/null || echo "")
  CURRENT_REMOTE=$(git config --get remote.origin.url 2>/dev/null || echo "")
  PARENT_NAME=$(basename "$PARENT_GIT_DIR")
  CURRENT_NAME=$(basename "$CURRENT_GIT_DIR")

  if [ "$PARENT_REMOTE" = "$CURRENT_REMOTE" ] || [ "$PARENT_NAME" = "$CURRENT_NAME" ]; then
    echo "==> Detected nested execution inside '$CURRENT_GIT_DIR'. Recovering context to parent repository '$PARENT_GIT_DIR'..."
    cd "$PARENT_GIT_DIR"
    CURRENT_GIT_DIR="$PARENT_GIT_DIR"
  else
    echo "Error: Cannot run installer inside a nested sub-directory of parent repository '$PARENT_GIT_DIR'."
    echo "Please move or clone this repository to an un-nested workspace directory."
    exit 1
  fi
fi

DEFAULT_UPSTREAM_REPO="https://github.com/gintatkinson/DEAP-spec-core.git"
REPO_URL="${DEAP_UPSTREAM_REPO:-$DEFAULT_UPSTREAM_REPO}"
PROFILE=""
WITH_UI=false
TARGET_DIR="."

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
      echo "Usage: $0 [--repo <url>] [--profile <name>] [--with-ui] [.]"
      echo "Profiles: ros2_cpp, px4_module, spark_ada, embedded_c, flutter, react"
      exit 0
      ;;
    .)
      TARGET_DIR="."
      shift
      ;;
    *)
      if [ "$1" != "." ]; then
        echo "Error: Positional target parameter must be '.' to prevent nested directory creation (got '$1')."
        exit 1
      fi
      TARGET_DIR="."
      shift
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

TMP_DIR="${TARGET_DIR}/.tmp-pipeline-install"

echo "==> Preparing digital pipeline installation..."

# Cleanup old temp directory if exists
rm -rf "$TMP_DIR"

echo "==> Cloning latest pipeline from $REPO_URL into target directory..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

# Zero-nesting assertion by construction: assert no nested repository subfolder wrapper created
REPO_SLUG_NAME=$(basename "$REPO_URL" .git)
if [ -d "$TARGET_DIR/$REPO_SLUG_NAME" ] && [ "$REPO_SLUG_NAME" != "." ]; then
  echo "Error: Zero-nesting invariant violated. Found nested repository wrapper '$TARGET_DIR/$REPO_SLUG_NAME'."
  exit 1
fi

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
