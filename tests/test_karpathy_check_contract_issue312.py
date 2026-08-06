"""Regression tests for issue #312 — the 4-point Karpathy compliance check.

Two defects, one gate.

**Defect 1 — the remedy was unexecutable.** Point 4 of the check asks whether
context-isolated subagent dispatch is mandated and locks coordinator file-writing
when it is. The dispatch machinery in ``.agents/AGENTS.md`` specified that remedy in
terms of ``invoke_subagent`` (``TypeName: self``) and ``manage_subagents``
(``kill`` / ``kill_all``). Neither tool exists in the Claude Code runtime, which
exposes a general-purpose agent-dispatch tool with a different interface and
automatic lifecycle. ``AGENTS.md`` § *Strict Context Isolation & Skill Fidelity*
mandates literal adherence, so an agent that correctly answered "yes" to point 4
could not then comply. The sections are now written as capabilities, with concrete
tools deferred to a per-runtime table, so the rule survives a change of runtime.

**Defect 2 — the scope of point 4 was ambiguous and the check was unenforced.**
"Does the active skill mandate context-isolated subagent dispatches" can be read as
binding only during named skill phases. That reading was taken during a real
session: governance repair was judged not to be skill execution and the coordinator
wrote every file directly for hours. ``rules/user-authorization-lock.md``
§ *Precedence* requires the strictest reading where statements differ, so both
documents now state the broad scope in one literal sentence, asserted below.

The check itself is a reasoning obligation — nothing here can prove an agent
performed it in a given turn. What these tests do guarantee is that neither
statement of the rule, nor its scope sentence, can be deleted while the suite stays
green. The residual gap is recorded in
``rule_contracts.KNOWN_UNREGISTERED_FAMILIES`` rather than left silent.
"""

import os

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

AUTH_LOCK = "rules/user-authorization-lock.md"
AGENTS = ".agents/AGENTS.md"

# Both documents state the check. Neither is a summary of the other; they are
# co-normative, so every assertion below runs against both.
STATING_DOCUMENTS = (AUTH_LOCK, AGENTS)

CHECK_TITLE = "4-point Karpathy and Pipeline Compliance Check"

# The four points, keyed by a fragment stable enough to survive rewording of the
# surrounding sentence but specific enough that deleting a point fails.
FOUR_POINTS = {
    "1-question-or-command": "question/inquiry or a direct command",
    "2-explicit-approval": "explicitly approved a file-write",
    "3-silent-assumptions": "silent assumptions about the user's intent",
    "4-subagent-dispatch": "context-isolated subagent dispatches",
}

# The sentence that closes the scope ambiguity. Asserted verbatim, in both
# documents, because a paraphrase is exactly what allowed the narrow reading.
SCOPE_SENTENCE = (
    "The delegation duty binds for all repository source and specification "
    "writes, not only during named skill phases."
)

# Tool names that do not exist in the Claude Code runtime. Naming them in the
# normative sentence is what made the remedy unexecutable.
NONEXISTENT_DISPATCH_TOOLS = ("invoke_subagent", "manage_subagents")


def _read(rel_path):
    with open(os.path.join(REPO_ROOT, rel_path), "r", encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def documents():
    """The corpus every assertion runs against.

    Returned as a mapping so a test that scans nothing is impossible: the guard
    below asserts the mapping is populated and that each document is substantial.
    """
    return {rel: _read(rel) for rel in STATING_DOCUMENTS}


# --------------------------------------------------------------------------- #
# Fixture guard. A document scan that reads an empty or missing file passes every
# "not in" assertion below for free, so the corpus is checked first.
# --------------------------------------------------------------------------- #

def test_scanned_corpus_is_not_empty(documents):
    assert len(documents) == 2, (
        "fixture guard: both co-normative statements of the check must be scanned, "
        f"got {sorted(documents)}"
    )
    thin = sorted(rel for rel, text in documents.items() if len(text) < 1000)
    assert not thin, (
        "fixture guard: a scanned governance document is empty or truncated, so the "
        f"assertions below would be vacuous: {thin}"
    )


# --------------------------------------------------------------------------- #
# The check must remain stated, in full, in both documents.
# --------------------------------------------------------------------------- #

def test_both_documents_state_the_four_point_check(documents):
    missing = sorted(rel for rel, text in documents.items() if CHECK_TITLE not in text)
    assert not missing, (
        "karpathy-gate: a governance document omits the four-point compliance check: "
        f"{missing}. The check is co-normative in {AUTH_LOCK} and {AGENTS}; deleting "
        "either statement is what this gate exists to catch."
    )


def test_both_documents_list_all_four_points(documents):
    missing = sorted(
        f"{rel} -> {key}"
        for rel, text in documents.items()
        for key, fragment in FOUR_POINTS.items()
        if fragment not in text
    )
    assert not missing, (
        "karpathy-gate: a governance document omits one of the four numbered points: "
        f"{missing}. All four must be present in both documents."
    )


# --------------------------------------------------------------------------- #
# Point 4's scope, stated so it cannot be read narrowly again.
# --------------------------------------------------------------------------- #

def test_both_documents_state_the_delegation_scope(documents):
    missing = sorted(
        rel for rel, text in documents.items() if SCOPE_SENTENCE not in " ".join(text.split())
    )
    assert not missing, (
        "karpathy-gate: a governance document omits the delegation scope statement: "
        f"{missing}. Expected verbatim: {SCOPE_SENTENCE!r}. Without it point 4 reads "
        "as binding only during named skill phases, which is the reading taken during "
        "the session recorded in issue #312."
    )


# --------------------------------------------------------------------------- #
# The remedy must be expressed as a capability, not as tools that do not exist.
# --------------------------------------------------------------------------- #

def test_agents_md_names_no_nonexistent_dispatch_tool(documents):
    text = documents[AGENTS]
    found = sorted(tool for tool in NONEXISTENT_DISPATCH_TOOLS if tool in text)
    assert not found, (
        "karpathy-gate: agents md names a dispatch tool absent from the runtime: "
        f"{found}. Describe the capability instead, and defer concrete tool names to "
        "the per-runtime table, so literal skill execution stays possible."
    )


def test_agents_md_still_mandates_dispatch_and_termination(documents):
    """The rewrite is for executability. Nothing mandatory may become optional."""
    text = documents[AGENTS]
    obligations = {
        "dispatch-is-mandatory": "Mandatory Subagent Dispatch",
        "termination-is-mandatory": "Mandatory Subagent Termination & Cleanup",
        "context-isolated-capability": "context-isolated subagent",
        "no-session-history": "conversation history",
        "skill-read-first": "SKILL.md",
        "runtime-table": "Dispatch capability by runtime",
    }
    missing = sorted(key for key, anchor in obligations.items() if anchor not in text)
    assert not missing, (
        f"the rewrite dropped an obligation from {AGENTS}: {missing}. Issue #312 "
        "authorised rewording for executability only."
    )
