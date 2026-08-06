"""Regression tests for issue #285.

``spec-orchestrator/SKILL.md`` invoked the linter through the repository-relative
``skills/`` prefix and ``create_issue.sh`` through ``.agents/skills/`` — in the same
sentence. Both resolved only because ``.agents/skills`` is a git-tracked symlink
(mode 120000) pointing at ``../skills``.

Nothing was broken at the time of filing, so this was drift risk rather than an
active defect. But the failure mode is asymmetric and confusing: if the symlink is
ever not materialised — archive extraction, ``core.symlinks=false``, a filesystem
without symlink support — the linter call on a given line still succeeds while the
``create_issue.sh`` call on the same line fails, pointing debugging at issue
creation rather than at path resolution.

The second test here is the stronger one: rather than only banning a prefix, it
asserts that every ``skills/...`` path mentioned in a governance document actually
resolves on disk. That catches dangling references generally, not just this one.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# `.agents` and `.pipeline` are hidden, and were omitted here until issue #305. The
# omission was self-defeating: the prefix ban below exists to keep `.agents/skills/`
# out of governance documents, and the only document using that prefix lived in the
# one directory this scan skipped. The test was green because it could not see its
# own subject. Same root cause as #295 — hidden directories dropped by
# convention-based enumeration — with a test doing the skipping rather than an agent.
#
# os.walk does not follow symlinks by default, so `.agents/skills -> ../skills` is
# not descended into and `skills/` documents are not counted twice.
SCAN_ROOTS = ("skills", "rules", ".agents", ".pipeline")
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "decisions",
    "designs",
    "diagnostics",  # .pipeline/diagnostics holds ~78 repro payloads, none of them .md
}

# Paths appearing inside prose as examples of the *wrong* form are allowed only in
# documents that exist to explain the convention.
ALLOWED_AGENTS_PREFIX = {
    # The normative statement of the rule has to quote the prohibited form in order to
    # prohibit it (#310). Exempting the rule's own home is the narrowest fix; exempting
    # by pattern, or weakening the scan, would reopen the #305 blind spot.
    "rules/document-references.md",
}


def _governance_docs():
    found = []
    for base in SCAN_ROOTS:
        root = os.path.join(REPO_ROOT, base)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
            for name in filenames:
                if name.endswith(".md"):
                    found.append(os.path.join(dirpath, name))
    return found


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def test_governance_docs_are_discoverable():
    """Guard: every assertion below iterates this corpus.

    The count alone is a weak guard — it cleared comfortably on ``skills/`` and
    ``rules/`` alone while the hidden roots were missing entirely (#305). The
    membership assertions are the real check: they name one document from each hidden
    root, so dropping a scan root fails here loudly instead of silently shrinking
    what the suite examines.
    """
    docs = _governance_docs()
    rels = {os.path.relpath(p, REPO_ROOT) for p in docs}

    assert len(docs) >= 28, (
        f"expected the skill, rule and hidden governance documents, found {len(docs)}"
    )
    for required in (".agents/AGENTS.md", ".pipeline/constitution.md"):
        assert required in rels, (
            f"{required} is missing from the scanned corpus — a SCAN_ROOTS regression. "
            "This is the #305 blind spot; do not fix it by lowering the guard."
        )


def test_no_document_uses_the_agents_skills_prefix_issue285():
    offenders = []
    for path in _governance_docs():
        rel = os.path.relpath(path, REPO_ROOT)
        if rel in ALLOWED_AGENTS_PREFIX:
            continue
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if ".agents/skills" in line:
                offenders.append(f"{rel}:{lineno}")
    assert not offenders, (
        "documents reference paths through the '.agents/skills/' symlink. Use the "
        "repository-relative 'skills/' prefix so resolution does not depend on the "
        f"symlink being materialised: {offenders}"
    )


def test_referenced_skill_paths_resolve_on_disk_issue285():
    """The real invariant: a path named in a governance document must exist."""
    # Most references are written './skills/...', so the leading './' must be
    # accepted and then normalised away. A lookbehind rejecting '.' or '/' matched
    # almost nothing and the vacuity guard below caught it.
    pattern = re.compile(r"(?<![\w-])((?:\./)?(?:\.agents/)?skills/[A-Za-z0-9_./-]+)")
    offenders = []
    checked = 0
    for path in _governance_docs():
        rel = os.path.relpath(path, REPO_ROOT)
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            for match in pattern.finditer(line):
                candidate = match.group(1).rstrip(".,;:)`\"'")
                if candidate.startswith("./"):
                    candidate = candidate[2:]
                # skip glob/placeholder forms that cannot be resolved literally
                if any(ch in candidate for ch in "<>*[]") or candidate.endswith("/"):
                    continue
                if "spec-orchestrator/scripts" in candidate or candidate.endswith(
                    (".md", ".py", ".sh", ".json")
                ):
                    checked += 1
                    if not os.path.exists(os.path.join(REPO_ROOT, candidate)):
                        offenders.append(f"{rel}:{lineno} -> {candidate}")
    assert checked >= 10, (
        f"only {checked} concrete skill paths examined; the scan is close to vacuous"
    )
    assert not offenders, f"governance documents reference paths that do not exist: {offenders}"


# A cross-document step citation, in the two forms the corpus actually uses. Anaphoric
# references ("Step 9 of that skill") carry no resolvable name and are skipped by the
# skills/<name>/SKILL.md existence check below rather than by a special case.
_CITE_NAME_THEN_STEP = re.compile(r"`([a-z0-9-]+)`[^.`]{0,40}?Step (\d+(?:\.\d+)?)")
_CITE_STEP_THEN_NAME = re.compile(r"Step (\d+(?:\.\d+)?) of `?([a-z0-9-]+)`?")


def _cited_steps():
    """(citing_doc, skill_name, step) for every resolvable cross-document citation."""
    found = []
    for path in _governance_docs():
        rel = os.path.relpath(path, REPO_ROOT)
        # Citations wrap across lines in pipeline-tooling.md, so scan the whole text
        # with newlines flattened rather than line by line.
        text = " ".join(_read(path).splitlines())
        for name, step in _CITE_NAME_THEN_STEP.findall(text):
            found.append((rel, name, step))
        for step, name in _CITE_STEP_THEN_NAME.findall(text):
            found.append((rel, name, step))
    return found


def test_step_citations_resolve_issue307():
    """A document citing another document's Step N must cite a step that exists.

    ``pipeline-tooling.md`` claimed to override ``feature-driven-implementation``
    "Step 5.5". There is no Step 5.5; the closure instructions are Step 5 item 5 and
    Step 6 item 2. A reader checking whether the override actually covers the
    offending text could not locate the target, and Step 6 went unmentioned, so on a
    literal reading the override did not reach the Epic closure at all.
    """
    offenders = []
    checked = 0
    for rel, name, step in _cited_steps():
        target = os.path.join(REPO_ROOT, "skills", name, "SKILL.md")
        if not os.path.exists(target):
            continue  # not a skill reference, or anaphoric — nothing to resolve
        checked += 1
        heading = re.compile(
            r"^#{1,6}\s*Step\s+" + re.escape(step) + r"\b", re.MULTILINE
        )
        if not heading.search(_read(target)):
            offenders.append(f"{rel} cites `{name}` Step {step}, which has no heading")

    assert checked >= 4, (
        f"only {checked} cross-document step citations examined; the scan is near-vacuous"
    )
    assert not offenders, f"governance documents cite steps that do not exist: {offenders}"


# A concrete subagent dispatch/lifecycle tool identifier: an action verb joined to
# "subagent". The verb prefix is what distinguishes a dispatch tool from an incidental
# compound — `browser_subagent` in rules/no-browser-automation.md is named in order to be
# *prohibited*, and a prohibition that stops matching the runtime goes inert rather than
# unexecutable, so it is deliberately out of scope.
_DISPATCH_TOOL = re.compile(
    r"`((?:invoke|dispatch|spawn|launch|create|manage|run|start|stop|terminate|kill|"
    r"reclaim|list)_[a-z0-9_]*sub_?agents?[a-z0-9_]*)`"
)


def test_no_document_names_a_runtime_dispatch_tool_issue312():
    """A normative directive must name the capability, not the tool. Issue #312.

    ``.agents/AGENTS.md`` and ``rules/user-authorization-lock.md`` both state this, each
    scoped to its own file, so nothing covered ``skills/`` and the #312 sweep left
    ``feature-driven-implementation/SKILL.md`` still directing the coordinator at a tool
    that does not exist in this runtime. An agent meeting an unexecutable directive does
    not halt — it does the work itself, which is the failure #312 records.

    The per-runtime dispatch table in ``.agents/AGENTS.md`` is the sanctioned home for
    concrete names, so table rows there are exempt; that is the one place a change of
    runtime is meant to be reflected.
    """
    offenders = []
    for path in _governance_docs():
        rel = os.path.relpath(path, REPO_ROOT)
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if rel == ".agents/AGENTS.md" and line.lstrip().startswith("|"):
                continue  # the per-runtime dispatch table
            for name in _DISPATCH_TOOL.findall(line):
                offenders.append(f"{rel}:{lineno} -> {name}")

    # Vacuity guard. The scan matches nothing once the corpus is clean, so a broken
    # regex and a compliant corpus look identical. Prove the pattern still recognises
    # the two names issue #312 removed, and that the corpus was actually read.
    assert _DISPATCH_TOOL.findall("use `invoke_subagent` and `manage_subagents`") == [
        "invoke_subagent",
        "manage_subagents",
    ], "the dispatch-tool pattern no longer matches the names issue #312 removed"
    assert len(_governance_docs()) >= 28, "governance corpus not scanned"

    assert not offenders, (
        "governance documents name concrete dispatch tools: "
        f"{offenders}. State the capability required and point at the per-runtime "
        "dispatch table in .agents/AGENTS.md, so a change of runtime cannot make the "
        "sentence unexecutable."
    )
