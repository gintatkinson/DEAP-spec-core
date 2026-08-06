"""Regression tests for issue #295 — authorization precedence.

Three documents governed the same decision and gave three incompatible answers
about what authorizes a file write:

  rules/user-authorization-lock.md:9  keyword PROCEED in the latest message suffices
  .pipeline/constitution.md:120       keyword in the current turn sequence suffices
  .agents/AGENTS.md:7                 a keyword is explicitly NOT sufficient

The decisive defect was in the reading order rather than in any single rule:
``rules/constitution-first.md`` enumerated the mandatory reads without listing
``.agents/AGENTS.md``, and ``.agents/`` is a hidden directory that glob and
ripgrep index queries skip. An agent complying fully with constitution-first
therefore read only the two keyword-sufficient documents.

These tests pin the unified resolution: an approved plan AND explicit approval,
with every document required to establish that rule present in the reads list.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONSTITUTION_FIRST = os.path.join(REPO_ROOT, "rules", "constitution-first.md")
AUTH_LOCK = os.path.join(REPO_ROOT, "rules", "user-authorization-lock.md")
AGENTS = os.path.join(REPO_ROOT, ".agents", "AGENTS.md")

GOVERNANCE_DOCS = {
    "constitution-first": CONSTITUTION_FIRST,
    "user-authorization-lock": AUTH_LOCK,
    "AGENTS": AGENTS,
}


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Guard: all three documents must exist, or the suite proves nothing.
# --------------------------------------------------------------------------- #

def test_all_governance_documents_are_discoverable():
    missing = [name for name, path in GOVERNANCE_DOCS.items() if not os.path.isfile(path)]
    assert not missing, f"governance documents not found: {missing}"


# --------------------------------------------------------------------------- #
# The root cause: AGENTS.md must be a mandatory read.
# --------------------------------------------------------------------------- #

def test_constitution_first_lists_agents_md_as_a_required_read():
    """Without this, an agent following constitution-first never sees the strictest rule."""
    content = _read(CONSTITUTION_FIRST)
    assert ".agents/AGENTS.md" in content, (
        "rules/constitution-first.md must list .agents/AGENTS.md among the required "
        "reads. It is a hidden-directory file that glob and ripgrep skip, so omitting "
        "it from the reads list makes the strictest authorization rule unreachable."
    )


def test_constitution_first_warns_that_agents_dir_is_hidden():
    content = _read(CONSTITUTION_FIRST)
    hidden_sentences = [
        s for s in re.split(r"(?<=[.!])\s+", content) if re.search(r"hidden", s, re.I)
    ]
    assert hidden_sentences, "constitution-first.md contains no hidden-directory warning"
    assert any(".agents" in s for s in hidden_sentences), (
        "the hidden-directory warning in constitution-first.md must cover .agents/, "
        f"not only .pipeline/. Sentences mentioning 'hidden': {hidden_sentences}"
    )


# --------------------------------------------------------------------------- #
# The contradiction: a keyword alone must no longer be stated as sufficient.
# --------------------------------------------------------------------------- #

def test_auth_lock_requires_an_approved_plan_not_only_a_keyword():
    content = _read(AUTH_LOCK)
    assert re.search(r"implementation plan", content, re.I), (
        "rules/user-authorization-lock.md must require an approved implementation "
        "plan in addition to the keyword. Stating the keyword alone as sufficient "
        "contradicts .agents/AGENTS.md:7 and caused unapproved writes to main."
    )


def test_auth_lock_declares_precedence():
    content = _read(AUTH_LOCK)
    assert re.search(r"strictest", content, re.I), (
        "rules/user-authorization-lock.md must state that where the governance "
        "documents appear to differ, the strictest reading applies"
    )


# --------------------------------------------------------------------------- #
# Cross-references: each document must point at the others.
# --------------------------------------------------------------------------- #

def test_auth_lock_cross_references_agents_md():
    assert ".agents/AGENTS.md" in _read(AUTH_LOCK), (
        "user-authorization-lock.md must cross-reference .agents/AGENTS.md"
    )


def test_agents_md_cross_references_the_rule_files():
    content = _read(AGENTS)
    assert "rules/user-authorization-lock.md" in content, (
        ".agents/AGENTS.md must cross-reference rules/user-authorization-lock.md so an "
        "agent entering from either direction finds the same unified rule"
    )
