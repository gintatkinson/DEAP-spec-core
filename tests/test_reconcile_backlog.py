import sys
import os
import pytest

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/spec-orchestrator/scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import rewrite_header_repository_urls, sanitize_source_references


def test_rewrite_header_repository_urls_preserves_external_urls():
    content = (
        "# Feature 03: External References\n\n"
        "- **Target Spec Link**: https://github.com/legacy-owner/digital-pipeline-repo/blob/main/docs/epics/epic-01.md\n"
        "- **Active Repo Link**: https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/features/feat-01.md\n"
        "- **YANG Models External**: https://github.com/YangModels/yang/blob/master/standard/ietf/RFC/ietf-interfaces.yang\n"
        "- **IETF WG External**: https://github.com/ietf-wg/cellar/blob/main/spec.md\n"
        "- **Other External Org**: https://github.com/ietf-ivy-wg/network-inventory-yang/blob/main/ietf-network-inventory.yang\n"
        "- **User External Org**: https://github.com/aguoietf/yang/blob/master/experimental/ietf-extracted-YANG-modules/ietf-network-slice.yang\n"
    )

    active_repo = "gintatkinson/digital-pipeline-repo"
    rewritten = rewrite_header_repository_urls(content, active_repo)

    # Active repo / target repo links should be pointing to active_repo
    assert "https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/epics/epic-01.md" in rewritten
    assert "https://github.com/gintatkinson/digital-pipeline-repo/blob/main/docs/features/feat-01.md" in rewritten

    # External org / repo URLs MUST remain untouched
    assert "https://github.com/YangModels/yang/blob/master/standard/ietf/RFC/ietf-interfaces.yang" in rewritten
    assert "https://github.com/ietf-wg/cellar/blob/main/spec.md" in rewritten
    assert "https://github.com/ietf-ivy-wg/network-inventory-yang/blob/main/ietf-network-inventory.yang" in rewritten
    assert "https://github.com/aguoietf/yang/blob/master/experimental/ietf-extracted-YANG-modules/ietf-network-slice.yang" in rewritten


def test_rewrite_header_repository_urls_rewrites_legacy_target_repo_urls():
    content = (
        "- **Legacy Link**: https://github.com/legacy-user/digital-pipeline-repo/blob/master/docs/features/feat-02.md\n"
        "- **External Link**: https://github.com/YangModels/yang/blob/master/README.md\n"
    )

    active_repo = "my-org/digital-pipeline-repo"
    rewritten = rewrite_header_repository_urls(content, active_repo)

    assert "https://github.com/my-org/digital-pipeline-repo/blob/master/docs/features/feat-02.md" in rewritten
    assert "https://github.com/YangModels/yang/blob/master/README.md" in rewritten
