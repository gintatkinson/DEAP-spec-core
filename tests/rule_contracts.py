"""Registry pairing each enforced rule with the document that states it.

Seven defects found in a single audit session were one class: the documented
contract and the enforced contract disagreed (#283, #286, #289, #292, #295, #281,
#299). Every one was found by a human noticing, or by accident. Nothing tested that
documentation matches enforcement — that absence, rather than any individual
mismatch, is the root cause. See issue #298.

A contract has two anchors. Both must resolve, and the pairing must be registered.
Two failure modes then become mechanically detectable:

* **Orphan documentation** — a rule stated as MUST or prohibited that nothing
  enforces. This is #289.
* **Orphan enforcement** — a rule the code rejects that no document mentions. This
  is #299, where ``parsers/mermaid.py`` rejected unquoted relationship labels while
  ``rules/platform-independence.md`` never mentioned quoting.

**Scope.** This registry currently covers the Mermaid syntax family, where three of
the seven instances live. It is deliberately not a universal solution. Other families
— cardinality, authorization precedence, Python version reconciliation — are listed
in ``KNOWN_UNREGISTERED_FAMILIES`` so their absence is explicit rather than implied.
"""

from dataclasses import dataclass
from typing import List, Optional

PARITY_SRC = "skills/spec-orchestrator/parity_auditor/src/parity_auditor"


@dataclass(frozen=True)
class RuleContract:
    """One rule, its documentation anchor, and its enforcement anchor.

    ``doc_anchor`` and ``enforcement_anchor`` are literal substrings expected to be
    present in the respective files. Substrings rather than regexes, so a failure
    message can quote exactly what was missing.
    """

    id: str
    documented_in: str
    doc_anchor: str
    enforced_in: str
    enforcement_anchor: str
    note: str = ""


MERMAID_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="mermaid-no-semicolon-in-note-or-message",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Semicolon Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="semicolon in Mermaid Note or message text",
        note="The fault that shipped a non-rendering diagram on issue #283.",
    ),
    RuleContract(
        id="mermaid-diagram-unquoted-brackets-forbidden",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Unquoted Bracket Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="mermaid-diagram-unquoted-brackets-forbidden",
        note=(
            "Enforced since #288 but stated only in .agents/AGENTS.md, never in this "
            "file's normative home for Mermaid rules — the #289 fragmentation shape."
        ),
    ),
    RuleContract(
        id="mermaid-node-label-must-be-quoted",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Node Label Quoting Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="unquoted special characters in node label",
        note="Same provenance as the rule above.",
    ),
    RuleContract(
        id="mermaid-subgraph-title-must-be-quoted",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Subgraph Title Quoting Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="unquoted subgraph title containing spaces or hyphens",
    ),
    RuleContract(
        id="mermaid-quotes-must-be-balanced",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Quote Balance Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="unclosed double quotes in line",
    ),
    RuleContract(
        id="mermaid-no-curly-brace-in-class-member",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Class Member Brace Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="curly brace inside a Mermaid class member",
        note="13 confirmed non-rendering diagrams in downstream output (#296).",
    ),
    RuleContract(
        id="mermaid-no-colon-in-class-member",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Class Diagram Syntax Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="colon inside a Mermaid class member line",
    ),
    RuleContract(
        id="mermaid-no-colon-in-note-string",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Note Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="colon inside a Mermaid note string",
    ),
    RuleContract(
        id="mermaid-no-stereotype-on-relationship",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Relationship Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="stereotype on a Mermaid relationship line",
    ),
    RuleContract(
        id="mermaid-fence-must-be-closed",
        documented_in="rules/platform-independence.md",
        doc_anchor="strictly and explicitly closed",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="unclosed ```mermaid fence",
    ),
    RuleContract(
        id="mermaid-no-single-line-empty-class-body",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Empty Class Body Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="single-line empty Mermaid class body",
        note=(
            "Issue #279. The reported rule -- forbid empty Mermaid classes outright -- "
            "would reject the canonical Feature template, whose ancestor container node "
            "is deliberately attribute-less. Only the single-line spelling is a defect: "
            "parsers/mermaid.py closes a class block only on a line that is exactly "
            "'}', so 'class X {}' leaves the block open and a later namespace-closing "
            "brace pops it, silently reassigning every following class."
        ),
    ),
    RuleContract(
        id="mermaid-no-colon-in-relationship-label",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Relationship Label Colon Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="colon inside a Mermaid relationship label",
        note=(
            "Issue #333. Distinct from mermaid-relationship-label-must-be-quoted: "
            "quoting fixes spaces and does not fix colons, because Mermaid parses ':' "
            "as a statement separator wherever it occurs. The documented rule grouped "
            "the two, so a quoted colon satisfied the gate and GitHub then refused to "
            "render the diagram - a wrong rule is invisible to a gate that enforces "
            "documented rules rather than the grammar."
        ),
    ),
    RuleContract(
        id="mermaid-relationship-label-must-be-quoted",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Relationship Label Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="unquoted Mermaid relationship label",
        note=(
            "Issue #299. Enforced by parsers/mermaid.py:447 but documented nowhere, so "
            "a generating subagent could not comply. 6 symptoms observed in downstream "
            "feat-10 and feat-11 output."
        ),
    ),
    RuleContract(
        id="mermaid-reserved-keyword-as-participant-alias",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Sequence Diagram Participant Alias Rules",
        enforced_in=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
        enforcement_anchor="mermaid-reserved-keyword-as-participant-alias",
        note=(
            "Issue #358. Disallows Mermaid reserved keywords ('link', 'actor', 'participant', 'loop', 'opt', 'alt', 'rect', 'note', 'end', etc.) "
            "from being used as participant aliases in sequence diagrams."
        ),
    ),
]

FILENAME_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="spec-filename-ordinal-uniqueness",
        documented_in="skills/spec-usecase-engineering/SKILL.md",
        doc_anchor="zero-padded, dash-separated",
        enforced_in=f"{PARITY_SRC}/validators/spec_filename_validator.py",
        enforcement_anchor="duplicate ordinal",
        note="Issue #300. feat-04 and feat-05 each appear twice in downstream output.",
    ),
    RuleContract(
        id="spec-filename-format",
        documented_in="skills/spec-user-story-engineering/SKILL.md",
        doc_anchor="zero-padded, dash-separated",
        enforced_in=f"{PARITY_SRC}/validators/spec_filename_validator.py",
        enforcement_anchor="does not match the documented convention",
    ),
    RuleContract(
        id="spec-filename-padding-consistency",
        documented_in="skills/spec-usecase-engineering/SKILL.md",
        doc_anchor="zero-padded",
        enforced_in=f"{PARITY_SRC}/validators/spec_filename_validator.py",
        enforcement_anchor="inconsistent ordinal padding width",
        note="feat-002 uses 3-digit padding where the directory otherwise uses 2.",
    ),
    RuleContract(
        id="spec-filename-directory-prefix",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="docs/features/feat-01-name.md",
        enforced_in=f"{PARITY_SRC}/validators/spec_filename_validator.py",
        enforcement_anchor="directory prefix mismatch",
    ),
]


@dataclass(frozen=True)
class ContractFamily:
    """A group of contracts plus the scanners that find orphans in either direction.

    ``doc_heading_pattern`` is optional. A family whose rule is scattered across several
    documents has no single file to scan for orphan documentation, so the field is None
    and ``doc_orphan_blocked_by`` must explain why. Orphan **enforcement** detection
    still works for such a family, because that scans one validator.

    ``enforcement_files`` is the symmetric relaxation, added for issue #304. The first
    five families each had exactly one enforcing file, so ``enforcement_file`` was
    sufficient. It stops being sufficient as soon as a rule family spans validators —
    the schema-traceability rules are enforced by ``cardinality_validator`` and
    ``spec_validator`` together, and neither alone parses enough messages to clear the
    vacuity floor. When set, it lists every file to scan; ``enforcement_file`` remains
    the primary one, so existing families are unaffected and error messages still name
    a single obvious place to look.
    """

    name: str
    contracts: List[RuleContract]
    enforcement_file: str
    enforcement_pattern: str
    doc_file: Optional[str] = None
    doc_heading_pattern: Optional[str] = None
    doc_only: Optional[dict] = None
    doc_orphan_blocked_by: str = ""
    enforcement_files: Optional[List[str]] = None

    def enforcement_paths(self) -> List[str]:
        """Every file the orphan-enforcement scanner reads for this family."""
        return list(self.enforcement_files or [self.enforcement_file])


MERMAID_FAMILY = ContractFamily(
    name="mermaid-syntax",
    contracts=MERMAID_CONTRACTS,
    doc_only=None,  # set below, once DOC_ONLY_MERMAID_RULES is defined
    doc_file="rules/platform-independence.md",
    doc_heading_pattern=r"\*\*(Mermaid[^*]*?)\*\*:",
    enforcement_file=f"{PARITY_SRC}/validators/mermaid_syntax_validator.py",
    enforcement_pattern=r'f"\{source\}:\{lineno\}: ([a-z][^"{]*?)(?:\s*"|\()',
)

FILENAME_FAMILY = ContractFamily(
    name="spec-filename",
    contracts=FILENAME_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/spec_filename_validator.py",
    enforcement_pattern=r'f"\{rel\}(?:/\{name\})?: ([a-z][a-z ]*[a-z])',
    doc_file="rules/platform-independence.md",
    doc_heading_pattern=r"\*\*((?!Mermaid)[A-Z][^*]*?)\*\*:",
    doc_only={
        "Obsolete Token Namespace Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Hardcoded Standard Reference Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Backlog Standard And Platform Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Markdown Construct Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Code Fence Closure Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Diagram Fence Parity Rules": "Documented in rules/platform-independence.md for document-integrity",
    },
)

