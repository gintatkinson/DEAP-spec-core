"""Regression tests for issue #282.

``reconcile_backlog.py`` carried the executable bit but no shebang, while
``spec-orchestrator/SKILL.md`` Phase 4 invokes it directly by path. On a
direct invocation ``execve`` returns ENOEXEC and the shell re-parses the
Python source as a shell script, so the mandatory Phase 4 validation gate
aborted with ``import: command not found`` instead of running.

These tests assert the invariant for every executable script in the
pipeline's scripts directory, not just the one that regressed.
"""

import os
import stat

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))


def _executable_scripts():
    """Every file in the scripts dir that has any executable bit set."""
    found = []
    for name in sorted(os.listdir(SCRIPT_DIR)):
        path = os.path.join(SCRIPT_DIR, name)
        if not os.path.isfile(path) or name.startswith("."):
            continue
        if os.stat(path).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            found.append(path)
    return found


def test_scripts_dir_has_executables_to_check():
    """Guard: the fixture must actually find scripts, or the suite proves nothing."""
    assert _executable_scripts(), f"no executable scripts discovered in {SCRIPT_DIR}"


def test_executable_scripts_start_with_shebang():
    """A file marked executable must declare an interpreter, or exec falls back to sh."""
    offenders = []
    for path in _executable_scripts():
        with open(path, "rb") as fh:
            if fh.read(2) != b"#!":
                offenders.append(os.path.basename(path))
    assert not offenders, (
        "executable scripts missing a '#!' shebang (direct invocation will be "
        f"reparsed by /bin/sh and fail with ENOEXEC): {offenders}"
    )


def test_executable_python_scripts_declare_a_python_interpreter():
    """A .py script's shebang must name python, not merely be present."""
    offenders = []
    for path in _executable_scripts():
        if not path.endswith(".py"):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
        if not first_line.startswith("#!") or "python" not in first_line:
            offenders.append((os.path.basename(path), first_line[:60]))
    assert not offenders, f"executable .py scripts without a python shebang: {offenders}"
