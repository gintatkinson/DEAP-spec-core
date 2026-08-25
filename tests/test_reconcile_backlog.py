import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add scripts directory to sys.path
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from reconcile_backlog import (
    expand_relative_links_for_tracker,
    sync_issue_body_to_tracker,
    get_blob_url_base,
)


class TestExpandRelativeLinksForTracker(unittest.TestCase):
    def setUp(self):
        self.workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.github_rules = {
            "meta": {"upstream_repository": "gintatkinson/DEAP-spec-core"},
            "tracker_rules": {"provider": "github"}
        }
        self.gitlab_rules = {
            "meta": {"upstream_repository": "gintatkinson/DEAP-spec-core"},
            "tracker_rules": {"provider": "gitlab"}
        }

    def test_expand_relative_links_github(self):
        content = (
            "# Feature Spec\n\n"
            "See [Rule](rules/sysml-ssot-completeness.md) and "
            "[Doc](docs/architecture/blueprints/DEAP_MODEL.sysml).\n"
            "Parent: [Epic 1](../epics/epic-01.md)\n"
            "Anchor: [Section](../features/feat-02.md#acceptance-criteria)\n"
        )
        spec_path = os.path.join(self.workspace_dir, "docs", "features", "feat-01.md")
        with patch("reconcile_backlog.get_current_branch", return_value="main"):
            expanded = expand_relative_links_for_tracker(
                content,
                filepath=spec_path,
                rules=self.github_rules,
                workspace_dir=self.workspace_dir
            )

        self.assertIn(
            "[Rule](https://github.com/gintatkinson/DEAP-spec-core/blob/main/rules/sysml-ssot-completeness.md)",
            expanded
        )
        self.assertIn(
            "[Doc](https://github.com/gintatkinson/DEAP-spec-core/blob/main/docs/architecture/blueprints/DEAP_MODEL.sysml)",
            expanded
        )
        self.assertIn(
            "[Epic 1](https://github.com/gintatkinson/DEAP-spec-core/blob/main/docs/epics/epic-01.md)",
            expanded
        )
        self.assertIn(
            "[Section](https://github.com/gintatkinson/DEAP-spec-core/blob/main/docs/features/feat-02.md#acceptance-criteria)",
            expanded
        )

    def test_expand_relative_links_gitlab(self):
        content = (
            "See [Rule](rules/sysml-ssot-completeness.md) and "
            "[Parent Epic](../epics/epic-01.md)."
        )
        spec_path = os.path.join(self.workspace_dir, "docs", "features", "feat-01.md")
        with patch("reconcile_backlog.get_current_branch", return_value="main"):
            expanded = expand_relative_links_for_tracker(
                content,
                filepath=spec_path,
                rules=self.gitlab_rules,
                workspace_dir=self.workspace_dir
            )

        self.assertIn(
            "[Rule](https://gitlab.com/gintatkinson/DEAP-spec-core/-/blob/main/rules/sysml-ssot-completeness.md)",
            expanded
        )
        self.assertIn(
            "[Parent Epic](https://gitlab.com/gintatkinson/DEAP-spec-core/-/blob/main/docs/epics/epic-01.md)",
            expanded
        )

    def test_expand_relative_links_preserves_absolute_and_special_links(self):
        content = (
            "External: [GitHub](https://github.com/org/repo)\n"
            "Insecure: [HTTP](http://example.com/spec)\n"
            "Mail: [Contact](mailto:dev@example.com)\n"
            "Anchor only: [Internal Link](#section-1)\n"
        )
        spec_path = os.path.join(self.workspace_dir, "docs", "features", "feat-01.md")
        with patch("reconcile_backlog.get_current_branch", return_value="main"):
            expanded = expand_relative_links_for_tracker(
                content,
                filepath=spec_path,
                rules=self.github_rules,
                workspace_dir=self.workspace_dir
            )

        self.assertIn("[GitHub](https://github.com/org/repo)", expanded)
        self.assertIn("[HTTP](http://example.com/spec)", expanded)
        self.assertIn("[Contact](mailto:dev@example.com)", expanded)
        self.assertIn("[Internal Link](#section-1)", expanded)

    def test_sync_issue_body_to_tracker_expands_relative_links(self):
        spec_content = (
            "---\ntitle: Feature One\ntype: feature\n---\n\n"
            "# Feature: Feature One\n\n"
            "## Requirements\n"
            "See [Rule](rules/sysml-ssot-completeness.md) and [Parent](../epics/epic-01.md).\n"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tf:
            tf.write(spec_content)
            temp_path = tf.name

        try:
            mock_provider = MagicMock()
            mock_provider.edit_issue.return_value = True
            mock_provider.edit_issue_title.return_value = True
            mock_provider.add_label.return_value = True

            with patch("reconcile_backlog.get_current_branch", return_value="main"):
                sync_issue_body_to_tracker(
                    issue_num=101,
                    filepath=temp_path,
                    issue_type="Feature",
                    rules=self.github_rules,
                    provider_adapter=mock_provider
                )

            mock_provider.edit_issue.assert_called_once()
            called_content = mock_provider.edit_issue.call_args[0][1]
            self.assertIn(
                "https://github.com/gintatkinson/DEAP-spec-core/blob/main/rules/sysml-ssot-completeness.md",
                called_content
            )
            self.assertIn(
                "https://github.com/gintatkinson/DEAP-spec-core/blob/main/docs/epics/epic-01.md",
                called_content
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