DOC_REFERENCE_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="doc-ref-repository-relative-skill-paths",
        documented_in="rules/document-references.md",
        doc_anchor="Repository-Relative Skill Paths",
        enforced_in="tests/test_skill_path_references.py",
        enforcement_anchor="documents reference paths through the '.agents/skills/' symlink",
        note="Enforced since #285, documented only at #310 — orphan enforcement for 3 issues.",
    ),
    RuleContract(
        id="doc-ref-cited-paths-resolve",
        documented_in="rules/document-references.md",
        doc_anchor="Cited Paths Must Resolve",
        enforced_in="tests/test_skill_path_references.py",
        enforcement_anchor="governance documents reference paths that do not exist",
    ),
    RuleContract(
        id="markdown-broken-link-reference",
        documented_in="rules/document-references.md",
        doc_anchor="Markdown Links Must Resolve",
        enforced_in=f"{PARITY_SRC}/validators/link_validator.py",
        enforcement_anchor="markdown-broken-link-reference",
        note=(
            "The specification-corpus counterpart of cited-paths-resolve: that rule "
            "governs paths in governance prose, this one governs markdown links inside "
            "backlog specifications, and a different checker enforces it."
        ),
    ),
    RuleContract(
        id="doc-ref-cited-steps-resolve",
        documented_in="rules/document-references.md",
        doc_anchor="Cited Steps Must Resolve",
        enforced_in="tests/test_skill_path_references.py",
        enforcement_anchor="governance documents cite steps that do not exist",
        note="The phantom 'Step 5.5' override citation, issue #307.",
    ),
    RuleContract(
        id="doc-ref-no-runtime-tool-names-in-directives",
        documented_in="rules/document-references.md",
        doc_anchor="Runtime Tool Names Belong In The Dispatch Table",
        enforced_in="tests/test_skill_path_references.py",
        enforcement_anchor="governance documents name concrete dispatch tools",
        note=(
            "Issue #312 established this rule twice — .agents/AGENTS.md scopes it to "
            "'nowhere else in this document' and rules/user-authorization-lock.md "
            "restates it for the authorization lock — so skills/ was covered by "
            "neither and feature-driven-implementation/SKILL.md:50 survived the sweep "
            "still naming a tool absent from this runtime. Documented normatively and "
            "given a gate here; the same missing-referent shape as the three rules "
            "above, with a tool as the referent instead of a path or a step."
        ),
    ),
    RuleContract(
        id="external-source-reference-must-not-be-self-referential",
        documented_in="rules/document-references.md",
        doc_anchor="Authoritative Source Locators Must Be Preserved Verbatim",
        enforced_in=f"{PARITY_SRC}/validators/source_reference_validator.py",
        enforcement_anchor="external-source-reference-must-not-be-self-referential",
        note=(
            "Issue #322, enforced by #320. A Structural Schema or Normative "
            "Specification is external by definition, so a locator pointing at this "
            "repository is the upstream URL having been rewritten during drafting. "
            "Reachability is deliberately NOT checked: pipeline-tooling.md "
            "Validation Gates forbids network egress in a blocking gate."
        ),
    ),
    RuleContract(
        id="source-reference-placeholder-must-be-populated",
        documented_in="rules/document-references.md",
        doc_anchor="Authoritative Source Locators Must Be Preserved Verbatim",
        enforced_in=f"{PARITY_SRC}/validators/source_reference_validator.py",
        enforcement_anchor="source-reference-placeholder-must-be-populated",
        note=(
            "Issue #320. 'link-to-schema' and 'link-to-specification' ship in the "
            "schema-specification-engineering and spec-usecase-engineering templates; "
            "surviving into a published spec means the block was never populated."
        ),
    ),
    RuleContract(
        id="source-reference-relative-link-must-resolve",
        documented_in="rules/document-references.md",
        doc_anchor="Cited Paths Must Resolve",
        enforced_in=f"{PARITY_SRC}/validators/source_reference_validator.py",
        enforcement_anchor="source-reference-relative-link-must-resolve",
        note=(
            "Issue #320. Extends the Cited Paths rule from governance documents, "
            "where test_skill_path_references.py already enforces it, to the "
            "backlog specifications under docs/."
        ),
    ),
    RuleContract(
        id="doc-ref-existence-claims-must-observe-symlinks",
        documented_in="rules/document-references.md",
        doc_anchor="Existence Claims Must Use Commands That Observe Symlinks",
        enforced_in="tests/test_process_discipline_gates.py",
        enforcement_anchor="`rules/document-references.md` must explicitly warn against `find -type f`.",
        note="Issue #345. `find -type f` ignores symlinks and symlink targets, producing false absence claims.",
    ),
]

DOC_REFERENCE_FAMILY = ContractFamily(
    name="document-references",
    contracts=DOC_REFERENCE_CONTRACTS,
    doc_file="rules/document-references.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
    enforcement_file="tests/test_skill_path_references.py",
    enforcement_files=[
        "tests/test_skill_path_references.py",
        f"{PARITY_SRC}/validators/source_reference_validator.py",
    ],
    # Terminate on ": " or ". " rather than a bare "." — one message embeds
    # ".agents/skills/", whose dot would otherwise truncate the extraction mid-path
    # and weaken orphan-enforcement detection for that rule.
    enforcement_pattern=r'"((?:governance )?documents [a-z][a-z\s\'./]{5,70}?)(?:: |\. )',
)

KARPATHY_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="karpathy-four-point-check-in-authorization-lock",
        documented_in="rules/user-authorization-lock.md",
        doc_anchor="4-point Karpathy and Pipeline Compliance Check",
        enforced_in="tests/test_karpathy_check_contract_issue312.py",
        enforcement_anchor=(
            "karpathy-gate: a governance document omits the four-point compliance check"
        ),
        note=(
            "Issue #312. Mandatory since the rule was written and enforced by nothing; "
            "not performed once during a session that produced 11 merges to main."
        ),
    ),
    RuleContract(
        id="karpathy-four-point-check-in-agents-md",
        documented_in=".agents/AGENTS.md",
        doc_anchor="4-point Karpathy and Pipeline Compliance Check",
        enforced_in="tests/test_karpathy_check_contract_issue312.py",
        enforcement_anchor=(
            "karpathy-gate: a governance document omits one of the four numbered points"
        ),
        note="The co-normative restatement. Deleting either statement must fail.",
    ),
    RuleContract(
        id="karpathy-delegation-scope-in-authorization-lock",
        documented_in="rules/user-authorization-lock.md",
        doc_anchor=(
            "The delegation duty binds for all repository source and specification "
            "writes, not only during named skill phases."
        ),
        enforced_in="tests/test_karpathy_check_contract_issue312.py",
        enforcement_anchor=(
            "karpathy-gate: a governance document omits the delegation scope statement"
        ),
        note=(
            "Point 4 was ambiguous about whether the delegation duty covered writes "
            "outside a named skill phase. The narrow reading was taken (#312)."
        ),
    ),
    RuleContract(
        id="karpathy-delegation-scope-in-agents-md",
        documented_in=".agents/AGENTS.md",
        doc_anchor=(
            "The delegation duty binds for all repository source and specification "
            "writes, not only during named skill phases."
        ),
        enforced_in="tests/test_karpathy_check_contract_issue312.py",
        enforcement_anchor=(
            "karpathy-gate: a governance document omits the delegation scope statement"
        ),
    ),
    RuleContract(
        id="karpathy-dispatch-machinery-is-runtime-neutral",
        documented_in=".agents/AGENTS.md",
        doc_anchor="Dispatch capability by runtime",
        enforced_in="tests/test_karpathy_check_contract_issue312.py",
        enforcement_anchor=(
            "karpathy-gate: agents md names a dispatch tool absent from the runtime"
        ),
        note=(
            "The remedy point 4 directs the agent to was specified as invoke_subagent "
            "and manage_subagents, neither of which exists in the Claude Code runtime, "
            "so literal compliance with AGENTS.md:75 was impossible (#312)."
        ),
    ),
]

KARPATHY_FAMILY = ContractFamily(
    name="karpathy-compliance-check",
    contracts=KARPATHY_CONTRACTS,
    enforcement_file="tests/test_karpathy_check_contract_issue312.py",
    enforcement_pattern=r'"(karpathy-gate: [a-z][a-z0-9 ]{5,80}?)(?:: |\. )',
    doc_file="rules/user-authorization-lock.md",
    doc_heading_pattern=r"(\b4-point Karpathy and Pipeline Compliance Check\b|Scope of point 4 \(issue #312\)\.|Subagent Authorization|Precedence)",
    doc_only={
        "Scope of point 4 (issue #312).": "Scope anchor for delegation duty",
        "Subagent Authorization": "Subagent authorization anchor",
        "Precedence": "Precedence rules anchor",
    },
)

