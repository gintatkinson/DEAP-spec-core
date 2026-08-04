import re
import sys
import os
import pytest
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.utils.comment_utils import strip_comments_and_strings

common_words = { "id", "name", "type", "status", "value", "height", "width", "time", "x", "y", "z", "t", "date", "info", "data", "key", "code", "save", "edit", "view", "vector" }

def is_present_in_codebase(v: str, codebase: List[str]) -> bool:
    v_escaped = re.escape(v)
    if v.lower() not in common_words:
        return any(re.search(r'\b' + v_escaped + r'\b', strip_comments_and_strings(content)) for content in codebase)

    patterns = [
        r'\.\s*' + v_escaped + r'\b',
        r'\bthis\s*\.\s*' + v_escaped + r'\b',
        r'\b[a-zA-Z_][a-zA-Z0-9_<>\s]*\s+' + v_escaped + r'\b',
        r'\b' + v_escaped + r'\s*:',
        r'\bconst\s*\{\s*[^}]*\b' + v_escaped + r'\b[^}]*\}\s*=',
        r'\blet\s*\{\s*[^}]*\b' + v_escaped + r'\b[^}]*\}\s*=',
    ]
    return any(any(re.search(pat, strip_comments_and_strings(content)) for pat in patterns) for content in codebase)


class TestIsPresentInCodebase:

    def test_non_common_word_matches_in_code_not_comment(self):
        """A non-common property name in actual code should be found."""
        code = ["const widget = new MyWidget();\nwidget.userId = 123;"]
        assert is_present_in_codebase("userId", code) is True

    def test_non_common_word_only_in_comment_returns_false(self):
        """A non-common property name only in a comment should NOT be found."""
        code = ["// This component uses the userId field from the API response\nconst widget = new MyWidget();"]
        assert is_present_in_codebase("userId", code) is False, (
            "userId appearing only in a comment was incorrectly matched as present in codebase"
        )

    def test_non_common_word_only_in_block_comment_returns_false(self):
        """A non-common property name only in a block comment should NOT be found."""
        code = ["/*\n * The userId is derived from the session token.\n */\nconst widget = new MyWidget();"]
        assert is_present_in_codebase("userId", code) is False, (
            "userId appearing only in a block comment was incorrectly matched"
        )

    def test_non_common_word_only_in_string_does_not_match(self):
        """A non-common property name only in a string literal should NOT be found."""
        code = ["const label = 'userId';"]
        result = is_present_in_codebase("userId", code)
        assert result is False, (
            "userId appearing only in a string literal was incorrectly matched as present in codebase"
        )

    def test_common_word_in_comment_not_matched_as_code(self):
        """Common word 'id' in a line comment should not be matched with strict patterns."""
        code = ["// Assign a unique id to each item\nconst item = new Item();\nitem.id = generateId();"]
        result = is_present_in_codebase("id", code)
        assert result is True, (
            "id is used in real code (item.id), so it should be found"
        )

    def test_common_word_only_in_comment_returns_false(self):
        """Common word 'id' only in a comment should NOT be matched."""
        code = ["// The record id is important for tracking\nfunction process() {\n  return true;\n}"]
        result = is_present_in_codebase("id", code)
        assert result is False, (
            "id appearing only in a comment was incorrectly matched as present in codebase"
        )

    def test_common_word_in_block_comment_only_returns_false(self):
        """Common word 'name' only in a block comment should NOT be matched."""
        code = ["/*\n * The component name is derived from metadata.\n */\nfunction render() {\n  return <div />;\n}"]
        result = is_present_in_codebase("name", code)
        assert result is False, (
            "name appearing only in a block comment was incorrectly matched"
        )

    def test_common_word_in_actual_code_matches(self):
        """Common word 'name' used as property in code should be found."""
        code = ["class User {\n  String name;\n  User(this.name);\n}"]
        result = is_present_in_codebase("name", code)
        assert result is True, (
            "name used as a real code declaration should be found"
        )


class TestAssertNoMockCli:

    def test_assert_no_mock_cli_detects_scratch_bin_binary(self, tmp_path, capsys):
        from parity_auditor.cli import assert_no_mock_cli
        workspace = str(tmp_path)
        scratch_bin = os.path.join(workspace, "scratch", "bin")
        os.makedirs(scratch_bin, exist_ok=True)
        mock_gh = os.path.join(scratch_bin, "gh")
        with open(mock_gh, "w") as f:
            f.write("#!/bin/sh\necho mock")

        with pytest.raises(SystemExit) as exc_info:
            assert_no_mock_cli(workspace)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "[FATAL] Zero-mocking policy violation" in captured.err

    def test_assert_no_mock_cli_passes_when_clean(self, tmp_path):
        from parity_auditor.cli import assert_no_mock_cli
        workspace = str(tmp_path)
        assert_no_mock_cli(workspace)


