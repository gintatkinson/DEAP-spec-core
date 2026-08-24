import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add scripts directory to sys.path
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from reconcile_backlog import (
    GitLabV4Provider,
    GitHubCLIProvider,
    parse_git_remote_url,
    detect_tracker_provider,
    load_codebase_rules,
    get_structural_label,
    get_resolved_label,
    create_tracker_provider,
    DEFAULT_GITLAB_TRACKER_RULES,
    DEFAULT_GITLAB_STRUCTURAL_LABELS,
)


class TestGitLabRemoteParser(unittest.TestCase):
    def test_parse_https_url(self):
        url = "https://gitlab.com/gintatkinson/DEAP-spec-core.git"
        info = parse_git_remote_url(url)
        self.assertTrue(info["is_gitlab"])
        self.assertEqual(info["project_path"], "gintatkinson/DEAP-spec-core")
        self.assertEqual(info["server_url"], "https://gitlab.com")
        self.assertEqual(info["host"], "gitlab.com")

    def test_parse_custom_gitlab_domain(self):
        url = "https://gitlab.internal.corp/safety-team/uas/uas-core.git"
        info = parse_git_remote_url(url)
        self.assertTrue(info["is_gitlab"])
        self.assertEqual(info["project_path"], "safety-team/uas/uas-core")
        self.assertEqual(info["server_url"], "https://gitlab.internal.corp")
        self.assertEqual(info["host"], "gitlab.internal.corp")

    def test_parse_ssh_scp_style(self):
        url = "git@gitlab.com:gintatkinson/DEAP-spec-core.git"
        info = parse_git_remote_url(url)
        self.assertTrue(info["is_gitlab"])
        self.assertEqual(info["project_path"], "gintatkinson/DEAP-spec-core")
        self.assertEqual(info["server_url"], "https://gitlab.com")

    def test_parse_github_url(self):
        url = "https://github.com/gintatkinson/digital-pipeline-repo.git"
        info = parse_git_remote_url(url)
        self.assertFalse(info["is_gitlab"])
        self.assertEqual(info["project_path"], "gintatkinson/digital-pipeline-repo")
        self.assertEqual(info["server_url"], "https://github.com")


class TestGitLabProviderResolution(unittest.TestCase):
    @patch.dict(os.environ, {
        "GITLAB_URL": "https://gitlab.example.com",
        "CI_PROJECT_PATH": "my-org/my-project",
        "GITLAB_TOKEN": "glpat-testtoken123"
    }, clear=True)
    def test_env_resolution(self):
        provider = GitLabV4Provider()
        self.assertEqual(provider.server_url, "https://gitlab.example.com")
        self.assertEqual(provider.raw_project_id, "my-org/my-project")
        self.assertEqual(provider.project_id_encoded, "my-org%2Fmy-project")
        self.assertEqual(provider.token, "glpat-testtoken123")
        self.assertEqual(provider.token_type, "PRIVATE-TOKEN")

    @patch.dict(os.environ, {
        "CI_SERVER_URL": "https://gitlab.ci.corp",
        "CI_PROJECT_PATH": "group/subgroup/project",
        "CI_JOB_TOKEN": "job-token-xyz"
    }, clear=True)
    def test_ci_job_token_resolution(self):
        provider = GitLabV4Provider()
        self.assertEqual(provider.server_url, "https://gitlab.ci.corp")
        self.assertEqual(provider.project_id_encoded, "group%2Fsubgroup%2Fproject")
        self.assertEqual(provider.token, "job-token-xyz")
        self.assertEqual(provider.token_type, "JOB-TOKEN")

    def test_numeric_project_id(self):
        provider = GitLabV4Provider(
            server_url="https://gitlab.com",
            project_id="123456",
            token="test-token"
        )
        self.assertEqual(provider.project_id_encoded, "123456")


