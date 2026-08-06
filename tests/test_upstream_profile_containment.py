"""Containment tests for the upstream-only pipeline-tooling profile.

The pipeline repository is consumed as a template. README "Direct Copy
Installation" performs ``cp -RP ./.tmp-pipeline/.pipeline ./``, a wholesale
recursive copy, and the GitHub template route copies the whole tree. Anything
placed under ``.pipeline/profiles/`` therefore ships into every downstream
project.

The pipeline-tooling profile governs *this* repository's own Python and
Markdown tooling and is meaningless -- actively misleading -- downstream. These
tests pin the containment so a future edit cannot silently reintroduce the leak.

Prose exclusions rot. This is the enforcement layer.
"""

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPSTREAM_DIR = os.path.join(REPO_ROOT, ".pipeline", "upstream")
PROFILE = os.path.join(UPSTREAM_DIR, "pipeline-tooling.md")
PROFILES_DIR = os.path.join(REPO_ROOT, ".pipeline", "profiles")
GITATTRIBUTES = os.path.join(REPO_ROOT, ".gitattributes")
README = os.path.join(REPO_ROOT, "README.md")


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Layer 1 -- location outside .pipeline/profiles/
# --------------------------------------------------------------------------- #

def test_profile_exists_in_upstream_dir():
    assert os.path.isfile(PROFILE), (
        f"upstream-only profile missing at {PROFILE}"
    )


def test_profile_declares_upstream_only_scope():
    assert re.search(r"^scope:\s*upstream-only\s*$", _read(PROFILE), re.M), (
        "profile frontmatter must declare 'scope: upstream-only' so its status "
        "is machine-detectable, not merely stated in prose"
    )


def test_profile_is_not_in_the_downstream_profiles_dir():
    """`ls .pipeline/profiles/` is the documented profile-discovery command.

    Keeping the upstream profile out of that directory means a downstream agent
    listing available platforms never sees it and cannot adopt it by accident.
    """
    if not os.path.isdir(PROFILES_DIR):
        return
    stray = [n for n in os.listdir(PROFILES_DIR) if "pipeline-tooling" in n]
    assert not stray, (
        f"pipeline-tooling profile must not live in .pipeline/profiles/ "
        f"(found {stray}); it would be surfaced to downstream projects"
    )


# --------------------------------------------------------------------------- #
# Layer 2 -- README Direct Copy must delete it
# --------------------------------------------------------------------------- #

def test_readme_direct_copy_deletes_the_upstream_dir():
    readme = _read(README)
    assert "cp -RP ./.tmp-pipeline/.pipeline ./" in readme, (
        "README Direct Copy block no longer copies .pipeline as expected; "
        "this test's assumption about the leak vector needs revisiting"
    )
    assert re.search(r"rm -rf \./\.pipeline/upstream", readme), (
        "README Direct Copy Installation must remove ./.pipeline/upstream after "
        "copying .pipeline, or the upstream-only profile ships downstream"
    )


def test_readme_deletion_comes_after_the_pipeline_copy():
    readme = _read(README)
    copy_at = readme.index("cp -RP ./.tmp-pipeline/.pipeline ./")
    rm_match = re.search(r"rm -rf \./\.pipeline/upstream", readme)
    assert rm_match and rm_match.start() > copy_at, (
        "the 'rm -rf ./.pipeline/upstream' must appear AFTER the .pipeline copy, "
        "otherwise the copy reinstates what was deleted"
    )


# --------------------------------------------------------------------------- #
# Layer 3 -- git archive / export paths
# --------------------------------------------------------------------------- #

def test_gitattributes_marks_upstream_dir_export_ignore():
    assert os.path.isfile(GITATTRIBUTES), (
        f"{GITATTRIBUTES} missing; needed to exclude upstream-only content from "
        "git archive and release tarballs"
    )
    content = _read(GITATTRIBUTES)
    assert re.search(r"^\.pipeline/upstream/?\s+export-ignore\s*$", content, re.M), (
        "'.pipeline/upstream/ export-ignore' must be declared in .gitattributes"
    )
