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
# Layer 2 -- Turnkey installer must exclude upstream-only profile
# --------------------------------------------------------------------------- #

def test_installer_excludes_the_upstream_dir():
    installer = _read(os.path.join(REPO_ROOT, "scripts", "install_pipeline.sh"))
    assert 'exclude="./upstream"' in installer or 'tar --exclude="./upstream"' in installer, (
        "install_pipeline.sh must exclude ./upstream when copying .pipeline, "
        "or the upstream-only profile ships downstream"
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