SUBAGENT_ISOLATION_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="subagent-isolation-mandate-in-orchestrator-skill",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Item-Level Subagent Context Isolation",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a governance document omits the item level isolation mandate"
        ),
        note=(
            "Issue #278. Every specification item is drafted by a fresh subagent with "
            "no inherited session state."
        ),
    ),
    RuleContract(
        id="subagent-isolation-mandate-in-agents-md",
        documented_in=".agents/AGENTS.md",
        doc_anchor="Fresh, isolated context",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a governance document omits the item level isolation mandate"
        ),
        note="The co-normative restatement. Deleting either statement must fail.",
    ),
    RuleContract(
        id="subagent-isolation-no-session-history-in-orchestrator-skill",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Do **NOT** pass the history of other items generated in the same run.",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a governance document omits the no session history constraint"
        ),
        note=(
            "SKILL.md:74, the line issue #278 was filed against. It was already there; "
            "nothing asserted it stayed."
        ),
    ),
    RuleContract(
        id="subagent-isolation-no-session-history-in-agents-md",
        documented_in=".agents/AGENTS.md",
        doc_anchor="Do not copy the entire conversation history",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a governance document omits the no session history constraint"
        ),
    ),
    RuleContract(
        id="subagent-isolation-marker-named-at-point-of-generation",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="generation_mode",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: the drafting step omits the subagent generation mode marker"
        ),
        note=(
            "Issue #278, the real gap. The mandate was stated in two documents and the "
            "marker that proves compliance was named in neither, while the UML "
            "validator rejected any item lacking it -- the #299 shape, a rule a "
            "generating subagent was never shown."
        ),
    ),
    RuleContract(
        id="subagent-isolation-marker-in-spec-templates",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor='generation_mode: "subagent"',
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a specification template omits the generation mode marker"
        ),
        note=(
            "Also stated in spec-user-story-engineering and spec-usecase-engineering; "
            "the test checks all three, this anchor pins the Epic/Feature home."
        ),
    ),
    RuleContract(
        id="subagent-isolation-marker-enforced-by-parity-auditor",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="_validate_subagent_isolation",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: the parity auditor no longer enforces the isolation marker"
        ),
        note=(
            "Enforced for all four document types by validators/uml.py. Deleting the "
            "check, or narrowing it to fewer types, fails here."
        ),
    ),
    RuleContract(
        id="subagent-isolation-markdown-tables-not-banned-outright",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Markdown tables are not otherwise restricted",
        enforced_in="tests/test_subagent_isolation_contract_issue278.py",
        enforcement_anchor=(
            "isolation-gate: a governance document prohibits markdown tables outright"
        ),
        note=(
            "Issue #278 proposed 'The generation of Markdown tables is strictly "
            "prohibited'. reconcile_backlog.py::convert_frontmatter_to_table publishes "
            "a '| Metadata | Value |' table into every tracker issue body, so the "
            "literal remedy outlaws the pipeline's own output -- the #279 pattern, "
            "where the reported rule would have rejected the canonical template and "
            "only a narrower rule was correct."
        ),
    ),
]

SUBAGENT_ISOLATION_FAMILY = ContractFamily(
    name="subagent-isolation",
    contracts=SUBAGENT_ISOLATION_CONTRACTS,
    enforcement_file="tests/test_subagent_isolation_contract_issue278.py",
    # Only `isolation-gate:` messages are rules about the corpus. That file also emits
    # `isolation-guard:` messages, which are self-checks on its own fixtures and
    # scanners; pairing those with a document would be meaningless.
    enforcement_pattern=r'"(isolation-gate: [a-z][a-z0-9 ]{5,90})"',
    doc_file="rules/user-authorization-lock.md",
    doc_heading_pattern=r"(\b4-point Karpathy and Pipeline Compliance Check\b|Scope of point 4 \(issue #312\)\.|Subagent Authorization|Precedence)",
    doc_only={
        "4-point Karpathy and Pipeline Compliance Check": "Karpathy check anchor",
        "Scope of point 4 (issue #312).": "Scope anchor for delegation duty",
        "Subagent Authorization": "Subagent authorization anchor",
        "Precedence": "Precedence rules anchor",
    },
)


SCHEMA_TRACEABILITY_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="schema-container-declaration-missing",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Every Feature MUST declare exactly one schema container",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="schema-container-declaration-missing",
        note=(
            "Issue #304. The first family whose enforcement anchors are rule ids rather "
            "than message fragments -- see SCHEMA_TRACEABILITY_FAMILY for why."
        ),
    ),
    RuleContract(
        id="schema-container-field-must-be-a-list",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="with exactly one entry containing the fully-qualified container path",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="schema-container-field-must-be-a-list",
        note=(
            "The YAML shape, not merely the count: `schema_containers: module/thing` "
            "parses to a str and would otherwise be length-tested character by character."
        ),
    ),
    RuleContract(
        id="schema-container-declaration-empty",
        documented_in="skills/spec-usecase-engineering/SKILL.md",
        doc_anchor="with exactly one entry containing the container path",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="schema-container-declaration-empty",
    ),
    RuleContract(
        id="schema-container-consolidation-forbidden",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Multi-container Features are forbidden",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="schema-container-consolidation-forbidden",
        note="The threshold corrected by issue #283; documented in both worker skills.",
    ),
    RuleContract(
        id="schema-container-path-must-be-fully-qualified",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="fully-qualified schema container path format",
        enforced_in=f"{PARITY_SRC}/validators/spec_validator.py",
        enforcement_anchor="schema-container-path-must-be-fully-qualified",
        note=(
            "A path without a module prefix colon cannot be resolved back to a YANG "
            "module, so container traceability is unverifiable."
        ),
    ),
    RuleContract(
        id="sysml-extraction-missing",
        # Was anchored to a heading in implementation_plan.md, which is a working
        # document that gets rewritten; the heading went away and the rule became
        # orphan enforcement. Re-homed to rules/, which is where a normative rule
        # belongs and which rules/constitution-first.md requires agents to read.
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="SysML Nodes Must Be Extracted Into A Feature",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="sysml-extraction-missing",
    ),
    RuleContract(
        id="sysml-model-not-readable",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="SysML Models Must Be Readable",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="sysml-model-not-readable",
    ),
    RuleContract(
        id="sysml-feature-not-readable",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="SysML Feature Specifications Must Be Readable",
        enforced_in=f"{PARITY_SRC}/validators/cardinality_validator.py",
        enforcement_anchor="sysml-feature-not-readable",
    ),
]

SCHEMA_TRACEABILITY_FAMILY = ContractFamily(
    name="schema-traceability",
    contracts=SCHEMA_TRACEABILITY_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/cardinality_validator.py",
    enforcement_files=[
        f"{PARITY_SRC}/validators/cardinality_validator.py",
        f"{PARITY_SRC}/validators/spec_validator.py",
    ],
    # The five families above scan for message *text*. This one scans for the rule id
    # passed to Finding(), which is strictly stronger now that validators are migrating
    # to structured findings (#304): a text scanner has to be re-tuned every time a
    # message is reworded, and silently stops matching when it is -- an orphan-detection
    # test that quietly matches nothing is the failure this registry exists to prevent.
    # The rule id is the thing the aggregator actually groups on, so pairing *it* with a
    # document is what the contract is really asserting.
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/platform-independence.md",
    doc_heading_pattern=r"\*\*((?!Mermaid)[A-Z][^*]*?)\*\*:",
    doc_only={
        "Obsolete Token Namespace Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Hardcoded Standard Reference Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Backlog Standard And Platform Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Markdown Construct Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Code Fence Closure Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Diagram Fence Parity Rules": "Documented in rules/platform-independence.md for document-integrity",
    },
)


BACKLOG_INTEGRITY_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="tracker-issue-without-local-specification",
        documented_in="rules/tracker-source-of-truth.md",
        doc_anchor="Registered Issues Must Have A Local Specification",
        enforced_in=f"{PARITY_SRC}/validators/sync_validator.py",
        enforcement_anchor="tracker-issue-without-local-specification",
        note=(
            "Issue #304 found this enforced since the validator was written and stated "
            "in no document -- the #299 shape. Documented as part of the migration."
        ),
    ),
    RuleContract(
        id="spec-index-collides-with-tracker-issue",
        documented_in="rules/tracker-source-of-truth.md",
        doc_anchor="Local Indices Must Not Collide With Registered Issues",
        enforced_in=f"{PARITY_SRC}/validators/sync_validator.py",
        enforcement_anchor="spec-index-collides-with-tracker-issue",
        note=(
            "Also undocumented before #304. Distinct from "
            "spec-filename-ordinal-uniqueness, which is a collision between two local "
            "files; this is a local ordinal colliding with a differently-titled issue "
            "already holding that ordinal on the tracker."
        ),
    ),
    RuleContract(
        id="spec-title-must-be-unique-within-its-spec-type",
        documented_in="rules/tracker-source-of-truth.md",
        doc_anchor="Local Specification Titles Must Be Unique Within A Spec Type",
        enforced_in=f"{PARITY_SRC}/validators/spec_title_uniqueness_validator.py",
        enforcement_anchor="spec-title-must-be-unique-within-its-spec-type",
        note=(
            "Issue #318. Distinct from spec-index-collides-with-tracker-issue and from "
            "spec-filename-ordinal-uniqueness, which are collisions of the ordinal; "
            "this is a collision of the title, which is the key reconcile_backlog.py "
            "actually builds its issue lookup on. Scoped per spec type rather than "
            "globally, matching the (spec_type, normalised_title) identity #303 "
            "settled for sync_validator: an Epic and a Feature may share a subject, "
            "and a global set would reject that ordinary pairing."
        ),
    ),
    RuleContract(
        id="generated-title-namespacing-in-tracker-rule",
        documented_in="rules/tracker-source-of-truth.md",
        doc_anchor="Generated Item Titles Must Be Namespaced To Their Source Module",
        enforced_in="tests/test_title_namespacing_issue317.py",
        enforcement_anchor=(
            "namespacing-gate: the tracker rule omits the title namespacing constraint"
        ),
        note=(
            "Issue #317. The normative home for the constraint. Its enforced half is "
            "the uniqueness rule above; the prefix shape is deliberately not checked, "
            "recorded in KNOWN_UNREGISTERED_FAMILIES rather than left silent."
        ),
    ),
    RuleContract(
        id="generated-title-namespacing-in-orchestrator-skill",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="rules/tracker-source-of-truth.md",
        enforced_in="tests/test_title_namespacing_issue317.py",
        enforcement_anchor=(
            "namespacing-gate: the drafting step omits the title namespacing constraint"
        ),
        note=(
            "Not a co-normative restatement but a reference, per "
            "rules/platform-independence.md section Normative home & enforcement. The "
            "defect in #317 was that the dispatch payload never mentioned the "
            "constraint, so an item subagent could not comply -- the #299 shape, with "
            "the rule reaching the generator as the missing half. The companion "
            "assertion forbids the skill from copying the normative heading, which "
            "would fork the rule the way the four Mermaid statements had before #289."
        ),
    ),
    RuleContract(
        id="schema-import-dependency-unspecified",
        documented_in=".pipeline/constitution.md",
        doc_anchor=(
            "Cross-module or external schema references must be explicitly documented "
            "with source and target module names"
        ),
        enforced_in=f"{PARITY_SRC}/validators/dependency_validator.py",
        enforcement_anchor="schema-import-dependency-unspecified",
    ),
    RuleContract(
        id="epic-imported-schema-prerequisite-link-missing",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Schema Import Prerequisite Links",
        enforced_in=f"{PARITY_SRC}/validators/dependency_validator.py",
        enforcement_anchor="epic-imported-schema-prerequisite-link-missing",
        note=(
            "Undocumented before #304. The import ordering constraint was enforced and "
            "recorded nowhere a generating subagent would read it."
        ),
    ),
]

