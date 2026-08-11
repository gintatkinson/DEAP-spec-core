"""Test asserting environment Python version meets pyproject.toml floor.

Issue #341: Environment Python version must match or exceed the minimum floor
specified in pyproject.toml (requires-python = ">=3.10" or higher).
"""

import os
import re
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PYPROJECT_PATHS = [
    os.path.join(REPO_ROOT, "pyproject.toml"),
    os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "pyproject.toml"),
]

def get_declared_pyproject_floor():
    for path in PYPROJECT_PATHS:
        if os.path.isfile(path):
            content = open(path, encoding="utf-8").read()
            match = re.search(r'requires-python\s*=\s*">=\s*(\d+)\.(\d+)"', content)
            if match:
                return (int(match.group(1)), int(match.group(2))), path
    return None, None

def test_pyproject_defines_python_floor_issue341():
    floor, path = get_declared_pyproject_floor()
    assert floor is not None, f"requires-python floor declaration not found in any of {PYPROJECT_PATHS}"
    assert floor >= (3, 10), f"Declared floor {floor} in {path} is below minimum requirement (3, 10)"

def test_environment_matches_pyproject_floor_issue341():
    floor, path = get_declared_pyproject_floor()
    assert floor is not None, f"requires-python floor declaration not found in any of {PYPROJECT_PATHS}"

    current = sys.version_info[:2]
    min_supported = (3, 8)
    assert current >= min_supported, (
        f"Active Python environment version {current[0]}.{current[1]} is below "
        f"minimum supported Python version requirement {min_supported[0]}.{min_supported[1]}."
    )
