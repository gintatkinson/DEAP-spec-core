#!/usr/bin/env bash
set -e

if [ -e ./.pipeline/upstream ]; then
  echo "REFUSING: this is the pipeline repository, not a downstream project." >&2
  exit 1
fi

git clone https://github.com/gintatkinson/DEAP-spec-core.git ./.tmp-pipeline
rm -rf ./skills ./rules ./.pipeline ./.agents ./scripts
cp -RP ./.tmp-pipeline/skills ./
cp -RP ./.tmp-pipeline/rules ./
cp -RP ./.tmp-pipeline/.pipeline ./
rm -rf ./.pipeline/upstream
cp -RP ./.tmp-pipeline/.agents ./
cp -RP ./.tmp-pipeline/scripts ./
if [ -f ./.gitignore ]; then
  cat ./.tmp-pipeline/.gitignore >> ./.gitignore
else
  cp ./.tmp-pipeline/.gitignore ./
fi
rm -rf ./.tmp-pipeline
python3 scripts/setup_git_hooks.py || true
python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py || true

mkdir -p ./tests
mkdir -p ./docs/conops ./docs/safety ./docs/architecture/blueprints ./docs/epics ./docs/features ./docs/user-stories ./docs/use-cases
if [ ! -f ./tests/test_baseline.py ]; then
  cat << 'EOF' > ./tests/test_baseline.py
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

echo "==> Digital Pipeline Installation Complete. 0 manual steps remaining."
