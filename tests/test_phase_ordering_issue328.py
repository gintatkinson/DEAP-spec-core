"""Regression test for issue #328 — Phase 2/3 async race in the orchestrator.

`spec-orchestrator/SKILL.md` marked Phase 3 `[P]` (parallel-capable) and justified it:

    "If both are dispatched simultaneously, Worker C will find the User Story issues
     as soon as Worker B creates them."

That is false. `gh issue list` is a one-shot query — it neither blocks nor polls — so
Worker C can read the tracker before Worker B has finished writing to it. The result is
a Use Case whose Realization Matrix silently omits User Stories that did not exist at
query time: a time-of-check-to-time-of-use race with no synchronisation barrier.

The barrier already exists in the skill's own rule — *"Phases NOT marked `[P]` are
strictly sequential — the validation gate of phase N must pass before phase N+1
begins."* Marking Phase 3 `[P]` removed it. The fix is to stop claiming a dependency
is absent when it is not.

This is a documentation defect with a runtime consequence, so it is tested at the
document: nothing in the corpus can detect a race that only manifests when two workers
are dispatched against a live tracker.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILL = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "SKILL.md")


def _skill():
    with open(SKILL, "r", encoding="utf-8") as fh:
        return fh.read()


def test_the_skill_under_test_exists_issue328():
    """Guard: every assertion below reads this file."""
    assert os.path.isfile(SKILL), f"{SKILL} missing; the suite would prove nothing"
    assert len(_skill()) > 2000, "SKILL.md is implausibly short; the scan is vacuous"


def test_phase_three_is_not_marked_parallel_issue328():
    """Phase 3 consumes Phase 2's tracker output, so it cannot run beside it."""
    heading = re.search(r"^## Phase 3.*$", _skill(), re.MULTILINE)
    assert heading, "Phase 3 heading not found"
    assert "[P]" not in heading.group(0), (
        f"Phase 3 is still marked parallel-capable: {heading.group(0)!r}. It queries "
        "the tracker for User Story issues that Phase 2 creates, so dispatching them "
        "together races (#328)."
    )


def test_the_false_concurrency_claim_is_gone_issue328():
    """The justification was the defect, not just the marker."""
    text = _skill()
    assert "will find the User Story issues as soon as Worker B creates them" not in text, (
        "the skill still asserts that a simultaneous dispatch is safe. gh issue list "
        "is one-shot: it does not block and does not poll, so there is nothing to make "
        "that true."
    )


def test_the_dependency_is_stated_so_it_is_not_re_marked_issue328():
    """A bare removal invites someone to add `[P]` back as an optimisation."""
    text = _skill()
    assert "#328" in text, (
        "the skill does not record why Phase 3 is sequential, so the marker can be "
        "reinstated by anyone who reads parallelism as free speed"
    )
    assert re.search(r"one-shot|does not (block|poll)", text), (
        "the skill does not state the mechanism (a one-shot query with no barrier), "
        "which is the part that makes the ordering non-negotiable"
    )


def test_phase_two_remains_parallel_capable_issue328():
    """Positive control: the fix must not serialise phases that are independent."""
    heading = re.search(r"^## Phase 2.*$", _skill(), re.MULTILINE)
    assert heading, "Phase 2 heading not found"
    assert "[P]" in heading.group(0), (
        "Phase 2 lost its parallel marker. Its dependency is Phase 1, whose Feature "
        "issues already exist when it runs, so serialising it is a cost with no "
        "correctness gain."
    )


def test_the_sequential_rule_it_relies_on_still_exists_issue328():
    """The barrier is the skill's own rule; the fix is inert without it."""
    assert re.search(
        r"Phases NOT marked .?\[P\].? are strictly sequential", _skill()
    ), (
        "the rule that unmarked phases are strictly sequential is gone, so removing "
        "[P] from Phase 3 no longer imposes any ordering"
    )
