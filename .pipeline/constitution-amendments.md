# Constitution Amendment Log

Append-only record of every change to `.pipeline/constitution.md`.

`tests/test_constitution_integrity.py` asserts that the SHA-256 of the constitution
matches the newest entry below. **The constitution therefore cannot be changed by
anyone — human or agent — without a logged entry.** An unlogged edit fails the suite.

## Why this exists

`.agents/AGENTS.md:60` permits rewriting `constitution.md` only when *"every line of
the replacement has been explicitly approved by the user in the current conversation
turn"*, and `skills/project-constitution/SKILL.md` Mandate 4 forbids modifying it
*autonomously*. Both allow an approved amendment; neither described **how**.

`project-constitution` Step 7 gave implementation profiles a full lifecycle — add,
update, remove, list — while the constitution, the higher-authority Tier 1 document,
had a single sentence at line 285. The stronger document had the weaker process, so
the safe default became refusal, and two known defects stayed unfixed as a result.
See Step 9 of that skill for the procedure this log serves.

## Entry format

Every entry MUST carry all fields. The integrity test rejects a partial entry.

- **Date** — the date of the constitution change, matching the file's `last_updated`.
- **Logged** — when this entry was written.
- **Motivating issue** — the issue that justifies the change, or `n/a` with a reason.
- **Approved by** — verbatim quote of the human's approval, or `n/a` for the baseline.
- **Destructive** — `no` if the change is purely additive or a refinement in place.
  `yes` requires a justification paragraph; `project-constitution` Mandate 3 requires
  amendments to be cumulative and never destructive.
- **Line count** — lines in the resulting file. A non-destructive entry may not
  reduce it below the previous entry.
- **Resulting SHA-256** — checksum of `.pipeline/constitution.md` after the change.

---

## AMEND-0000 — Baseline

- **Date:** 2026-06-29
- **Logged:** 2026-07-31
- **Motivating issue:** n/a — protocol adoption, no content change
- **Approved by:** n/a — baseline record; the constitution was not modified
- **Destructive:** no
- **Line count:** 161
- **Resulting SHA-256:** `ae68494ed6190919dc342612d27f873d01f273750b2d1418aa3516913dac24e9`

Records the constitution's state at the moment the amendment protocol was adopted, so
the integrity test has a starting point. No content was changed by this entry. The
`Date` is the constitution's existing `last_updated` value rather than the date this
entry was written, because it records the state as of the last actual change.

### Amendments known to be pending at baseline

Two divergences between the constitution and the implemented, enforced behaviour were
outstanding when this log was created. Both are registered in
`tests/rule_contracts.py` `KNOWN_DOC_DIVERGENCES` and both require line-by-line human
approval before they can be applied through Step 9:

