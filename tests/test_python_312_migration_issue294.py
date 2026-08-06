"""Regression tests for the Python 3.12 migration — issue #294.

Python 3.9 reached end-of-life in October 2025. The declared floor stays at 3.9
because the development machine's bare ``python3`` is still 3.9.6 and every
documented command and the ``pip install -e`` step run under it — see
``.pipeline/upstream/pipeline-tooling.md`` § *Platform & Stack*. Retaining the
floor is therefore a deliberate staging decision, not an oversight.

What that staging costs is forward compatibility: code that runs today on 3.9 can
still be relying on APIs that 3.12+ has deprecated and will remove. The suites
cannot catch that, because they run on 3.9 where the API is still present and
silent. This file is the static gate that catches it instead.

Every replacement named below is available on 3.9, so adopting it does **not**
raise the floor.
"""

import io
import os
import re
import tokenize

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Roots holding this repository's own Python. Third-party trees are excluded:
# a vendored dependency's use of a deprecated API is not ours to fix here.
SOURCE_ROOTS = (
    "scripts",
    "skills",
    "tests",
    os.path.join(".pipeline", "scripts"),
)

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".eggs",
}

# This file names the forbidden APIs in order to forbid them, so scanning it
# would report itself.
SELF = os.path.abspath(__file__)

# (compiled pattern, what it is, what to use instead).
#
# Each entry is removed, or deprecated and scheduled for removal, at or after
# 3.12. The replacement column is deliberately restricted to spellings that also
# work on 3.9 — `datetime.UTC`, for instance, is 3.11+ and so is NOT the
# replacement offered for `utcnow()`; `timezone.utc` is.
FORBIDDEN_APIS = (
    (
        re.compile(r"\butcnow\s*\("),
        "datetime.utcnow() — deprecated in 3.12, scheduled for removal",
        "datetime.now(timezone.utc) (add `timezone` to the datetime import)",
    ),
    (
        re.compile(r"\butcfromtimestamp\s*\("),
        "datetime.utcfromtimestamp() — deprecated in 3.12, scheduled for removal",
        "datetime.fromtimestamp(ts, timezone.utc)",
    ),
    (
        re.compile(r"^\s*(?:import\s+imp|from\s+imp\s+import)\b", re.MULTILINE),
        "the `imp` module — removed in 3.12",
        "importlib / importlib.util",
    ),
    (
        re.compile(r"^\s*(?:import|from)\s+distutils\b", re.MULTILINE),
        "distutils — removed in 3.12 (PEP 632)",
        "setuptools, shutil or packaging",
    ),
    (
        re.compile(r"\bunittest\.makeSuite\s*\("),
        "unittest.makeSuite() — removed in 3.13",
        "unittest.TestLoader().loadTestsFromTestCase(...)",
    ),
)


