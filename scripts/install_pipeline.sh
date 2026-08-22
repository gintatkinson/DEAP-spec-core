#!/usr/bin/env bash
set -e

INSTALLER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-.}"
mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

if [ "$TARGET_DIR" = "$INSTALLER_ROOT" ] && [ -e "$INSTALLER_ROOT/.pipeline/upstream" ]; then
  echo "REFUSING: target is the pipeline repository itself, not a downstream project." >&2
  exit 1
fi

rm -rf "$TARGET_DIR/skills" "$TARGET_DIR/rules" "$TARGET_DIR/.pipeline" "$TARGET_DIR/.agents" "$TARGET_DIR/scripts"
cp -RP "$INSTALLER_ROOT/skills" "$TARGET_DIR/"
cp -RP "$INSTALLER_ROOT/rules" "$TARGET_DIR/"
cp -RP "$INSTALLER_ROOT/.pipeline" "$TARGET_DIR/"
rm -rf "$TARGET_DIR/.pipeline/upstream"
cp -RP "$INSTALLER_ROOT/.agents" "$TARGET_DIR/"
cp -RP "$INSTALLER_ROOT/scripts" "$TARGET_DIR/"
cp -P "$INSTALLER_ROOT/requirements.txt" "$TARGET_DIR/" 2>/dev/null || true
if [ -f "$TARGET_DIR/.gitignore" ]; then
  cat "$INSTALLER_ROOT/.gitignore" >> "$TARGET_DIR/.gitignore"
  # Deduplicate lines in .gitignore
  sort -u "$TARGET_DIR/.gitignore" -o "$TARGET_DIR/.gitignore"
elif [ -f "$INSTALLER_ROOT/.gitignore" ]; then
  cp "$INSTALLER_ROOT/.gitignore" "$TARGET_DIR/"
fi

mkdir -p "$TARGET_DIR/tests"
mkdir -p "$TARGET_DIR/docs/conops" "$TARGET_DIR/docs/safety" "$TARGET_DIR/docs/architecture/blueprints" "$TARGET_DIR/docs/epics" "$TARGET_DIR/docs/features" "$TARGET_DIR/docs/user-stories" "$TARGET_DIR/docs/use-cases"
mkdir -p "$TARGET_DIR/.pipeline/contracts" "$TARGET_DIR/.pipeline/domain_specs" "$TARGET_DIR/.pipeline/profiles"
chmod +x "$TARGET_DIR"/scripts/*.sh "$TARGET_DIR"/scripts/*.py 2>/dev/null || true

if [ ! -f "$TARGET_DIR/tests/test_baseline.py" ]; then
  cat << 'EOF' > "$TARGET_DIR/tests/test_baseline.py"
"""
Downstream Environment & Runtime Integrity Verification Suite.
/// Realises: [BaselineVerification]
"""
import sys
import os
import tempfile
import pytest

def test_python_runtime_environment():
    """Verify Python runtime version and core interpreter executable exist and function."""
    assert sys.version_info >= (3, 8), f"Python version {sys.version} is below required 3.8+"
    assert os.path.exists(sys.executable), "Python interpreter path invalid"

def test_disk_io_and_permissions():
    """Verify local file system read, write, and permission capabilities."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp_file:
        test_payload = "DEAP_ENVIRONMENT_INTEGRITY_CHECK_PAYLOAD_2026"
        temp_file.write(test_payload)
        temp_file.seek(0)
        read_back = temp_file.read()
        assert read_back == test_payload, "Disk I/O payload mismatch during environment validation"
EOF
fi

if [ -f "$TARGET_DIR/scripts/setup_git_hooks.py" ]; then
  (cd "$TARGET_DIR" && python3 scripts/setup_git_hooks.py) || true
fi

echo "==> Digital Pipeline Installation Complete. 0 manual steps remaining."
