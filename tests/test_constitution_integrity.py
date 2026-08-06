"""Integrity gate for the constitution amendment protocol.

The constitution is the Tier 1 governing document, yet before this gate existed it had
a weaker change process than the Tier 2 implementation profiles: profiles had a full
add/update/remove/list lifecycle, the constitution had one sentence. The result was
that the safe default became refusal, and two known defects stayed unfixed because
there was no described way to amend it safely.

This makes the audit trail mandatory rather than aspirational. The checksum of
``.pipeline/constitution.md`` must match the newest entry in
``.pipeline/constitution-amendments.md``, so **any** unlogged edit — by a human, by an
agent, or by a merge — fails the suite.

That is a deliberate trade. Allowing an agent to amend the constitution reduces a
safety property; making every change attributable and detectable is what makes the
reduction acceptable.
"""

import hashlib
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONSTITUTION = os.path.join(REPO_ROOT, ".pipeline", "constitution.md")
AMENDMENT_LOG = os.path.join(REPO_ROOT, ".pipeline", "constitution-amendments.md")

REQUIRED_FIELDS = (
    "Date", "Logged", "Motivating issue", "Approved by",
    "Destructive", "Line count", "Resulting SHA-256",
)


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _entries():
    """Parse amendment entries in file order. Returns a list of (id, fields, body)."""
    content = _read(AMENDMENT_LOG)
    chunks = re.split(r"^## AMEND-(\d+)", content, flags=re.M)[1:]
    parsed = []
    for i in range(0, len(chunks), 2):
        amend_id, body = chunks[i], chunks[i + 1]
        fields = {}
        for name in REQUIRED_FIELDS:
            m = re.search(
                rf"^- \*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", body, re.M
            )
            if m:
                fields[name] = m.group(1).strip().strip("`")
        parsed.append((amend_id, fields, body))
    return parsed


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

def test_constitution_and_log_both_exist():
    assert os.path.isfile(CONSTITUTION), f"missing {CONSTITUTION}"
    assert os.path.isfile(AMENDMENT_LOG), (
        f"missing {AMENDMENT_LOG}. The constitution may not be changed without an "
        "amendment log to record it."
    )


def test_log_contains_at_least_the_baseline_entry():
    entries = _entries()
    assert entries, (
        "no AMEND-nnnn entries parsed from the amendment log; the checksum assertion "
        "below would be vacuous"
    )


# --------------------------------------------------------------------------- #
# The core assertion: no unlogged change
# --------------------------------------------------------------------------- #

def test_constitution_checksum_matches_newest_amendment():
    entries = _entries()
    amend_id, fields, _ = entries[-1]
    logged = fields.get("Resulting SHA-256")
    actual = _sha256(CONSTITUTION)
    assert logged, f"AMEND-{amend_id} has no 'Resulting SHA-256' field"
    assert logged == actual, (
        f"constitution.md has been modified without a logged amendment.\n"
        f"  newest log entry : AMEND-{amend_id} -> {logged}\n"
        f"  file on disk     : {actual}\n"
        "Append an entry via project-constitution Step 9, recording the motivating "
        "issue and the verbatim human approval, or revert the edit."
    )


# --------------------------------------------------------------------------- #
# Entry completeness and provenance
# --------------------------------------------------------------------------- #

def test_every_entry_carries_all_required_fields():
    problems = []
    for amend_id, fields, _ in _entries():
        for name in REQUIRED_FIELDS:
            if name not in fields:
                problems.append(f"AMEND-{amend_id} missing '{name}'")
    assert not problems, (
        "amendment entries are incomplete, so the trail is not auditable: " + str(problems)
    )


def test_every_entry_records_approval_provenance():
    """An amendment without recorded approval is indistinguishable from an unapproved one."""
    problems = []
    for amend_id, fields, _ in _entries():
        approved = fields.get("Approved by", "")
        if not approved:
            problems.append(f"AMEND-{amend_id}: empty")
        elif approved.startswith("n/a") and len(approved) < 12:
            problems.append(f"AMEND-{amend_id}: 'n/a' without a stated reason")
    assert not problems, f"entries lacking approval provenance: {problems}"


def test_last_updated_matches_the_newest_amendment_date():
    _, fields, _ = _entries()[-1]
    m = re.search(r'^last_updated:\s*"?([^"\n]+)"?', _read(CONSTITUTION), re.M)
    assert m, "constitution frontmatter has no last_updated field"
    assert m.group(1).strip() == fields.get("Date"), (
        f"constitution last_updated is {m.group(1).strip()!r} but the newest amendment "
        f"records Date {fields.get('Date')!r}. Bump last_updated when amending."
    )


# --------------------------------------------------------------------------- #
# Cumulative, never destructive (project-constitution Mandate 3)
# --------------------------------------------------------------------------- #

def test_non_destructive_amendments_do_not_shrink_the_constitution():
    entries = _entries()
    problems = []
    previous = None
    for amend_id, fields, body in entries:
        try:
            count = int(fields.get("Line count", "").split()[0])
        except (ValueError, IndexError):
            problems.append(f"AMEND-{amend_id}: unparseable Line count")
            continue
        destructive = fields.get("Destructive", "").lower().startswith("yes")
        if previous is not None and not destructive and count < previous:
            problems.append(
                f"AMEND-{amend_id}: line count fell {previous} -> {count} but is not "
                "flagged Destructive. Mandate 3 requires amendments to be cumulative."
            )
        if destructive and len(body.strip()) < 200:
            problems.append(
                f"AMEND-{amend_id}: flagged Destructive without a justification "
                "paragraph explaining what was removed and why"
            )
        previous = count
    assert not problems, str(problems)


def test_current_line_count_matches_newest_entry():
    _, fields, _ = _entries()[-1]
    actual = len(_read(CONSTITUTION).splitlines())
    assert str(actual) == fields.get("Line count"), (
        f"constitution has {actual} lines but the newest amendment records "
        f"{fields.get('Line count')!r}"
    )