BACKLOG_INTEGRITY_FAMILY = ContractFamily(
    name="backlog-tracker-integrity",
    contracts=BACKLOG_INTEGRITY_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/sync_validator.py",
    enforcement_files=[
        f"{PARITY_SRC}/validators/sync_validator.py",
        f"{PARITY_SRC}/validators/dependency_validator.py",
        f"{PARITY_SRC}/validators/spec_title_uniqueness_validator.py",
    ],
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/tracker-source-of-truth.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
    doc_only=None,
)


PLATFORM_PROFILE_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="profile-scoping-requires-platform-sources",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Profile Scoping Requires Platform Sources",
        enforced_in=f"{PARITY_SRC}/validators/profile_scoping_validator.py",
        enforcement_anchor="profile-scoping-requires-platform-sources",
        note=(
            "Issue #304. The first family documented in a platform profile rather than "
            "in rules/: every rule here names the Flutter source tree, a Flutter widget "
            "or Flutter UI directories, so rules/platform-independence.md section Where "
            "platform-specific details belong sends it to the profile."
        ),
    ),
    RuleContract(
        id="flutter-splitter-requires-pointer-gesture-listener",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Splitter Widgets Require Pointer Gesture Listeners",
        enforced_in=f"{PARITY_SRC}/validators/profile_scoping_validator.py",
        enforcement_anchor="flutter-splitter-requires-pointer-gesture-listener",
        note=(
            "Enforced since the validator was written and documented nowhere -- the "
            "#299 shape. A splitter without a Listener or GestureDetector renders as a "
            "divider that cannot be dragged, so the layout requirement is met visually "
            "and not functionally."
        ),
    ),
    RuleContract(
        id="schema-mapping-requires-platform-sources",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Schema Mapping Requires Platform Sources",
        enforced_in=f"{PARITY_SRC}/validators/schema_mapping_validator.py",
        enforcement_anchor="schema-mapping-requires-platform-sources",
        note=(
            "Deliberately a distinct rule id from the profile-scoping precondition "
            "above, though the underlying condition -- no platform sources -- is the "
            "same. The two gates fail independently, and a grouped multi-workspace "
            "report that could not say which one fired would be ambiguous."
        ),
    ),
    RuleContract(
        id="schema-field-must-be-realised-in-the-codebase",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Schema Fields Must Be Realised In The Codebase",
        enforced_in=f"{PARITY_SRC}/validators/schema_mapping_validator.py",
        enforcement_anchor="schema-field-must-be-realised-in-the-codebase",
    ),
    RuleContract(
        id="schema-field-must-be-bound-to-a-ui-component",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Schema Fields Must Be Bound To A UI Component",
        enforced_in=f"{PARITY_SRC}/validators/schema_mapping_validator.py",
        enforcement_anchor="schema-field-must-be-bound-to-a-ui-component",
        note=(
            "Conditional on the workspace declaring flutter_rules.ui_directories; a "
            "project with no UI layer is not asked to bind anything."
        ),
    ),
    RuleContract(
        id="public-member-docstring-missing",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Public Member Docstrings Mandatory",
        enforced_in=f"{PARITY_SRC}/validators/docstring_validator.py",
        enforcement_anchor="public-member-docstring-missing",
        note="Enforces mandatory docstrings on public members in target source files.",
    ),
    RuleContract(
        id="uml-traceability-tag-missing",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="UML Traceability Tags Mandatory",
        enforced_in=f"{PARITY_SRC}/validators/profile_compliance_validator.py",
        enforcement_anchor="uml-traceability-tag-missing",
        note="Enforces UML traceability tags (/// Realises: [...]) on public declarations.",
    ),
    RuleContract(
        id="domain-immutable-annotation-missing",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Domain Immutable Annotations Mandatory",
        enforced_in=f"{PARITY_SRC}/validators/profile_compliance_validator.py",
        enforcement_anchor="domain-immutable-annotation-missing",
        note="Enforces @immutable annotations on all public domain model classes.",
    ),
    RuleContract(
        id="domain-result-signature-missing",
        documented_in=".pipeline/profiles/flutter.md",
        doc_anchor="Domain Result Signatures Mandatory",
        enforced_in=f"{PARITY_SRC}/validators/profile_compliance_validator.py",
        enforcement_anchor="domain-result-signature-missing",
        note="Enforces Result<T> return type signatures for fallible domain operations.",
    ),
]

PLATFORM_PROFILE_FAMILY = ContractFamily(
    name="platform-profile-compliance",
    contracts=PLATFORM_PROFILE_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/profile_scoping_validator.py",
    enforcement_files=[
        f"{PARITY_SRC}/validators/profile_scoping_validator.py",
        f"{PARITY_SRC}/validators/schema_mapping_validator.py",
        f"{PARITY_SRC}/validators/docstring_validator.py",
        f"{PARITY_SRC}/validators/profile_compliance_validator.py",
    ],
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    # Unlike every family registered before it, this one HAS a single normative home, so
    # orphan-documentation detection is live rather than blocked. `.pipeline/profiles/`
    # is where platform-specific constraints belong, and all five rules are Flutter-
    # specific, so nothing is fragmented across files here.
    doc_file=".pipeline/profiles/flutter.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
)


COVERAGE_GATE_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="test-suite-must-exist-in-the-workspace",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Test Suite Must Exist",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-must-exist-in-the-workspace",
        note="Issue #304. Undocumented before the migration -- the #299 shape.",
    ),
    RuleContract(
        id="test-suite-requires-regex-pattern-assertions",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Regex Pattern Assertions Required",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-requires-regex-pattern-assertions",
    ),
    RuleContract(
        id="test-suite-requires-numerical-precision-assertions",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Numerical Precision Assertions Required",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-requires-numerical-precision-assertions",
    ),
    RuleContract(
        id="test-suite-requires-computed-style-assertions",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Computed Style Assertions Required",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-requires-computed-style-assertions",
    ),
    RuleContract(
        id="test-suite-requires-layout-size-assertions",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Layout Size Assertions Required",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-requires-layout-size-assertions",
    ),
    RuleContract(
        id="test-suite-requires-exception-path-assertions",
        documented_in="rules/tdd-mandate.md",
        doc_anchor="Exception Path Assertions Required",
        enforced_in=f"{PARITY_SRC}/validators/test_completeness_validator.py",
        enforcement_anchor="test-suite-requires-exception-path-assertions",
    ),
    RuleContract(
        id="behavioral-trigger-node-must-be-covered-by-a-specification",
        documented_in="rules/behavioral-trigger-coverage.md",
        doc_anchor="Active Trigger Nodes Must Be Covered",
        enforced_in=f"{PARITY_SRC}/validators/behavioral.py",
        enforcement_anchor="behavioral-trigger-node-must-be-covered-by-a-specification",
        note=(
            "Issue #304 found the whole behavioural trigger mechanism enforced and "
            "stated in no document -- rules/behavioral_triggers.json carried the data "
            "and nothing carried the rule. rules/behavioral-trigger-coverage.md was "
            "written as its normative home."
        ),
    ),
    RuleContract(
        id="behavioral-trigger-rule-must-be-satisfied-by-the-specification",
        documented_in="rules/behavioral-trigger-coverage.md",
        doc_anchor="Trigger Rules Must Be Satisfied",
        enforced_in=f"{PARITY_SRC}/validators/behavioral.py",
        enforcement_anchor="behavioral-trigger-rule-must-be-satisfied-by-the-specification",
        note=(
            "Distinct from the coverage rule above: a file may reference the trigger "
            "node and still omit the Mermaid block or body terms the trigger requires, "
            "which looks like coverage and asserts nothing."
        ),
    ),
]

COVERAGE_GATE_FAMILY = ContractFamily(
    name="downstream-coverage-gates",
    contracts=COVERAGE_GATE_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/test_completeness_validator.py",
    enforcement_files=[
        f"{PARITY_SRC}/validators/test_completeness_validator.py",
        f"{PARITY_SRC}/validators/behavioral.py",
    ],
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/tdd-mandate.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
    doc_only=None,
)


