import os
import pytest
from parity_auditor.validators.link_validator import LinkValidator
from parity_auditor.core.workspace import WorkspaceRepository

def test_link_validator_detects_broken_link(tmp_path):
    repo = WorkspaceRepository(str(tmp_path))
    
    # Create backlog directories
    features_dir = tmp_path / "docs" / "features"
    features_dir.mkdir(parents=True)
    
    # Define a codebase_rules mock
    class MockRules:
        class BacklogDirs:
            features = "docs/features"
            epics = None
            user_stories = None
            use_cases = None
        backlog_directories = BacklogDirs()
    
    # Patch repo.get_codebase_rules to return our mock
    import types
    repo.get_codebase_rules = types.MethodType(lambda self: MockRules(), repo)

    # Create a feature with a valid and broken link
    valid_target = features_dir / "valid-target.md"
    valid_target.write_text("Hello")

    feature_file = features_dir / "feat-01-test.md"
    feature_file.write_text(
        "Here is a valid link [Valid](valid-target.md).\n"
        "Here is a broken link [Broken](broken-target.md).\n"
        "Here is a GitHub blob link [Valid Blob](https://github.com/org/repo/blob/main/docs/features/valid-target.md).\n"
        "Here is a GitHub broken blob link [Broken Blob](https://github.com/org/repo/blob/main/docs/features/broken-blob.md).\n"
        "Here is a GitHub broken yang link [Broken Yang](https://github.com/org/repo/blob/main/standard/ietf/RFC/nonexistent.yang).\n"
    )

    validator = LinkValidator()
    errors = validator.validate(repo)
    
    assert len(errors) == 3
    assert all(e.rule_id == "markdown-broken-link-reference" for e in errors)
    messages = [str(e) for e in errors]
    assert any("broken-target.md" in msg for msg in messages)
    assert any("broken-blob.md" in msg for msg in messages)
    assert any("nonexistent.yang" in msg for msg in messages)

