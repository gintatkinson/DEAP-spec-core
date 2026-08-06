"""Contract gate for issue #278 — item-level subagent context isolation.

The audit filed against ``skills/spec-orchestrator/SKILL.md:74`` under the heading
*Context Leakage / Generation Drift*. Line 74 is the isolation statement itself —
"Do **NOT** pass the history of other items generated in the same run" — and it is
intact, as is its co-normative twin in ``.agents/AGENTS.md`` § *Mandatory Subagent
Dispatch*. The issue body's actual claim is narrower and different from its title: the
drafting step imposes no structural output contract, so a worker may emit a Markdown
table where structured metadata belongs.

Two parts of that claim do not survive checking, and this file pins both down so the
literal remedy cannot be applied later:

* **The proposed blanket ban is wrong.** "The generation of Markdown tables is
  strictly prohibited" would outlaw the pipeline's own canonical output —
  ``skills/spec-orchestrator/scripts/reconcile_backlog.py`` calls
  ``convert_frontmatter_to_table`` on every Phase 4 sync and publishes a
  ``| Metadata | Value |`` table into every tracker issue body. Same shape as issue
  #279, where the reported rule would have rejected the canonical Feature template
  and only a narrower rule was correct.
* **The claimed crash does not exist.** Every frontmatter parse in the pipeline
  (``extract_metadata``, ``convert_frontmatter_to_table``,
  ``UmlValidator._validate_subagent_isolation``) wraps ``yaml.safe_load`` in
  ``try``/``except`` and degrades; a table in the document body is never handed to
  PyYAML at all.

What is genuinely wrong is the third thing the audit gestures at. The isolation
mandate has exactly one machine-readable trace — the ``generation_mode: "subagent"``
frontmatter key, enforced for Epics, Features, User Stories and Use Cases by
``parity_auditor``'s UML validator. That key is stated in the four worker templates
and in none of the documents that state the mandate, and the pairing was registered
neither in ``tests/rule_contracts.py`` nor in its ``KNOWN_UNREGISTERED_FAMILIES``
list. By that registry's own premise (#298) the pairing was invisible: deleting the
mandate, or deleting the check, failed nothing.

Message prefixes are load-bearing. ``rule_contracts.SUBAGENT_ISOLATION_FAMILY`` scans
this file for ``isolation-gate:`` messages to detect orphan enforcement, so every one
of them must be paired with a document in the registry. Messages prefixed
``isolation-guard:`` are self-checks on this file's own fixtures and scanners — not
rules about the corpus — and are deliberately outside that scan.
"""

import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ORCHESTRATOR = os.path.join(REPO_ROOT, "skills", "spec-orchestrator", "SKILL.md")
AGENTS = os.path.join(REPO_ROOT, ".agents", "AGENTS.md")
UML_VALIDATOR = os.path.join(
    REPO_ROOT,
    "skills", "spec-orchestrator", "parity_auditor", "src", "parity_auditor",
    "validators", "uml.py",
)
RECONCILER = os.path.join(
    REPO_ROOT, "skills", "spec-orchestrator", "scripts", "reconcile_backlog.py"
)

# The templates a drafting subagent is handed, one per specification item type.
# schema-specification-engineering carries both the Epic and the Feature template.
SPEC_TEMPLATES = (
    os.path.join(REPO_ROOT, "skills", "schema-specification-engineering", "SKILL.md"),
    os.path.join(REPO_ROOT, "skills", "spec-user-story-engineering", "SKILL.md"),
    os.path.join(REPO_ROOT, "skills", "spec-usecase-engineering", "SKILL.md"),
)

# The isolation section of the orchestrator skill, where the drafting step lives.
_ISOLATION_SECTION = re.compile(
    r"^## Item-Level Subagent Context Isolation\n(.*?)(?=^## )",
    re.MULTILINE | re.DOTALL,
)

# A blanket prohibition of Markdown tables, in the wording issue #278 proposed. Used as
# a negative control below: the corpus is clean, so a broken pattern and a compliant
# corpus are indistinguishable without it.
_BLANKET_TABLE_BAN = re.compile(
    r"(?:generation of )?markdown tables?(?: [a-z]+){0,3} (?:is|are) "
    r"(?:strictly )?(?:prohibited|forbidden|banned)",
    re.IGNORECASE,
)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_contract_sources_are_discoverable_issue278():
    """Fixture guard: every assertion below reads these files."""
    missing = [
        os.path.relpath(p, REPO_ROOT)
        for p in (ORCHESTRATOR, AGENTS, UML_VALIDATOR, RECONCILER) + SPEC_TEMPLATES
        if not os.path.isfile(p)
    ]
    assert not missing, (
        "isolation-guard: a source of the isolation contract is missing"
        f" — {missing}. The assertions below would pass vacuously."
    )
    assert len(SPEC_TEMPLATES) >= 3, (
        "isolation-guard: the specification template corpus is empty"
        " — nothing would be checked for the marker."
    )


# --------------------------------------------------------------------------- #
# The mandate itself. Stated co-normatively; deleting either statement must fail.
# --------------------------------------------------------------------------- #

def test_governance_documents_state_the_isolation_mandate_issue278():
    missing = []
    if "Item-Level Subagent Context Isolation" not in _read(ORCHESTRATOR):
        missing.append("skills/spec-orchestrator/SKILL.md")
    if "Fresh, isolated context" not in _read(AGENTS):
        missing.append(".agents/AGENTS.md")
    assert not missing, (
        "isolation-gate: a governance document omits the item level isolation mandate"
        f" — {missing}. Every specification item must be drafted by a fresh subagent "
        "with no inherited session state."
    )