1. **Line 41 — external actor exemption (issue #277).** The constitution requires
   *every* sequence-diagram lifeline to resolve to a defined Class or Component. The
   enforced rule exempts lifelines declared as external UML actors, which are outside
   the system boundary and correctly absent from the structural models.
2. **Line 120 — authorization sufficiency (issue #295).** The constitution states that
   typing "Proceed" is sufficient authorization. `.agents/AGENTS.md:7` states a
   keyword is explicitly insufficient without an approved implementation plan, and
   #295 unified on the stricter reading. The constitution sentence remains weaker.

---

## AMEND-0001 — External actor exemption for sequence-diagram lifelines

- **Date:** 2026-07-31
- **Logged:** 2026-07-31
- **Motivating issue:** #277 (implemented), #298 (divergence class)
- **Approved by:** "approve both" — in response to Amendments A and B quoted verbatim as current-versus-proposed text, per Step 9 items 2 and 3.
- **Destructive:** no
- **Line count:** 161
- **Resulting SHA-256:** `98434ea59d1fdba780cf2aea430004658c0dc0776519f0374c96a809e5152a6e`

### Change

Section *Universal Model Consistency Rules*, line 41.

Before:

> - Every lifeline in a sequence diagram MUST represent an instance of a defined logical Class or Component.

After:

> - Every lifeline in a sequence diagram MUST represent an instance of a defined logical Class or Component, except lifelines declared as external actors (UML `actor`), which represent entities outside the system boundary and are therefore not defined in the structural models. Every non-actor lifeline MUST resolve to a defined classifier.

### Rationale

Issue #277 replaced a name-suffix bypass in `validators/uml.py` with an exemption keyed
on UML role. The prior rule exempted classifiers by spelling — `PaymentManager` passed
while `PaymentHandler` did not — and, because an exempt classifier never entered the
global class registry, it also silently disabled operation-signature validation for
every message sent to that lifeline.

Deleting the bypass outright was tested and rejected: an ordinary human actor
`payer : Payer` was reported undefined, which is the false-positive class that commit
`a5de5f8` had introduced the bypass to remove. A UML `actor` denotes an entity outside
the system boundary and is correctly absent from the structural models.

The sentence as written required *every* lifeline to resolve, so the implemented rule
was narrower than the constitution. Left unamended this would have been an eighth
instance of the defect class #298 exists to detect — a documented contract diverging
from the enforced one — created while closing the third.

Non-destructive: the original requirement is preserved in full and an exemption is
carved out. The second clause restates the requirement for all non-actor lifelines so
no obligation is weakened by implication.

---

## AMEND-0002 — Authorization requires an approved plan, not only a keyword

- **Date:** 2026-07-31
- **Logged:** 2026-07-31
- **Motivating issue:** #295
- **Approved by:** "approve both" — in response to Amendments A and B quoted verbatim as current-versus-proposed text, per Step 9 items 2 and 3.
- **Destructive:** no
- **Line count:** 161
- **Resulting SHA-256:** `5dc3da88e38fa9333e1dd297701fdd4082fda48b343363f850e1ab20a26e5e50`

### Change

Section *Strict Planning Mode Gate (Insurmountable Approval Gate)*, line 120. Line 121
is untouched.

Before:

> - Under NO circumstances may the agent invoke any file-writing, file-modifying, or command-running tools that alter the codebase/repository files unless the user has explicitly typed "Proceed", "Approved", or "Approve plan" in the conversation history of the current turn sequence.

After:

> - Under NO circumstances may the agent invoke any file-writing, file-modifying, or command-running tools that alter the codebase/repository files unless BOTH of the following hold: (1) the specific file and its exact changes are documented in an approved implementation plan, AND (2) the user has explicitly typed "Proceed", "Approved", or "Approve plan" in the conversation history of the current turn sequence. An authorization keyword alone is NOT sufficient. See `.agents/AGENTS.md` § Strict Planning Gate, which takes precedence, and `rules/user-authorization-lock.md` § Precedence.

### Rationale

Issue #295 found three documents stating three different rules for what authorizes a
file write. This sentence and `rules/user-authorization-lock.md:9` both treated an
authorization keyword as sufficient, while `.agents/AGENTS.md:7` states explicitly that
a keyword is **not** sufficient without an approved implementation plan.

The decisive defect was reading order: `rules/constitution-first.md` enumerated the
mandatory reads without listing `.agents/AGENTS.md`, and `.agents/` is a hidden
directory that glob and ripgrep skip. An agent complying fully with constitution-first
therefore read only the two keyword-sufficient documents and never saw the strictest
rule. That is exactly what happened during this session: two commits reached `main`
before `AGENTS.md` was discovered.

#295 unified on the strictest reading, on the grounds that under-authorizing costs one
redundant question whereas over-authorizing causes unapproved writes. This amendment
brings the Tier 1 document into agreement with that resolution, so the highest-authority
statement is no longer the weakest.

**This amendment tightens a constraint on the agent.** It removes an authorization path
the agent previously had, and adds no capability.

Non-destructive: no principle is removed. Condition (2) preserves the original clause
verbatim, and condition (1) is added alongside it.

---

## AMEND-0003 — Standardize product name to Digital Engineering Agentic Pipeline (DEAP)

- **Date:** 2026-08-06
- **Logged:** 2026-08-06
- **Motivating issue:** n/a — product name standardization across repository
- **Approved by:** "PROCEED" — approved implementation plan to standardize official product name to Digital Engineering Agentic Pipeline (DEAP).
- **Destructive:** no
- **Line count:** 161
- **Resulting SHA-256:** `952397210c5163672e05bac9b1afcaa1351522e2ad6a3c18c09525cdc6cae896`

### Change

Frontmatter line 3 and main title line 9.

Before:

> project: "Digital Systems Engineering Pipeline"
> # Project Constitution: Digital Systems Engineering Pipeline

After:

> project: "Digital Engineering Agentic Pipeline (DEAP)"
> # Project Constitution: Digital Engineering Agentic Pipeline (DEAP)

### Rationale

Standardize the official product name to Digital Engineering Agentic Pipeline (DEAP) across the repository in accordance with the approved implementation plan.

Non-destructive: product name updated, governance rules unchanged.