DOCUMENT_INTEGRITY_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="doc-obsolete-token-namespace-reference",
        documented_in="rules/platform-independence.md",
        doc_anchor="Obsolete Token Namespace Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="doc-obsolete-token-namespace-reference",
        note="Issue #304. Enforced since docs.py was written, documented nowhere.",
    ),
    RuleContract(
        id="doc-hardcoded-standard-reference",
        documented_in="rules/platform-independence.md",
        doc_anchor="Hardcoded Standard Reference Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="doc-hardcoded-standard-reference",
        note=(
            "The blocklist itself is workspace configuration "
            "(spec_rules.forbidden_standards_blocklist); the rule that a document may "
            "not name what is on it is what belongs in a rule file."
        ),
    ),
    RuleContract(
        id="spec-standard-or-platform-leak",
        documented_in="rules/platform-independence.md",
        doc_anchor="Backlog Standard And Platform Leak Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="spec-standard-or-platform-leak",
        note=(
            "Applies only to files under the configured backlog directories, not to "
            "READMEs or profiles, which legitimately discuss implementation."
        ),
    ),
    RuleContract(
        id="spec-markdown-construct-inside-mermaid-block",
        documented_in="rules/platform-independence.md",
        doc_anchor="Markdown Construct Leak Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="spec-markdown-construct-inside-mermaid-block",
    ),
    RuleContract(
        id="spec-code-fence-must-be-closed",
        documented_in="rules/platform-independence.md",
        doc_anchor="Code Fence Closure Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="spec-code-fence-must-be-closed",
        note=(
            "Deliberately a separate rule id from mermaid-fence-must-be-closed in the "
            "Mermaid family. That rule governs a mermaid fence inside a diagram under "
            "audit; this one governs any fence in the enclosing Markdown document, and "
            "the two are owned by different validators. Sharing an id would make a "
            "grouped multi-workspace report unable to say which checker fired -- the "
            "one thing signature() grouping exists to make unambiguous."
        ),
    ),
    RuleContract(
        id="spec-mermaid-fence-count-must-be-even",
        documented_in="rules/platform-independence.md",
        doc_anchor="Diagram Fence Parity Rules",
        enforced_in=f"{PARITY_SRC}/validators/docs.py",
        enforcement_anchor="spec-mermaid-fence-count-must-be-even",
        note=(
            "The heading deliberately does not begin with 'Mermaid': MERMAID_FAMILY's "
            "doc_heading_pattern claims every '**Mermaid...**:' heading in this file, "
            "so a heading spelled that way would be reported as a Mermaid-family orphan."
        ),
    ),
]

DOCUMENT_INTEGRITY_FAMILY = ContractFamily(
    name="specification-document-integrity",
    contracts=DOCUMENT_INTEGRITY_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/docs.py",
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/platform-independence.md",
    # This family and MERMAID_FAMILY share a documentation file and partition its rule
    # headings between them: the Mermaid family claims every heading beginning
    # "Mermaid", this one claims the rest. The negative lookahead is what keeps the two
    # orphan scans from each reporting the other's rules. Without it, adding this family
    # would have turned nine correctly-registered Mermaid rules into orphans.
    doc_heading_pattern=r"\*\*((?!Mermaid)[A-Z][^*]*?)\*\*:",
)


LOGICAL_UI_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="logical-ui-layout-manifest-must-exist",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Layout Manifest Must Exist",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-layout-manifest-must-exist",
        note=(
            "Issue #304. The manifest-level rules are documented in the orchestrator "
            "skill because logical-layout.json is produced in its Phase 0 and no worker "
            "skill owns it; the Feature-level rules are documented in "
            "schema-specification-engineering, which owns the Feature template."
        ),
    ),
    RuleContract(
        id="logical-ui-layout-manifest-must-parse",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Layout Manifest Must Parse",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-layout-manifest-must-parse",
        note=(
            "Distinct from the existence rule: an unparseable manifest is reported as "
            "such rather than treated as an empty layout, which would report every "
            "Feature binding as invalid and point at the wrong file."
        ),
    ),
    RuleContract(
        id="logical-ui-tabbed-container-child-must-be-a-table-view",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Tabbed Containers Accept Only Tabular Children",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-tabbed-container-child-must-be-a-table-view",
        note=(
            "Three emission sites, one rule: a missing children list, a non-object "
            "child, and a child of a disallowed type. One rule id per rule, not per "
            "site."
        ),
    ),
    RuleContract(
        id="logical-ui-features-directory-must-exist",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="Features Directory Must Exist",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-features-directory-must-exist",
    ),
    RuleContract(
        id="logical-ui-feature-requires-layout-bindings-section",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Interface Bindings Section Required",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-feature-requires-layout-bindings-section",
        note=(
            "The section itself was already mandated by the Feature template; the "
            "interface_type exemption that decides which Features are excused was not "
            "documented anywhere before #304."
        ),
    ),
    RuleContract(
        id="logical-ui-feature-frontmatter-must-parse",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Feature Frontmatter Must Parse",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-feature-frontmatter-must-parse",
    ),
    RuleContract(
        id="logical-ui-prohibit-raw-na-fallback",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Raw N/A Fallback Strings Strictly Prohibited",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-prohibit-raw-na-fallback",
        note="Raw N/A fallback strings are strictly prohibited across interface bindings.",
    ),
    RuleContract(
        id="logical-ui-prohibit-placeholder-string",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Raw N/A Fallback Strings Strictly Prohibited",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-prohibit-placeholder-string",
        note="Literal placeholder strings (#X, Task Y) are strictly prohibited across interface bindings.",
    ),
    RuleContract(
        id="logical-ui-missing-interface-channel-row",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Interface Channel Row Required",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-missing-interface-channel-row",
        note="Every interface channel listed in frontmatter must have a row in the Multi-Interface Binding Table.",
    ),
    RuleContract(
        id="logical-ui-component-type-must-exist-in-the-layout",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Target Component Must Exist In The Layout",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-component-type-must-exist-in-the-layout",
    ),
    RuleContract(
        id="logical-ui-container-id-must-exist-in-the-layout",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Target Container Must Exist In The Layout",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-container-id-must-exist-in-the-layout",
    ),
    RuleContract(
        id="logical-ui-component-must-match-its-container-type",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Component Must Match Its Container Type",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-component-must-match-its-container-type",
    ),
    RuleContract(
        id="logical-ui-data-source-binding-must-be-a-schema-path",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Data Source Bindings Must Be Schema Paths",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-data-source-binding-must-be-a-schema-path",
    ),
    RuleContract(
        id="logical-ui-data-source-binding-must-omit-choice-and-case-nodes",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Data Source Bindings Must Omit Choice And Case Nodes",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-data-source-binding-must-omit-choice-and-case-nodes",
        note=(
            "A YANG choice/case node is a modelling construct absent from the data "
            "tree, so a data path containing one cannot resolve at runtime."
        ),
    ),
    RuleContract(
        id="logical-ui-augmented-node-must-carry-its-module-prefix",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Augmented Nodes Must Carry Their Module Prefix",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-augmented-node-must-carry-its-module-prefix",
        note=(
            "Two emission sites, one rule: the augmenting element itself and any "
            "descendant segment beneath it."
        ),
    ),
    RuleContract(
        id="logical-ui-spatial-feature-requires-a-spatial-component",
        documented_in="skills/schema-specification-engineering/SKILL.md",
        doc_anchor="Spatial Features Must Bind A Spatial Component",
        enforced_in=f"{PARITY_SRC}/validators/logical_ui_validator.py",
        enforcement_anchor="logical-ui-spatial-feature-requires-a-spatial-component",
        note=(
            "Complements the Geolocation & Geodetic Semantic Mapping Rules already in "
            "the same skill, which state where geodetic attributes may NOT be mapped; "
            "this states the positive requirement the validator actually enforces."
        ),
    ),
]

LOGICAL_UI_FAMILY = ContractFamily(
    name="logical-ui-bindings",
    contracts=LOGICAL_UI_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/logical_ui_validator.py",
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/platform-independence.md",
    doc_heading_pattern=r"\*\*((?!Mermaid)[A-Z][^*]*?)\*\*:",
    doc_only={
        "Obsolete Token Namespace Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Hardcoded Standard Reference Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Backlog Standard And Platform Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Markdown Construct Leak Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Code Fence Closure Rules": "Documented in rules/platform-independence.md for document-integrity",
        "Diagram Fence Parity Rules": "Documented in rules/platform-independence.md for document-integrity",
    },
)