class TestGitLabApiOperations(unittest.TestCase):
    def setUp(self):
        self.provider = GitLabV4Provider(
            server_url="https://gitlab.com",
            project_id="owner/repo",
            token="glpat-mock-token"
        )

    @patch("urllib.request.urlopen")
    def test_list_issues_pagination(self, mock_urlopen):
        page1_data = json.dumps([
            {"iid": 1, "title": "Epic 1", "state": "opened", "labels": ["type::epic"]},
            {"iid": 2, "title": "Feature 1", "state": "opened", "labels": ["type::feature"]}
        ]).encode("utf-8")
        
        page2_data = json.dumps([
            {"iid": 3, "title": "User Story 1", "state": "closed", "labels": ["type::user-story"]}
        ]).encode("utf-8")

        resp1 = MagicMock()
        resp1.status = 200
        resp1.headers = {"X-Next-Page": "2"}
        resp1.read.return_value = page1_data
        resp1.__enter__.return_value = resp1

        resp2 = MagicMock()
        resp2.status = 200
        resp2.headers = {"X-Next-Page": ""}
        resp2.read.return_value = page2_data
        resp2.__enter__.return_value = resp2

        mock_urlopen.side_effect = [resp1, resp2]

        issues = self.provider.list_issues()
        self.assertEqual(len(issues), 3)
        self.assertEqual(issues[0]["number"], 1)
        self.assertEqual(issues[0]["state"], "OPENED")
        self.assertEqual(issues[2]["number"], 3)
        self.assertEqual(issues[2]["state"], "CLOSED")

    @patch("urllib.request.urlopen")
    def test_create_issue(self, mock_urlopen):
        resp_data = json.dumps({"iid": 42, "title": "New Issue", "state": "opened"}).encode("utf-8")
        resp = MagicMock()
        resp.status = 201
        resp.headers = {}
        resp.read.return_value = resp_data
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        created = self.provider.create_issue("New Issue", "Description", labels=["type::feature"])
        self.assertIsNotNone(created)
        self.assertEqual(created["number"], 42)

    @patch("urllib.request.urlopen")
    def test_edit_issue(self, mock_urlopen):
        resp = MagicMock()
        resp.status = 200
        resp.headers = {}
        resp.read.return_value = b'{"iid": 42}'
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        success = self.provider.edit_issue(42, "Updated description")
        self.assertTrue(success)

    @patch("urllib.request.urlopen")
    def test_edit_issue_title(self, mock_urlopen):
        resp = MagicMock()
        resp.status = 200
        resp.headers = {}
        resp.read.return_value = b'{"iid": 42, "title": "Updated Title"}'
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        success = self.provider.edit_issue_title(42, "Updated Title")
        self.assertTrue(success)

    @patch("urllib.request.urlopen")
    def test_add_label(self, mock_urlopen):
        resp = MagicMock()
        resp.status = 200
        resp.headers = {}
        resp.read.return_value = b'{"iid": 42}'
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        success = self.provider.add_label(42, "status::ready-for-review")
        self.assertTrue(success)

    @patch("urllib.request.urlopen")
    def test_comment_issue(self, mock_urlopen):
        resp = MagicMock()
        resp.status = 201
        resp.headers = {}
        resp.read.return_value = b'{"id": 101, "body": "Test comment"}'
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        success = self.provider.comment_issue(42, "Test comment")
        self.assertTrue(success)


class TestTrackerProviderDetection(unittest.TestCase):
    def test_cli_provider_override(self):
        prov = detect_tracker_provider(cli_provider="gitlab")
        self.assertEqual(prov, "gitlab")

    @patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True)
    def test_gitlab_ci_detection(self):
        prov = detect_tracker_provider()
        self.assertEqual(prov, "gitlab")

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True)
    def test_github_actions_detection(self):
        prov = detect_tracker_provider()
        self.assertEqual(prov, "github")

    def test_rules_loading_with_gitlab_defaults(self):
        rules = load_codebase_rules(os.getcwd(), provider="gitlab")
        self.assertEqual(rules["tracker_rules"]["provider"], "gitlab")
        self.assertEqual(rules["tracker_rules"]["labels"]["epic"], "type::epic")
        self.assertEqual(rules["tracker_rules"]["labels"]["feature"], "type::feature")
        self.assertEqual(rules["tracker_rules"]["labels"]["user_story"], "type::user-story")
        self.assertEqual(rules["tracker_rules"]["labels"]["use_case"], "type::use-case")
        self.assertEqual(rules["tracker_rules"]["labels"]["resolved"], "status::fixed-resolved")

    def test_gitlab_scoped_labels(self):
        rules = {"tracker_rules": {"provider": "gitlab"}}
        self.assertEqual(get_structural_label("Epic", rules), "type::epic")
        self.assertEqual(get_structural_label("Feature", rules), "type::feature")
        self.assertEqual(get_structural_label("User Story", rules), "type::user-story")
        self.assertEqual(get_structural_label("Use Case", rules), "type::use-case")
        self.assertEqual(get_resolved_label(rules), "status::fixed-resolved")


if __name__ == "__main__":
    unittest.main()