class TestSanitizeGithubTokenEnv:

    def test_sanitize_removes_dummy_keywords_from_github_token_and_gh_token(self, monkeypatch):
        from parity_auditor.cli import sanitize_github_token_env

        keywords = ["antigravity_token", "my_dummy_key", "placeholder", "invalid_tok", "mock_secret"]
        for kw in keywords:
            monkeypatch.setenv("GITHUB_TOKEN", kw)
            monkeypatch.setenv("GH_TOKEN", kw)
            sanitize_github_token_env()
            assert "GITHUB_TOKEN" not in os.environ, f"GITHUB_TOKEN with '{kw}' was not removed"
            assert "GH_TOKEN" not in os.environ, f"GH_TOKEN with '{kw}' was not removed"

    def test_sanitize_preserves_valid_tokens(self, monkeypatch):
        from parity_auditor.cli import sanitize_github_token_env

        valid_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        monkeypatch.setenv("GITHUB_TOKEN", valid_token)
        monkeypatch.setenv("GH_TOKEN", valid_token)
        sanitize_github_token_env()
        assert os.environ.get("GITHUB_TOKEN") == valid_token
        assert os.environ.get("GH_TOKEN") == valid_token

    def test_sanitize_handles_missing_tokens(self, monkeypatch):
        from parity_auditor.cli import sanitize_github_token_env

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        sanitize_github_token_env()

class TestNoteExtraction:

    def test_mermaid_class_diagram_notes_extracted(self):
        from parity_auditor.parsers.mermaid import MermaidClassDiagramParser
        class MockWorkspaceRules:
            class ValidationRules:
                def __init__(self):
                    self.visibility_prefixes = ["+", "-", "#", "~"]
                    self.relationship_connectors = "(<\\|--|\\*--|o--|-->|\\.\\.>|--)"
            def __init__(self):
                self.validation_rules = self.ValidationRules()
        class MockWorkspaceRepo:
            workspace_dir = "."
            def get_codebase_rules(self):
                return MockWorkspaceRules()
        parser = MermaidClassDiagramParser(MockWorkspaceRepo())
        content = """```mermaid
classDiagram
    class ReferenceFrame {
        +string body
    }
    note for ReferenceFrame "alternateSystem guarded by <<feature_guard>> alternate-systems"
```"""
        parsed = parser.parse(content)
        assert "ReferenceFrame" in parsed.classes
        cls_info = parsed.classes["ReferenceFrame"]
        assert len(cls_info.notes) == 1
        assert "alternate-systems" in cls_info.notes[0]

class TestGetOpenFeatureIssues:

    def test_get_open_feature_issues_success_filters_keywords(self, monkeypatch):
        import json
        from parity_auditor.cli import get_open_feature_issues

        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)

        class MockResult:
            returncode = 0
            stdout = json.dumps([
                {"number": 1, "title": "A valid feature"},
                {"number": 2, "title": "A bug fix"},
                {"number": 3, "title": "defect in UI"},
                {"number": 4, "title": "repro for crash"},
                {"number": 5, "title": "tooling update"},
                {"number": 6, "title": "Another valid feature"},
            ])
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockResult())

        issues = get_open_feature_issues()
        assert issues is not None
        assert len(issues) == 2
        assert issues[0]["number"] == 1
        assert issues[1]["number"] == 6

    def test_get_open_feature_issues_returns_none_on_error(self, monkeypatch):
        from parity_auditor.cli import get_open_feature_issues
        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)

        class MockResult:
            returncode = 1
            stdout = ""
            stderr = "gh error"

        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockResult())

        issues = get_open_feature_issues()
        assert issues is None

    def test_get_open_feature_issues_returns_none_on_timeout(self, monkeypatch):
        import subprocess
        from parity_auditor.cli import get_open_feature_issues
        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="gh", timeout=3)
        
        monkeypatch.setattr("subprocess.run", mock_run)

        issues = get_open_feature_issues()
        assert issues is None

    def test_get_open_feature_issues_fast_fail_offline(self, monkeypatch):
        from parity_auditor.cli import get_open_feature_issues
        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)
        monkeypatch.setenv("OFFLINE", "1")
        
        called = False
        def mock_run(*args, **kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr("subprocess.run", mock_run)
        issues = get_open_feature_issues()
        assert issues is None
        assert not called, "subprocess.run should not be called when OFFLINE is set"

    def test_get_open_feature_issues_fast_fail_no_gh(self, monkeypatch):
        from parity_auditor.cli import get_open_feature_issues
        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)
        monkeypatch.setattr("shutil.which", lambda cmd: None)

        called = False
        def mock_run(*args, **kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr("subprocess.run", mock_run)
        issues = get_open_feature_issues()
        assert issues is None
        assert not called, "subprocess.run should not be called when gh is not in PATH"

    def test_get_open_feature_issues_custom_timeout(self, monkeypatch):
        import json
        from parity_auditor.cli import get_open_feature_issues
        monkeypatch.setattr("parity_auditor.cli.assert_no_mock_cli", lambda x: None)
        monkeypatch.setenv("PARITY_AUDITOR_GH_TIMEOUT", "5.5")

        timeout_passed = None
        class MockResult:
            returncode = 0
            stdout = "[]"
            stderr = ""

        def mock_run(*args, **kwargs):
            nonlocal timeout_passed
            timeout_passed = kwargs.get("timeout")
            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)
        get_open_feature_issues()
        assert timeout_passed == 5.5