CODEBASE_COMPLIANCE_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="platform-directory-must-exist-when-configured",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Configured Platform Directory Must Exist",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="platform-directory-must-exist-when-configured",
        note=(
            "Issue #304. A configured platform directory that is absent while matching sources sit elsewhere makes every platform check scan nothing, which reads as a clean run -- the message calls it a compliance bypass loophole for that reason."
        ),
    ),
    RuleContract(
        id="design-tokens-path-must-be-configured",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Design Tokens Path Must Be Configured",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="design-tokens-path-must-be-configured",
    ),
    RuleContract(
        id="design-tokens-file-must-exist",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Design Tokens File Must Exist",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="design-tokens-file-must-exist",
    ),
    RuleContract(
        id="design-tokens-file-must-be-loadable",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Design Tokens File Must Be Loadable",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="design-tokens-file-must-be-loadable",
    ),
    RuleContract(
        id="design-tokens-must-declare-colours",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Design Tokens Must Declare Colours",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="design-tokens-must-declare-colours",
        note=(
            "Four separate rules rather than one precondition, because each failure mode makes the hardcoded-colour checks vacuous in a different way and a vacuous check is indistinguishable from a compliant codebase."
        ),
    ),
    RuleContract(
        id="source-file-must-be-valid-utf8",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Source Files Must Be Valid UTF-8",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="source-file-must-be-valid-utf8",
    ),
    RuleContract(
        id="source-file-must-be-readable",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Source Files Must Be Readable",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="source-file-must-be-readable",
    ),
    RuleContract(
        id="hardcoded-design-token-colour-forbidden",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Hardcoded Design Token Colours Are Forbidden",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="hardcoded-design-token-colour-forbidden",
    ),
    RuleContract(
        id="selection-setter-requires-an-event-echo-guard",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Selection Setters Require An Event Echo Guard",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="selection-setter-requires-an-event-echo-guard",
    ),
    RuleContract(
        id="ui-layer-must-not-import-banned-libraries",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="UI Layers Must Not Import Banned Libraries",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="ui-layer-must-not-import-banned-libraries",
    ),
    RuleContract(
        id="network-gateway-requires-a-write-lock",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Network Gateways Require A Write Lock",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="network-gateway-requires-a-write-lock",
    ),
    RuleContract(
        id="viewport-requires-playhead-rate-clamps",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Viewports Require Playhead Rate Clamps",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="viewport-requires-playhead-rate-clamps",
    ),
    RuleContract(
        id="ffi-boundary-requires-a-native-finalizer",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="FFI Boundaries Require A Native Finalizer",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="ffi-boundary-requires-a-native-finalizer",
    ),
    RuleContract(
        id="ffi-boundary-requires-reference-counting",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="FFI Boundaries Require Reference Counting",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="ffi-boundary-requires-reference-counting",
        note=(
            "Distinct from the finalizer rule: a finalizer frees on collection, reference counting is what makes shared native memory safe to free at all."
        ),
    ),
    RuleContract(
        id="python-source-must-not-hardcode-token-constants",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Python Source Must Not Hardcode Token Constants",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="python-source-must-not-hardcode-token-constants",
        note=(
            "The AST-based twin of the colour-literal rule, so a colour assembled from constants is caught as well as one written literally."
        ),
    ),
    RuleContract(
        id="specification-must-not-leak-dom-attributes",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Specifications Must Not Leak DOM Attributes",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="specification-must-not-leak-dom-attributes",
        note=(
            "Documented here rather than in rules/platform-independence.md, which owns the same concern for backlog documents: this one is enforced by codebase.py over spec_rules.spec_files, and a rule file may only be heading-scanned by one family. Splitting the codebase rules across two doc files would leave whichever family did not own the file reporting the other's headings as orphans."
        ),
    ),
    RuleContract(
        id="specification-must-not-hardcode-pixel-dimensions",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Specifications Must Not Hardcode Pixel Dimensions",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="specification-must-not-hardcode-pixel-dimensions",
    ),
    RuleContract(
        id="specification-file-must-be-readable",
        documented_in="rules/codebase-compliance.md",
        doc_anchor="Specification Files Must Be Readable",
        enforced_in=f"{PARITY_SRC}/validators/codebase.py",
        enforcement_anchor="specification-file-must-be-readable",
    ),
]

CODEBASE_COMPLIANCE_FAMILY = ContractFamily(
    name="codebase-compliance",
    contracts=CODEBASE_COMPLIANCE_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/codebase.py",
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/codebase-compliance.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
)


UML_MODEL_CONTRACTS: List[RuleContract] = [
    RuleContract(
        id="epic-directory-must-exist-when-configured",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Epic Directory Must Exist When Configured",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="epic-directory-must-exist-when-configured",
        note=(
            "Issue #304. A missing Epic directory silently drops Epic-defined classes from the cross-document registry, so User Story lifelines resolving against them are then reported as undefined for the wrong reason."
        ),
    ),
    RuleContract(
        id="uml-validator-configuration-must-be-complete",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Validator Configuration Must Be Complete",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="uml-validator-configuration-must-be-complete",
        note=(
            "Eight emission sites, one rule: each document type has two configuration keys and each is reported the same way. One rule id per rule, not per site."
        ),
    ),
    RuleContract(
        id="backlog-document-must-be-readable",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Backlog Documents Must Be Readable",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="backlog-document-must-be-readable",
        note=(
            "Distinct id from specification-file-must-be-readable in the codebase-compliance family: that one governs spec_rules.spec_files read by codebase.py, this one governs the backlog corpus read by uml.py. Different validators, so a grouped report must be able to say which failed."
        ),
    ),
    RuleContract(
        id="backlog-document-requires-its-configured-sections",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Documents Must Carry Their Configured Sections",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="backlog-document-requires-its-configured-sections",
    ),
    RuleContract(
        id="backlog-document-requires-its-configured-diagrams",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Documents Must Carry Their Configured Diagrams",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="backlog-document-requires-its-configured-diagrams",
    ),
    RuleContract(
        id="feature-requires-a-test-data-payload-example",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Features Must Carry A Test Data Payload Example",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="feature-requires-a-test-data-payload-example",
    ),
    RuleContract(
        id="user-story-requires-a-bdd-scenario",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="User Stories Must Carry A BDD Scenario",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="user-story-requires-a-bdd-scenario",
    ),
    RuleContract(
        id="user-story-requires-a-required-features-matrix",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="User Stories Must Carry A Required Features Matrix",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="user-story-requires-a-required-features-matrix",
    ),
    RuleContract(
        id="user-story-matrix-requires-a-feature-reference",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="The Features Matrix Must Reference At Least One Feature",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="user-story-matrix-requires-a-feature-reference",
    ),
    RuleContract(
        id="use-case-filename-must-follow-the-naming-convention",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Case Filenames Must Follow The Naming Convention",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-filename-must-follow-the-naming-convention",
        note=(
            "Distinct from spec-filename-format in the spec-filename family, which checks ordinal and padding shape across a directory; this checks one file against the pattern configured for use cases."
        ),
    ),
    RuleContract(
        id="use-case-requires-alternate-and-exception-flows",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Cases Must Carry Alternate And Exception Flows",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-requires-alternate-and-exception-flows",
        note=(
            "The required count is derived from the schema validation constraints declared by the referenced Features, so it scales with the contract rather than being a fixed floor."
        ),
    ),
    RuleContract(
        id="use-case-alternate-flow-requires-numbered-steps",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Alternate Flows Must Be Detailed",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-alternate-flow-requires-numbered-steps",
    ),
    RuleContract(
        id="use-case-requires-an-alternate-flows-block",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Cases Must Carry An Alternate Flows Block",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-requires-an-alternate-flows-block",
    ),
    RuleContract(
        id="use-case-requires-a-complete-realization-matrix",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Cases Must Carry A Complete Realization Matrix",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-requires-a-complete-realization-matrix",
        note=(
            "Two sites, one rule: the User Stories header and the Features header are the two halves of the same matrix."
        ),
    ),
    RuleContract(
        id="use-case-realization-matrix-requires-checklist-entries",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="The Realization Matrix Must Carry Checklist Entries",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-realization-matrix-requires-checklist-entries",
        note=(
            "Distinct from the rule above: the headers can both be present and both sections empty, which asserts traceability that does not exist."
        ),
    ),
    RuleContract(
        id="checklist-item-requires-an-absolute-url",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Checklist Items Must Carry An Absolute URL",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="checklist-item-requires-an-absolute-url",
        note=(
            "Four sites, one rule: two in the User Story Required Features Matrix and two in the Use Case Realization Matrix."
        ),
    ),
    RuleContract(
        id="checklist-item-requires-a-semantic-justification",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Checklist Items Must Carry A Semantic Justification",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="checklist-item-requires-a-semantic-justification",
    ),
    RuleContract(
        id="epic-checklist-item-requires-a-feature-file-link",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Epic Checklist Items Must Link To A Feature File",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="epic-checklist-item-requires-a-feature-file-link",
    ),
    RuleContract(
        id="specification-must-not-contain-template-placeholders",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Specifications Must Not Contain Template Placeholders",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="specification-must-not-contain-template-placeholders",
        note=(
            "The detector this rule states was repaired by issue #281, which found it blind to '[Epic Title]', '(semantic linkage justification)' and '*(None)*'."
        ),
    ),
    RuleContract(
        id="specification-must-not-contain-unresolved-registration-tokens",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Specifications Must Not Contain Unresolved Registration Tokens",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="specification-must-not-contain-unresolved-registration-tokens",
        note=(
            "Also #281: the check was 'IssueID' in content, which does not match '#[EpicID]'."
        ),
    ),
    RuleContract(
        id="epic-prohibit-unreplaced-placeholder-text",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Epic Prohibit Unreplaced Placeholder Text",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="epic-prohibit-unreplaced-placeholder-text",
        note=(
            "Prohibits literal '(semantic linkage justification)' and '[POPULATE:' placeholder tokens in Epic markdown files (#391)."
        ),
    ),
    RuleContract(
        id="specification-requires-the-subagent-generation-mode-marker",
        documented_in="skills/spec-orchestrator/SKILL.md",
        doc_anchor="generation_mode",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="specification-requires-the-subagent-generation-mode-marker",
        note=(
            "Keeps its existing home rather than being restated here. Already registered as subagent-isolation-marker-enforced-by-parity-auditor in the subagent-isolation family, which pairs the mandate with the documents stating it; this contract pairs the emitted rule id with the same statement, which is what #304 requires."
        ),
    ),
    RuleContract(
        id="sequence-diagram-must-parse",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Sequence Diagrams Must Parse",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-diagram-must-parse",
    ),
    RuleContract(
        id="sequence-lifeline-requires-name-and-classifier",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Lifelines Must Declare A Name And A Classifier",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-lifeline-requires-name-and-classifier",
    ),
    RuleContract(
        id="sequence-lifeline-classifier-must-be-defined",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Lifeline Classifiers Must Be Defined",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-lifeline-classifier-must-be-defined",
        note=(
            "The actor exemption is the resolution of issue #277 and of AMEND-0001; it keys on the UML role the parser records, not on a name suffix."
        ),
    ),
    RuleContract(
        id="sequence-message-requires-an-operation-signature",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Messages Must Carry An Operation Signature",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-message-requires-an-operation-signature",
    ),
    RuleContract(
        id="sequence-message-operation-must-exist-on-the-receiver",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Message Operations Must Exist On The Receiver",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-message-operation-must-exist-on-the-receiver",
    ),
    RuleContract(
        id="sequence-message-operation-must-be-public",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Message Operations Must Be Public",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-message-operation-must-be-public",
    ),
    RuleContract(
        id="sequence-return-message-requires-a-reply-arrow",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Return Messages Must Use A Reply Arrow",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-return-message-requires-a-reply-arrow",
    ),
    RuleContract(
        id="sequence-return-message-must-not-be-an-operation-call",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Return Messages Must Not Look Like Calls",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-return-message-must-not-be-an-operation-call",
    ),
    RuleContract(
        id="sequence-combined-fragment-guard-requires-square-brackets",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Combined Fragment Guards Must Be Bracketed",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="sequence-combined-fragment-guard-requires-square-brackets",
    ),
    RuleContract(
        id="use-case-flowchart-must-parse",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Case Flowcharts Must Parse",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-flowchart-must-parse",
    ),
    RuleContract(
        id="use-case-requires-a-system-boundary-subgraph",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Cases Must Declare A System Boundary Subgraph",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-requires-a-system-boundary-subgraph",
    ),
    RuleContract(
        id="use-case-actor-must-be-outside-the-system-boundary",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Actors Must Sit Outside The System Boundary",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-actor-must-be-outside-the-system-boundary",
    ),
    RuleContract(
        id="use-case-node-must-be-inside-the-system-boundary",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Case Nodes Must Sit Inside The System Boundary",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-node-must-be-inside-the-system-boundary",
    ),
    RuleContract(
        id="use-case-node-must-use-the-stadium-shape",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Use Case Nodes Must Use The Stadium Shape",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-node-must-use-the-stadium-shape",
    ),
    RuleContract(
        id="use-case-actor-association-must-be-undirected",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Actor Associations Must Be Undirected",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="use-case-actor-association-must-be-undirected",
    ),
    RuleContract(
        id="class-diagram-member-must-not-contain-braces",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Class Member Brace Rules",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-member-must-not-contain-braces",
        note=(
            "Not restated in rules/uml-model-integrity.md. platform-independence.md is the single normative home for Mermaid syntax constraints and restating it would breach its own Normative home clause. Distinct rule id from mermaid-no-curly-brace-in-class-member because a different validator emits it, per the decision recorded on #304."
        ),
    ),
    RuleContract(
        id="class-diagram-note-must-not-contain-colons",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Note Rules",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-note-must-not-contain-colons",
        note=(
            "Same arrangement as the brace rule above."
        ),
    ),
    RuleContract(
        id="class-diagram-relationship-must-not-carry-a-stereotype",
        documented_in="rules/platform-independence.md",
        doc_anchor="Mermaid Relationship Rules",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-relationship-must-not-carry-a-stereotype",
        note=(
            "Same arrangement as the brace rule above."
        ),
    ),
    RuleContract(
        id="class-diagram-must-parse",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Class Diagrams Must Parse",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-must-parse",
    ),
    RuleContract(
        id="class-diagram-requires-relationships",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Class Diagrams Must Declare Relationships",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-requires-relationships",
    ),
    RuleContract(
        id="class-diagram-connector-must-be-recognised",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Relationship Connectors Must Be Recognised",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-connector-must-be-recognised",
    ),
    RuleContract(
        id="class-diagram-class-must-not-be-isolated",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Classes Must Not Be Isolated",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-class-must-not-be-isolated",
        note=(
            "Narrower than the requires-relationships rule: a diagram can be richly connected and still leave one class attached to nothing."
        ),
    ),
    RuleContract(
        id="class-diagram-must-be-connected",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Class Diagrams Must Be Connected",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-must-be-connected",
    ),
    RuleContract(
        id="class-attribute-requires-a-type",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Attributes Must Declare A Type",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-attribute-requires-a-type",
    ),
    RuleContract(
        id="class-attribute-type-must-be-a-uml-primitive",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Attribute Types Must Be UML Primitives",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-attribute-type-must-be-a-uml-primitive",
    ),
    RuleContract(
        id="choice-class-requires-a-generalization-subclass",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Choice Classes Must Have A Subclass",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="choice-class-requires-a-generalization-subclass",
    ),
    RuleContract(
        id="class-member-requires-a-visibility-prefix",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Members Must Declare A Visibility Prefix",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-member-requires-a-visibility-prefix",
        note=(
            "Two sites, one rule: attributes and methods. Visibility is what the sequence-message-operation-must-be-public rule is evaluated against, so an unprefixed member makes that rule unevaluable rather than merely untidy."
        ),
    ),
    RuleContract(
        id="class-member-requires-a-multiplicity",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Members Must Declare A Multiplicity",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-member-requires-a-multiplicity",
        note=(
            "Two sites, one rule: attributes and method return signatures."
        ),
    ),
    RuleContract(
        id="subsystem-component-class-must-declare-members",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Subsystem Component Classes Must Declare Members",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="subsystem-component-class-must-declare-members",
        note=(
            "Deliberately narrower than a ban on attribute-less classes, which would reject the canonical Feature template -- the distinction issue #279 established."
        ),
    ),
    RuleContract(
        id="class-diagram-must-model-the-schema-container-path",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Class Diagrams Must Model The Schema Container Path",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-must-model-the-schema-container-path",
    ),
    RuleContract(
        id="class-diagram-relationship-requires-multiplicity",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Composition And Aggregation Relationships Must Declare A Multiplicity",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-relationship-requires-multiplicity",
    ),
    RuleContract(
        id="class-diagram-must-model-the-schema-containment-relationships",
        documented_in="rules/uml-model-integrity.md",
        doc_anchor="Class Diagrams Must Model The Schema Containment Relationships",
        enforced_in=f"{PARITY_SRC}/validators/uml.py",
        enforcement_anchor="class-diagram-must-model-the-schema-containment-relationships",
    ),
]