def _discover_python_files():
    found = []
    for root in SOURCE_ROOTS:
        base = os.path.join(REPO_ROOT, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.abspath(path) == SELF:
                    continue
                found.append(path)
    return sorted(found)


PYTHON_FILES = _discover_python_files()


# --------------------------------------------------------------------------- #
# Fixture guard: a scan that discovers nothing passes vacuously and proves less
# than no test at all.
# --------------------------------------------------------------------------- #

def test_the_source_scan_discovers_the_repository_issue294():
    assert len(PYTHON_FILES) >= 60, (
        f"the deprecated-API scan discovered only {len(PYTHON_FILES)} Python files "
        f"under {list(SOURCE_ROOTS)}; the repository holds well over 60, so the "
        "walk is broken and every scan below would pass vacuously."
    )
    relative = {os.path.relpath(p, REPO_ROOT) for p in PYTHON_FILES}
    for expected in (
        os.path.join(
            "skills", "spec-orchestrator", "parity_auditor",
            "src", "parity_auditor", "utils", "diagnostics.py",
        ),
        os.path.join("tests", "test_ci_workflow_config.py"),
    ):
        assert expected in relative, (
            f"{expected} was not discovered by the scan, so the roots are wrong"
        )


# --------------------------------------------------------------------------- #
# #294 - no API that 3.12+ has removed or scheduled for removal
# --------------------------------------------------------------------------- #

def _code_only(source):
    """Blank comments and string literals, preserving offsets and line numbers.

    A call is never inside a comment or a string, but the *name* of a deprecated
    API frequently is — the migration note explaining why a call was replaced
    quotes the thing it replaced. Scanning raw text therefore fires on precisely
    the documentation this gate wants people to write, and the only way to
    silence it is to delete the explanation.

    Same shape as ``ALLOWED_AGENTS_PREFIX`` in test_skill_path_references.py,
    where the rule's own normative statement had to quote the form it prohibits
    (#310). There the fix was one exemption; here it generalises, because any
    file may carry such a note.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source  # unparseable: fall back to raw text rather than skipping

    lines = source.splitlines(keepends=True)
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        (srow, scol), (erow, ecol) = tok.start, tok.end
        for row in range(srow, erow + 1):
            line = lines[row - 1]
            begin = scol if row == srow else 0
            end = ecol if row == erow else len(line.rstrip("\n"))
            lines[row - 1] = (
                line[:begin] + " " * (end - begin) + line[end:]
            )
    return "".join(lines)


def test_no_apis_removed_after_python_39_issue294():
    offenders = []
    for path in PYTHON_FILES:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = _code_only(fh.read())
        except (OSError, UnicodeDecodeError):  # pragma: no cover - unreadable file
            continue
        for pattern, what, replacement in FORBIDDEN_APIS:
            for match in pattern.finditer(content):
                line_no = content.count("\n", 0, match.start()) + 1
                offenders.append(
                    f"{os.path.relpath(path, REPO_ROOT)}:{line_no} uses {what}. "
                    f"Use {replacement} instead."
                )

    assert not offenders, (
        "Python APIs that 3.12+ removes are still in use. The suites run on 3.9, "
        "where these are still present and silent, so only this static gate sees "
        "them — and each one becomes a hard failure the moment the interpreter "
        "moves. Every replacement below also works on 3.9, so none of them raise "
        "the declared floor (issue #294):\n  - " + "\n  - ".join(offenders)
    )


# --------------------------------------------------------------------------- #
# #294 - the retained 3.9 floor must be justified where the floor is declared,
#        not left looking like an accident.
# --------------------------------------------------------------------------- #

TOOLING_PROFILE = os.path.join(
    REPO_ROOT, ".pipeline", "upstream", "pipeline-tooling.md"
)
PYPROJECT = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "parity_auditor", "pyproject.toml"
)


def test_floor_is_not_end_of_life_issue294():
    """The floor must name a supported interpreter, and say where it came from.

    Originally this asserted the *retained* 3.9 floor was justified in place. The
    floor has since moved to 3.12 (#294), so the assertion inverts: what needs
    guarding now is that it never silently slips back onto an end-of-life version.
    """
    if not os.path.isfile(PYPROJECT):  # pragma: no cover - guarded by other tests
        pytest.skip("pyproject.toml absent")
    content = open(PYPROJECT, encoding="utf-8").read()
    match = re.search(r'requires-python\s*=\s*">=\s*(\d+)\.(\d+)"', content)
    assert match, "requires-python is not declared as a >= floor in pyproject.toml"
    floor = (int(match.group(1)), int(match.group(2)))
    assert floor >= (3, 12), (
        f"the declared Python floor is {floor[0]}.{floor[1]}, which is end-of-life. "
        "3.9 lost security patches in October 2025 and the migration to 3.12 landed "
        "in #294. Do not move the floor back."
    )
    assert "294" in content, (
        "pyproject.toml declares a Python floor without citing the issue that "
        "assessed it (#294). An unexplained floor invites someone to change it "
        "without knowing what was verified."
    )
