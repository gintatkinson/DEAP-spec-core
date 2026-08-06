"""``FAMILIES`` must be bound exactly once in ``tests/rule_contracts.py``.

The registry was written with two module-level ``FAMILIES`` assignments. The second
shadowed the first, and it omitted ``DOC_REFERENCE_FAMILY``. Because ``ALL_CONTRACTS``
is derived from ``FAMILIES``, the three ``doc-ref-*`` contracts registered for issue
#310 were never parametrized into a single assertion — while the suite reported green.

That is the registry failing its own premise. ``rule_contracts.py`` exists to detect a
documented contract diverging from an enforced one (#298); here the registry documented
four families and enforced three, and nothing noticed, because the defect lived in the
detector rather than in what it detects.

A count of contracts or families would not have caught it: both counts were internally
consistent after the shadowing. The observable fact is textual — two bindings of one
name — so this test reads the module source. It deliberately does not import the module
and inspect ``FAMILIES``, because a shadowed binding is indistinguishable from a single
correct one at runtime, which is precisely why the defect survived.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGISTRY = os.path.join(REPO_ROOT, "tests", "rule_contracts.py")

_BINDING = re.compile(r"^FAMILIES\b", re.MULTILINE)


def _source():
    with open(REGISTRY, "r", encoding="utf-8") as fh:
        return fh.read()


def test_registry_module_is_present():
    """Fixture guard: every assertion below reads this one file."""
    assert os.path.isfile(REGISTRY), (
        f"{REGISTRY} is missing; the assertions below would pass vacuously"
    )
    source = _source()
    assert "ContractFamily" in source and "ALL_CONTRACTS" in source, (
        "rule_contracts.py does not look like the contract registry; this test is "
        "reading the wrong file"
    )


def test_families_is_bound_exactly_once():
    lines = [
        f"{n}: {line}"
        for n, line in enumerate(_source().splitlines(), 1)
        if _BINDING.match(line)
    ]
    assert len(lines) == 1, (
        f"FAMILIES is bound {len(lines)} times in tests/rule_contracts.py. A later "
        "binding shadows an earlier one, silently dropping every family the last "
        "binding omits from ALL_CONTRACTS and from every parametrized assertion — "
        "which is how DOC_REFERENCE_FAMILY went unasserted from #310 until #312. "
        f"Bindings found: {lines}"
    )


def test_every_defined_family_is_listed_in_families():
    """The complementary invariant: one binding that is also complete.

    Collapsing to a single binding removes the shadowing but not the underlying risk —
    a family could still be defined and left out of the list. This compares the module's
    ``ContractFamily`` instances against the contents of ``FAMILIES``.
    """
    import sys

    tests_dir = os.path.join(REPO_ROOT, "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    import rule_contracts

    from rule_contracts import ContractFamily, FAMILIES

    defined = {
        name
        for name, value in vars(rule_contracts).items()
        if isinstance(value, ContractFamily)
    }
    assert defined, "no ContractFamily instances found; this assertion would be vacuous"

    listed = {f.name for f in FAMILIES}
    missing = sorted(
        name
        for name in defined
        if getattr(rule_contracts, name).name not in listed
    )
    assert not missing, (
        f"ContractFamily instances defined but absent from FAMILIES: {missing}. An "
        "unlisted family contributes nothing to ALL_CONTRACTS, so its contracts are "
        "registered on paper and asserted nowhere."
    )