UML_MODEL_FAMILY = ContractFamily(
    name="uml-model-integrity",
    contracts=UML_MODEL_CONTRACTS,
    enforcement_file=f"{PARITY_SRC}/validators/uml.py",
    enforcement_pattern=r'Finding\(\s*"([a-z][a-z0-9-]+)"',
    doc_file="rules/uml-model-integrity.md",
    doc_heading_pattern=r"\*\*([A-Z][^*]*?)\*\*:",
    doc_only={
        "SysML Nodes Must Be Extracted Into A Feature": (
            "Registered in the schema-traceability family as sysml-extraction-missing, "
            "and enforced in cardinality_validator.py rather than uml.py. It is stated "
            "in this document because this file is the normative home for the "
            "model-integrity constraints, and because its previous anchor -- a heading "
            "in implementation_plan.md -- was deleted when that working document was "
            "rewritten, leaving the rule enforced and documented nowhere."
        ),
        "SysML Models Must Be Readable": (
            "Registered in the schema-traceability family as sysml-model-not-readable, "
            "and enforced in cardinality_validator.py rather than uml.py."
        ),
        "SysML Feature Specifications Must Be Readable": (
            "Registered in the schema-traceability family as sysml-feature-not-readable, "
            "and enforced in cardinality_validator.py rather than uml.py."
        ),
    },
)


# NOTE: `FAMILIES` is bound ONCE, at the very bottom of this module, after
# `MERMAID_FAMILY` has been rebound with its doc-only exemptions. There used to be a
# binding here as well; the lower one shadowed it and omitted `DOC_REFERENCE_FAMILY`,
# so three registered contracts were asserted by nothing while the suite reported
# green. `tests/test_families_binding_is_unique.py` now fails on a second binding.
# Do not reintroduce one here.


