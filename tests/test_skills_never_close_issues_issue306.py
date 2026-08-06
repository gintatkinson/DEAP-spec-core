"""Regression tests for issue #306.

``.pipeline/constitution.md:161`` makes ``Closed`` unreachable without Product Owner
validation. Two skills nonetheless instructed the agent to close issues, and
``.pipeline/upstream/pipeline-tooling.md`` declared an override rather than the skill
text being corrected. That override is insufficient on two counts: ``AGENTS.md:75``
mandates *literal* skill execution, and the override lives in an upstream-only profile
that a downstream project never receives.

The subtle part is the second assertion here. Removing the close step is not safe on
its own: ``debug-protocol`` selects work with ``gh issue list --label bug`` and
terminates only when no open ``bug`` issue passes its Step 0 defect gate. Both assume a
finished bug *leaves* the selection set, which previously happened by closing it. With
closing removed, a fixed bug stays open, still labelled ``bug``, still a genuine defect
— so the loop reselects it forever. That is the #287 deadlock in a new form, and the
#287 reclassification clause does not rescue it because it only removes *non*-defects.
The selection query must therefore exclude ``status:fixed-resolved``.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

# Phrasings that instruct or assert closing a tracker issue. Deliberately narrow:
# "closing fence", "closing procedures", "Loop closed" and the phase headings
# "Release & Closure" / "Agentic Epic Closure" are about something other than issue
# state and must not trip this gate.
CLOSE_PATTERNS = [
    re.compile(r"gh issue close", re.IGNORECASE),
    re.compile(
        r"\bclose\s+(?:the\s+|this\s+)?(?:feature\s+|epic\s+|github\s+|tracker\s+)?issue\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bclose\s+it\b", re.IGNORECASE),
    re.compile(r"\bclosed\s+issues?\b", re.IGNORECASE),
    re.compile(r"\bissue\s+closed\b", re.IGNORECASE),
    re.compile(r"\bautomatically\s+closes\b", re.IGNORECASE),
]

# Documented exemptions. An entry here is a visible gap with an owning issue, not a
# silent exclusion. Empty is the goal.
KNOWN_EXEMPT = {
    # Emptied by #309. spec-orchestrator/SKILL.md was exempt while it accurately
    # described reconcile_backlog.py's auto-close behaviour — correcting the prose
    # before the script would have replaced a true statement about broken behaviour
    # with a false one. #309 fixed both together, so the exemption is retired rather
    # than left standing as a permanent excuse.
}


def _skill_files():
    found = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if os.path.isfile(path):
            found.append(path)
    return found


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def test_every_skill_is_discovered():
    """Guard: a scan that finds nothing would pass both assertions below."""
    skills = _skill_files()
    assert len(skills) >= 10, f"expected every SKILL.md, found {len(skills)}"


def test_no_skill_instructs_closing_a_tracker_issue_issue306():
    offenders = []
    for path in _skill_files():
        rel = os.path.relpath(path, SKILLS_DIR)
        if rel in KNOWN_EXEMPT:
            continue
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            for pattern in CLOSE_PATTERNS:
                if pattern.search(line):
                    offenders.append(f"{rel}:{lineno} -> {line.strip()[:90]}")
                    break
    assert not offenders, (
        "skills instruct closing a tracker issue, which .pipeline/constitution.md:161 "
        "reserves for Product Owner validation. Stop at Fixed / Resolved and apply the "
        f"status:fixed-resolved label instead: {offenders}"
    )


def test_debug_protocol_selection_excludes_resolved_issues_issue306():
    """Without this, removing the close step makes the loop non-terminating."""
    path = os.path.join(SKILLS_DIR, "debug-protocol", "SKILL.md")
    selection_lines = [
        line
        for line in _read(path).splitlines()
        if "gh issue list" in line and "bug" in line
    ]
    assert selection_lines, "debug-protocol no longer states how it selects work"
    for line in selection_lines:
        assert "status:fixed-resolved" in line, (
            "debug-protocol's selection query does not exclude status:fixed-resolved, so "
            "a resolved-but-open bug is reselected forever once closing is removed "
            f"(#287 deadlock class): {line.strip()}"
        )
