"""Regression tests for CI workflow configuration defects.

Covers:
  #290 - push trigger filtered on ``master`` while the default branch is ``main``,
         so pushes to the default branch triggered no run at all.
  #291 - the only test step ran ``pytest tests/test_repro_cases.py``, so 30 of 31
         test files and all 116 parity_auditor tests never executed in CI, yet the
         check reported green.
  #292 - ``requires-python`` (>=3.8), the CI pin (3.10) and the sole installed
         interpreter (3.9.6) all disagreed, so the declared floor was never
         exercised and post-3.9 syntax could pass CI while breaking local runs.
  #294 - the floor (3.9) is end-of-life and is retained deliberately, because the
         development machine's bare ``python3`` is still 3.9.6. A retained EOL
         floor is only safe while CI *also* exercises a supported interpreter,
         while the ruff target version tracks the floor rather than drifting from
         it, and while the profile's stated matrix matches the real one.
"""

import os
import re
import subprocess

import pytest
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "auto_regression_testing.yml")
PYPROJECT = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "pyproject.toml"
)

PARITY_TESTS = "skills/spec-orchestrator/parity_auditor/tests"


def _load_workflow():
    with open(WORKFLOW, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _triggers(wf):
    """PyYAML resolves the bare key ``on`` to boolean True under YAML 1.1."""
    if "on" in wf:
        return wf["on"]
    return wf[True]


def _push_branches(wf):
    push = _triggers(wf).get("push") or {}
    return list(push.get("branches") or [])


def _run_blocks(wf):
    blocks = []
    for job in wf.get("jobs", {}).values():
        for step in job.get("steps", []) or []:
            if isinstance(step, dict) and step.get("run"):
                blocks.append(step["run"])
    return blocks


def _ci_python_versions(wf):
    """Every python version the workflow could run, from matrix or a literal pin."""
    versions = set()
    for job in wf.get("jobs", {}).values():
        matrix = (job.get("strategy") or {}).get("matrix") or {}
        for key, value in matrix.items():
            if "python" in key.lower() and isinstance(value, list):
                versions.update(str(v) for v in value)
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            pinned = (step.get("with") or {}).get("python-version")
            if pinned and "matrix" not in str(pinned):
                versions.add(str(pinned))
    return versions


def _declared_python_floor():
    with open(PYPROJECT, "r", encoding="utf-8") as fh:
        match = re.search(r'requires-python\s*=\s*"[><=~!]*\s*([0-9]+\.[0-9]+)', fh.read())
    assert match, "could not parse requires-python from pyproject.toml"
    return match.group(1)


# --------------------------------------------------------------------------- #
# Guard: the fixtures must find real content, or these tests prove nothing.
# --------------------------------------------------------------------------- #

def test_workflow_and_pyproject_are_discoverable():
    assert os.path.isfile(WORKFLOW), f"workflow not found at {WORKFLOW}"
    assert os.path.isfile(PYPROJECT), f"pyproject not found at {PYPROJECT}"
    assert _run_blocks(_load_workflow()), "no run steps parsed from the workflow"


# --------------------------------------------------------------------------- #
# #290 - push trigger must reference a branch that exists
# --------------------------------------------------------------------------- #

def test_push_trigger_does_not_reference_master_issue290():
    branches = _push_branches(_load_workflow())
    assert "master" not in branches, (
        f"push trigger references a non-existent 'master' branch: {branches}. "
        "The default branch is 'main', so this filter matches nothing and CI "
        "silently never runs on push."
    )


def test_push_trigger_targets_the_default_branch_issue290():
    try:
        ref = subprocess.check_output(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        default_branch = ref.rsplit("/", 1)[-1]
    except (subprocess.CalledProcessError, OSError):
        pytest.skip("origin/HEAD not resolvable in this environment")

    branches = _push_branches(_load_workflow())
    assert default_branch in branches, (
        f"default branch '{default_branch}' is absent from the push filter {branches}, "
        "so merges to it receive no regression validation."
    )


# --------------------------------------------------------------------------- #
# #291 - CI must run the repository's test suites, not one file
# --------------------------------------------------------------------------- #

def test_ci_runs_the_root_test_suite_issue291():
    joined = "\n".join(_run_blocks(_load_workflow()))
    assert re.search(r"pytest\s+tests/(\s|$|-)", joined), (
        "no CI step runs the root suite as a directory ('pytest tests/'). "
        "Running a single file means a green check does not mean the tests passed."
    )


def test_ci_runs_the_parity_auditor_suite_issue291():
    joined = "\n".join(_run_blocks(_load_workflow()))
    assert PARITY_TESTS in joined, (
        f"no CI step runs the parity_auditor suite ({PARITY_TESTS}); "
        "116 tests never execute in CI despite the package being pip-installed."
    )


# --------------------------------------------------------------------------- #
# #292 - declared floor, CI pin and tested runtime must be reconciled
# --------------------------------------------------------------------------- #

def test_ci_exercises_the_declared_python_floor_issue292():
    floor = _declared_python_floor()
    ci_versions = _ci_python_versions(_load_workflow())
    assert floor in ci_versions, (
        f"pyproject declares a floor of Python {floor} but CI runs {sorted(ci_versions)}. "
        "The declared minimum is never exercised, so it is an unverified claim."
    )


# --------------------------------------------------------------------------- #
# #294 - the floor is end-of-life and retained on purpose; the guards that make
#        that safe must stay in place
# --------------------------------------------------------------------------- #

# 3.12 is the migration target named in issue #294. Anything at or above it is a
# currently-supported interpreter.
SUPPORTED_PYTHON = (3, 12)


def _as_version(text):
    match = re.match(r"^(\d+)\.(\d+)", str(text).strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


def test_ci_exercises_a_supported_python_above_the_floor_issue294():
    """The floor is EOL. A green check on the floor alone proves only that the
    code works on an interpreter that no longer receives security patches, and
    says nothing about whether it still runs on a supported one — which is the
    whole question issue #294 exists to answer."""
    floor = _as_version(_declared_python_floor())
    versions = {v: _as_version(v) for v in _ci_python_versions(_load_workflow())}
    supported = sorted(
        raw for raw, parsed in versions.items()
        if parsed and parsed >= SUPPORTED_PYTHON and parsed > floor
    )
    assert supported, (
        f"CI runs {sorted(versions)}, none of which is both above the declared "
        f"floor {'.'.join(str(p) for p in floor)} and still supported "
        f"(>= {'.'.join(str(p) for p in SUPPORTED_PYTHON)}). The floor is "
        "end-of-life, so a matrix that only exercises it makes the migration in "
        "issue #294 unverifiable and would let a 3.12-incompatible change land green."
    )


def _ruff_target_versions(wf):
    """Every ruff ``--target-version`` in the workflow, plus the pyproject default."""
    targets = set(re.findall(r"--target-version\s+(py\d+)", "\n".join(_run_blocks(wf))))
    with open(PYPROJECT, "r", encoding="utf-8") as fh:
        targets.update(re.findall(r'target-version\s*=\s*"(py\d+)"', fh.read()))
    return targets


def test_ruff_target_version_tracks_the_declared_floor_issue294():
    """``--target-version`` is what makes ruff reject syntax the floor cannot
    parse. Declared in three places — the workflow flag, the pyproject default and
    the profile's documented command — it drifts silently from ``requires-python``
    unless something ties them together."""
    floor = _declared_python_floor()
    expected = "py" + floor.replace(".", "")
    targets = _ruff_target_versions(_load_workflow())
    assert targets, "no ruff --target-version found in the workflow or pyproject"
    assert targets == {expected}, (
        f"pyproject declares requires-python >= {floor}, so ruff must target "
        f"{expected!r}, but the configured targets are {sorted(targets)}. A target "
        "above the floor lets syntax the floor cannot parse pass lint; a target "
        "below it rejects code the floor accepts."
    )


def _profile_ci_matrix():
    """The matrix the tooling profile claims CI runs, from its Platform & Stack bullet."""
    with open(TOOLING_PROFILE, "r", encoding="utf-8") as fh:
        match = re.search(r"\*\*CI matrix:\*\*\s*`\[([^\]]*)\]`", fh.read())
    assert match, "the tooling profile no longer states a CI matrix"
    return {v.strip().strip("'\"") for v in match.group(1).split(",") if v.strip()}


def test_tooling_profile_states_the_real_ci_matrix_issue294():
    """The profile's Platform & Stack section is the document an agent reads before
    touching the runtime. Its previous claim about the machine went stale without
    anything noticing, which is how #294 came to be assessed on false premises."""
    if not os.path.isfile(TOOLING_PROFILE):
        pytest.skip("upstream tooling profile absent")
    stated = _profile_ci_matrix()
    actual = _ci_python_versions(_load_workflow())
    assert stated == actual, (
        f"the tooling profile states the CI matrix is {sorted(stated)} but the "
        f"workflow runs {sorted(actual)}. The profile is the documented source of "
        "truth for the runtime; drift there sends the next agent to the wrong "
        "conclusion about what is actually verified."
    )


# --------------------------------------------------------------------------- #
# #302 - bytecode cache must not be written during tests
# --------------------------------------------------------------------------- #

TOOLING_PROFILE = os.path.join(
    REPO_ROOT, ".pipeline", "upstream", "pipeline-tooling.md"
)


def _job_env(wf):
    env = dict(wf.get("env") or {})
    for job in wf.get("jobs", {}).values():
        env.update(job.get("env") or {})
    return {k: str(v) for k, v in env.items()}


def test_ci_disables_bytecode_writing_issue302():
    """macOS system Python caches .pyc outside the repo, in
    ~/Library/Caches/com.apple.python/. Combined with mtime+size invalidation, a probe
    that edits a file without changing its length can report a false result - which
    undermines every negative control the gates rely on."""
    env = _job_env(_load_workflow())
    assert env.get("PYTHONDONTWRITEBYTECODE") == "1", (
        "CI must set PYTHONDONTWRITEBYTECODE=1 so stale bytecode cannot make a test "
        f"pass or fail against source no longer on disk. Job env: {env}"
    )


def test_tooling_profile_documents_the_bytecode_rule_issue302():
    if not os.path.isfile(TOOLING_PROFILE):
        pytest.skip("upstream tooling profile absent")
    content = open(TOOLING_PROFILE, encoding="utf-8").read()
    assert "PYTHONDONTWRITEBYTECODE" in content, (
        "the tooling profile must document the bytecode rule under Testing Mandates, "
        "or the reason for it is lost and someone will remove it from CI"
    )