# Rule families known to exist and deliberately not yet registered. Listing them
# keeps the gap explicit: an empty registry section is indistinguishable from a
# complete one otherwise.
KNOWN_UNREGISTERED_FAMILIES = {
    "schema-container-cardinality": "covered ad hoc by test_schema_container_docs_issue283.py",
    "authorization-precedence": "covered ad hoc by test_authorization_precedence.py",
    "python-version-reconciliation": "covered ad hoc by test_ci_workflow_config.py",
    # "spec-filename-uniqueness" was listed here as "not yet enforced at all - issue
    # #300". That stopped being true when #300 shipped spec_filename_validator.py and
    # FILENAME_FAMILY was registered in FAMILIES below, and the entry survived the
    # change. Removed at #304. A stale disclaimer is worse than no disclaimer: this
    # mapping exists so an incomplete registry is distinguishable from a complete one,
    # and an entry claiming a registered family is unenforced inverts that signal.
    # "document-references" was listed here while DOC_REFERENCE_FAMILY sat outside the
    # live FAMILIES binding. It is now registered and asserted, so the entry is gone
    # rather than being left as a stale disclaimer. The vacuity guard it tripped
    # (rules/document-references.md stated 3 rule headings against a guard of >= 4) was
    # resolved by documenting a fourth genuine constraint -- runtime dispatch tool names
    # belong only in the .agents/AGENTS.md dispatch table -- not by lowering the guard.
    # That rule was already normative in two file-scoped statements written for #312,
    # was violated by skills/feature-driven-implementation/SKILL.md:50 at the time of
    # writing, and is now mechanically enforced.
    "generated-title-prefix-shape": (
        "issue #317 - the namespacing rule's two halves are enforced unequally, and "
        "that is deliberate. Its *effect* is gated: "
        "spec-title-must-be-unique-within-its-spec-type rejects two specifications of "
        "one type whose titles normalise to the same key, which is the collision that "
        "actually corrupts the tracker. Its *shape* - a bracketed module short-code at "
        "the front of every generated title - is not checked, and a checker would be "
        "wrong here rather than merely absent. Every one of the 25 specifications in "
        "this repository and in every downstream corpus predates the rule and carries "
        "no prefix, so a shape check turns the linter red everywhere on a cosmetic "
        "criterion while the invariant it approximates is already gated. It is also "
        "the pattern issue #279 warned about: enforcing the remedy proposed on the "
        "issue rather than the invariant behind it would reject the canonical "
        "template. What IS enforced is that the constraint is stated normatively in "
        "rules/tracker-source-of-truth.md and reaches the drafting subagent through "
        "skills/spec-orchestrator/SKILL.md - see the two "
        "generated-title-namespacing-* contracts in BACKLOG_INTEGRITY_CONTRACTS, "
        "which is the half that was actually missing when #317 was filed. Closing "
        "this would need the corpus to be regenerated under the rule first, so the "
        "shape check has something to be true of."
    ),
    "karpathy-check-performance": (
        "issue #312 - the two statements of the 4-point Karpathy and Pipeline "
        "Compliance Check and their scope sentence are now registered as the "
        "karpathy-compliance-check family, so deleting either statement fails the "
        "suite. That pairs documentation with documentation. Nothing verifies the "
        "check is actually PERFORMED: it is a per-turn reasoning obligation with no "
        "artefact in the repository, so no test over source can observe it. Closing "
        "this would need an out-of-band control - a transcript/thought-block auditor "
        "or a runtime pre-tool-use hook that refuses a coordinator write until the "
        "check is recorded for that turn. Neither exists here. "
        "A pre-tool-use hook of exactly that shape was built and then withdrawn under "
        "implementation_plan.md Part R: it worked, but the machinery was judged "
        "disproportionate to the problem and the simpler control was kept instead "
        "(removal of blanket write permissions, so each write is confirmed "
        "interactively). This entry therefore remains fully open, and deliberately so "
        "- recording it as closed on the strength of a control that is no longer "
        "present is the stale-disclaimer failure this mapping exists to prevent."
    ),
}


# Documented Mermaid rule headings in rules/platform-independence.md that are
# intentionally not paired with an enforcement anchor, with the reason. Anything not
# listed here and not in the registry is an orphan-documentation failure.
# Known divergences between a governing document and the implemented rule, recorded so
# they are visible rather than forgotten. Each must name the amendment that resolves it.
# An agent may not edit .pipeline/constitution.md (AGENTS.md:59, project-constitution
# Core Mandate 4), so constitution-level divergences can only be recorded here and
# submitted for human approval.
# OPEN divergences. Empty is the goal, not a defect — but the structure must remain so
# a future divergence has a defined home rather than being left undocumented.
KNOWN_DOC_DIVERGENCES: dict = {
    "coordinator-direct-governance-writes": (
        "rules/role-boundary-lock.md section Coordinator Direct Writing & Research "
        "Lock, and .agents/AGENTS.md section Strict Coordinator Tool Locking point 4, "
        "require every repository source, governance and tooling write to be delegated "
        "to a context-isolated subagent. In this runtime that rule is unexecutable as "
        "written: the harness is configured not to spawn subagents unless the user "
        "explicitly requests one, so a coordinator facing a governance repair has no "
        "compliant route and -- per issue #312 -- does the work itself rather than "
        "halting. That is exactly what happened in implementation_plan.md Part Q, "
        "where the conflict was raised as an open question (Q6), never answered, and "
        "then resolved silently by the coordinator in its own favour. "
        "DECISION: the user was asked directly and chose coordinator-direct execution "
        "with this divergence registered, over delegation or amendment "
        "(implementation_plan.md Part R, decision D1). "
        "RESOLUTION PATH: either the runtime configuration changes to permit standing "
        "subagent dispatch, or rules/role-boundary-lock.md is amended to scope the "
        "delegation duty to specification and implementation phases and exclude "
        "governance and tooling repair. The second option was offered and not taken, "
        "so the rule stands as written and this entry records that practice diverges "
        "from it deliberately rather than accidentally."
    ),
}


# RESOLVED divergences, retained as history. Each MUST name the amendment or change that
# resolved it, so the register records how divergences were closed and not merely that
# they vanished.
RESOLVED_DIVERGENCES = {
    "reconciler-auto-closes-issues": (
        "skills/spec-orchestrator/scripts/reconcile_backlog.py closed Epics, User "
        "Stories and Use Cases automatically at three call sites, while "
        ".pipeline/constitution.md:161 makes Closed unreachable without Product Owner "
        "validation. This was the enforced-side twin of the documentation divergence: "
        "the skills instructed closure and the tooling performed it, and AGENTS.md "
        "requires the reconciler run before every merge, so it was mandated to execute. "
        "RESOLVED by #309, which replaced close_issue_on_tracker with "
        "resolve_issue_on_tracker applying status:fixed-resolved plus an evidence "
        "comment, moved the idempotency guard from issue state onto the label, and "
        "corrected skills/spec-orchestrator/SKILL.md in the same change."
    ),
    "skills-instruct-closing-issues": (
        "skills/debug-protocol/SKILL.md and "
        "skills/feature-driven-implementation/SKILL.md instructed the agent to close "
        "tracker issues across 6 detected sites, while .pipeline/constitution.md:161 "
        "reserves Closed for Product Owner validation. "
        ".pipeline/upstream/pipeline-tooling.md declared an override, which could not "
        "work: AGENTS.md:75 mandates literal skill execution and that profile is "
        "upstream-only. RESOLVED by #306, which amended both skills to stop at "
        "Fixed / Resolved, narrowed debug-protocol's selection query to exclude "
        "status:fixed-resolved so the loop still terminates, and added "
        "tests/test_skills_never_close_issues_issue306.py as the enforcing gate."
    ),
    "constitution-lifeline-actor-exemption": (
        ".pipeline/constitution.md:41 required every sequence-diagram lifeline to resolve "
        "to a defined Class or Component, while issue #277 option B exempts external UML "
        "actors. RESOLVED by AMEND-0001, which added the exemption and restated the "
        "requirement for all non-actor lifelines."
    ),
    "constitution-proceed-keyword-sufficiency": (
        ".pipeline/constitution.md:120 treated an authorization keyword as sufficient, "
        "while .agents/AGENTS.md:7 states it is not without an approved plan; issue #295 "
        "unified on the stricter reading. RESOLVED by AMEND-0002, which now requires both "
        "an approved implementation plan and the keyword."
    ),
}


DOC_ONLY_MERMAID_RULES = {
    "Mermaid Class Naming Rules": (
        "Backtick/quote requirements for class names are enforced inside the class "
        "diagram parser rather than the syntax validator; pairing deferred."
    ),
}


# Bound after definition: the Mermaid family's intentional doc-only exemptions.
MERMAID_FAMILY = ContractFamily(
    name=MERMAID_FAMILY.name,
    contracts=MERMAID_FAMILY.contracts,
    enforcement_file=MERMAID_FAMILY.enforcement_file,
    enforcement_pattern=MERMAID_FAMILY.enforcement_pattern,
    doc_file=MERMAID_FAMILY.doc_file,
    doc_heading_pattern=MERMAID_FAMILY.doc_heading_pattern,
    doc_only=DOC_ONLY_MERMAID_RULES,
)
# The single binding of FAMILIES. It must stay here, below the MERMAID_FAMILY rebinding
# above, because that rebinding is what attaches the doc-only exemptions; a list built
# before it would capture the exemption-less instance.
#
# There were formerly two bindings, and the second shadowed the first. The shadowed list
# held DOC_REFERENCE_FAMILY and the live one did not, so from #310 onward the three
# doc-ref contracts were derived into neither ALL_CONTRACTS nor any parametrized
# assertion — registered on paper, checked by nothing, suite green. That is this
# registry failing its own premise: it exists to detect a documented contract diverging
# from an enforced one, and the divergence was inside the detector.
#
# Any new family must be added to this list. tests/test_families_binding_is_unique.py
# asserts both halves of the invariant: exactly one binding of the name, and no
# ContractFamily defined in this module that is missing from it.
FAMILIES: List[ContractFamily] = [
    MERMAID_FAMILY,
    FILENAME_FAMILY,
    DOC_REFERENCE_FAMILY,
    KARPATHY_FAMILY,
    SUBAGENT_ISOLATION_FAMILY,
    SCHEMA_TRACEABILITY_FAMILY,
    BACKLOG_INTEGRITY_FAMILY,
    PLATFORM_PROFILE_FAMILY,
    COVERAGE_GATE_FAMILY,
    DOCUMENT_INTEGRITY_FAMILY,
    LOGICAL_UI_FAMILY,
    CODEBASE_COMPLIANCE_FAMILY,
    UML_MODEL_FAMILY,
]
ALL_CONTRACTS: List[RuleContract] = [c for f in FAMILIES for c in f.contracts]


# The `id` field of each contract is the same string validators pass as Finding.rule_id.
# tests/test_rule_contracts.py asserts every emitted rule id is registered here, so a new
# finding cannot become invisible to aggregation (#301) or undocumented (#299).
REGISTERED_RULE_IDS = {c.id for c in ALL_CONTRACTS}