def test_governance_documents_forbid_passing_session_history_issue278():
    """The line #278 anchors on. It is present, and must stay present."""
    missing = []
    if "Do **NOT** pass the history of other items generated in the same run." not in _read(
        ORCHESTRATOR
    ):
        missing.append("skills/spec-orchestrator/SKILL.md")
    if "Do not copy the entire conversation history" not in _read(AGENTS):
        missing.append(".agents/AGENTS.md")
    assert not missing, (
        "isolation-gate: a governance document omits the no session history constraint"
        f" — {missing}. A curated prompt is the whole of the isolation guarantee; "
        "passing the transcript reintroduces the drift the mandate exists to prevent."
    )


# --------------------------------------------------------------------------- #
# The marker: the only machine-readable evidence that the mandate was honoured.
# --------------------------------------------------------------------------- #

def test_drafting_step_names_the_frontmatter_marker_issue278():
    """The gap #278 actually found.

    The section states the mandate but never told the drafting subagent what to emit,
    while ``parity_auditor`` rejects any item lacking ``generation_mode: subagent``.
    Enforced but undocumented at the point of generation — the shape of issue #299,
    where a generating subagent could not comply with a rule it was never shown.
    """
    match = _ISOLATION_SECTION.search(_read(ORCHESTRATOR))
    assert match, (
        "isolation-guard: the orchestrator isolation section could not be located"
        " — the heading was renamed, so this gate stopped examining its subject."
    )
    section = match.group(1)
    assert "generation_mode" in section and "_validate_subagent_isolation" in section, (
        "isolation-gate: the drafting step omits the subagent generation mode marker"
        " — the section must name the generation_mode frontmatter key and the check "
        "that enforces it, or a drafting subagent cannot comply with a gate it is "
        "never shown."
    )


def test_every_spec_template_emits_the_marker_issue278():
    missing = []
    for path in SPEC_TEMPLATES:
        if 'generation_mode: "subagent"' not in _read(path):
            missing.append(os.path.relpath(path, REPO_ROOT))
    assert not missing, (
        "isolation-gate: a specification template omits the generation mode marker"
        f" — {missing}. The template is what the drafting subagent copies; drop the "
        "key there and every generated item fails the UML validator."
    )


def test_parity_auditor_enforces_the_marker_issue278():
    source = _read(UML_VALIDATOR)
    validated = set(
        re.findall(r'_validate_subagent_isolation\(\s*content,\s*"([^"]+)"', source)
    )
    expected = {"Epic", "Feature", "User Story", "Use Case"}
    assert "violates the Item-Level Subagent Context Isolation mandate" in source, (
        "isolation-gate: the parity auditor no longer enforces the isolation marker"
        " — the mandate would become documentation with nothing behind it."
    )
    assert expected <= validated, (
        "isolation-gate: the parity auditor no longer enforces the isolation marker"
        f" — checked only {sorted(validated)}; all of {sorted(expected)} must be."
    )


# --------------------------------------------------------------------------- #
# The remedy #278 proposed, rejected. See the module docstring.
# --------------------------------------------------------------------------- #

def test_no_governance_document_bans_markdown_tables_outright_issue278():
    # Negative control: prove the pattern still recognises the wording #278 proposed,
    # so a clean corpus is distinguishable from a dead regex.
    assert _BLANKET_TABLE_BAN.search(
        "The generation of Markdown tables is strictly prohibited."
    ), (
        "isolation-guard: the blanket table ban pattern no longer matches its subject"
    )

    assert "| Metadata | Value |" in _read(RECONCILER), (
        "isolation-guard: the reconciler no longer renders frontmatter as a table"
        " — this test's premise, that the pipeline itself emits Markdown tables, "
        "must be re-checked before the guard below is trusted."
    )

    offenders = []
    for path in (ORCHESTRATOR, AGENTS) + SPEC_TEMPLATES:
        rel = os.path.relpath(path, REPO_ROOT)
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if _BLANKET_TABLE_BAN.search(line):
                offenders.append(f"{rel}:{lineno}")
    assert not offenders, (
        "isolation-gate: a governance document prohibits markdown tables outright"
        f" — {offenders}. reconcile_backlog.py publishes a '| Metadata | Value |' "
        "table into every tracker issue body, so a blanket ban would outlaw the "
        "pipeline's own canonical output. Constrain the frontmatter block instead."
    )


# --------------------------------------------------------------------------- #
# Registration, so the pairing above is visible to the #298 registry.
# --------------------------------------------------------------------------- #

def test_isolation_family_is_registered_issue278():
    tests_dir = os.path.join(REPO_ROOT, "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from rule_contracts import FAMILIES, KNOWN_UNREGISTERED_FAMILIES

    names = {f.name for f in FAMILIES}
    assert (
        "subagent-isolation" in names
        or "subagent-isolation" in KNOWN_UNREGISTERED_FAMILIES
    ), (
        "isolation-guard: the subagent isolation family is registered nowhere"
        f" — FAMILIES holds {sorted(names)}. A rule paired with neither an entry in "
        "the registry nor an entry in KNOWN_UNREGISTERED_FAMILIES is invisible to "
        "the #298 orphan checks in both directions."
    )
