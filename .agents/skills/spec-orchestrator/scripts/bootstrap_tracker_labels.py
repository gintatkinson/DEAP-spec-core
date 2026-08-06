#!/usr/bin/env python3
# Copyright Gint Atkinson, gint.atkinson@gmail.com
"""Provision the full tracker label taxonomy at install time (issue #323).

Labels were created just-in-time: `create_issue.sh` made a label at the moment the
first issue of that type was filed. They did arrive eventually, but a freshly installed
downstream repository showed an empty "Filter by labels" dropdown until an orchestrator
run had filed at least one issue of every type — and a partial run left it showing
`user-story` alone, which reads as a broken installation rather than an incomplete one.

The taxonomy is known at install time. There is no reason to discover it lazily.

This does not replace the just-in-time path in `create_issue.sh`, deliberately. That
path is idempotent and remains the safety net for a repository provisioned before this
script existed, or one where a label was deleted by hand. Removing it would trade a
cosmetic defect for a functional one.

Label names are read from `tracker_rules.labels` in the runtime configuration rather
than hardcoded, so a downstream project that renames its taxonomy gets its own names
provisioned. `--force` makes every creation idempotent, so re-running is safe and is
the intended way to repair a tracker whose labels were removed.

Usage:
    python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py [--repo OWNER/NAME]
"""

import argparse
import json
import os
import subprocess
import sys

# Presentation only. A label absent from this map is still provisioned, with the
# tracker's default colour — the taxonomy is authoritative, not this table.
LABEL_PRESENTATION = {
    "epic": ("800080", "Epic: a major functional domain or protocol module"),
    "feature": ("0366d6", "Feature: a single independently testable capability"),
    "user_story": ("0e8a16", "User Story: a BDD behavioural scenario"),
    "use_case": ("fbca04", "Use Case: a formal UML system interaction"),
    "resolved": (
        "0e8a16",
        "Dev complete, tests pass, merged to main. Awaiting Product Owner validation.",
    ),
}


def find_workspace_dir(start):
    """Walk up until the runtime configuration is found."""
    current = os.path.abspath(start)
    while True:
        if os.path.exists(
            os.path.join(current, ".pipeline", "logical-ui", "codebase_rules.json")
        ):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(start)
        current = parent


def load_labels(workspace_dir):
    """The configured taxonomy, or the built-in default if none is declared."""
    path = os.path.join(
        workspace_dir, ".pipeline", "logical-ui", "codebase_rules.json"
    )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rules = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"FATAL: could not read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    labels = rules.get("tracker_rules", {}).get("labels", {})
    if not labels:
        print(
            "FATAL: tracker_rules.labels is empty in codebase_rules.json. The taxonomy "
            "is configuration, not a constant, so there is nothing to provision.",
            file=sys.stderr,
        )
        sys.exit(1)
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Target repository as OWNER/NAME")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the commands without executing them",
    )
    args = parser.parse_args()

    workspace_dir = find_workspace_dir(os.path.dirname(os.path.abspath(__file__)))
    labels = load_labels(workspace_dir)

    print(f"Provisioning {len(labels)} tracker labels from tracker_rules.labels...")
    failures = []
    for key, name in sorted(labels.items()):
        colour, description = LABEL_PRESENTATION.get(key, ("ededed", str(key)))
        cmd = ["gh", "label", "create", name,
               "--color", colour, "--description", description, "--force"]
        if args.repo:
            cmd += ["--repo", args.repo]

        if args.dry_run:
            print("  [dry-run] " + " ".join(cmd))
            continue

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  [ok] {name}")
        else:
            failures.append((name, (result.stderr or "").strip()))
            print(f"  [FAILED] {name}: {(result.stderr or '').strip()}", file=sys.stderr)

    if failures:
        print(
            f"\n{len(failures)} label(s) could not be provisioned. The just-in-time "
            "path in create_issue.sh remains as a fallback, so filing still works — "
            "but the tracker's label filter will stay incomplete until this succeeds.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.dry_run:
        print("Tracker label taxonomy provisioned.")


if __name__ == "__main__":
    main()
