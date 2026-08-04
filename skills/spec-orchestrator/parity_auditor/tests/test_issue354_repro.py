import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from parity_auditor.validators.uml import UmlValidator
from parity_auditor.core.workspace import WorkspaceRepository

def test_reproduce_issue354_unmapped_feature_validation_constraints():
    """
    Issue #354 reproduction test:
    Demonstrates that feature validation constraints under '## 2. Validation & Constraints' (H2 header)
    are silently ignored by uml.py line 551 (which searches for H3 header `###\s+`), causing total_constraints
    to be calculated as 0 instead of 3. As a result, required_flow_count is max(2, 0) = 2 instead of 3,
    and a Use Case with only 2 alternate flows incorrectly PASSES validation without reporting
    `use-case-requires-alternate-and-exception-flows`.
    """
    tmpdir = tempfile.mkdtemp()
    try:
        # Create standard workspace layout
        pipeline_dir = os.path.join(tmpdir, ".pipeline", "logical-ui")
        features_dir = os.path.join(tmpdir, "features")
        usecases_dir = os.path.join(tmpdir, "use_cases")
        userstories_dir = os.path.join(tmpdir, "user_stories")
        
        os.makedirs(pipeline_dir, exist_ok=True)
        os.makedirs(features_dir, exist_ok=True)
        os.makedirs(usecases_dir, exist_ok=True)
        os.makedirs(userstories_dir, exist_ok=True)
        
        import json
        rules = {
            "backlog_directories": {
                "features": "features",
                "use_cases": "use_cases",
                "user_stories": "user_stories"
            },
            "validation_rules": {
                "use_case_alternate_flows_header": "## 5. Alternate and Exception Flows",
                "required_sections": {
                    "feature_ui": [["## 1. Overview", "Overview"]],
                    "feature": [["## 1. Overview", "Overview"]],
                    "use_case": [["## 1. Description", "Description"]]
                }
            }
        }
        with open(os.path.join(pipeline_dir, "codebase_rules.json"), "w", encoding="utf-8") as f:
            json.dump(rules, f)
        
        # Feature file with H2 header '## 2. Validation & Constraints' containing 3 constraints
        feat_path = os.path.join(features_dir, "feat-01-auth.md")
        with open(feat_path, "w", encoding="utf-8") as f:
            f.write(
                "---\ngeneration_mode: subagent\n---\n\n"
                "# Feature 01: Authentication\n\n"
                "## 1. Overview\n"
                "Auth feature.\n\n"
                "## 2. Validation & Constraints\n"
                "- Password must be at least 8 characters\n"
                "- Email must be valid format\n"
                "- Account must not be locked\n"
            )
            
        # Use Case file referencing feat-01-auth.md but providing only 2 alternate flows
        uc_path = os.path.join(usecases_dir, "uc-01-login.md")
        with open(uc_path, "w", encoding="utf-8") as f:
            f.write(
                "---\ngeneration_mode: subagent\n---\n\n"
                "# Use Case 01: Login\n\n"
                "## 1. Description\n"
                "Login usecase.\n\n"
                "## 5. Alternate and Exception Flows\n"
                "### Flow 1: Invalid Password\n"
                "1. System displays error.\n"
                "2. User retries.\n\n"
                "### Flow 2: Locked Account\n"
                "1. System locks UI.\n"
                "2. User contacts support.\n\n"
                "## 6. Postconditions\n"
                "User is logged in.\n\n"
                "## 7. Realization Matrix\n"
                "### Required User Stories\n"
                "- [x] [US-01](https://github.com/org/repo/issues/1)\n\n"
                "### Required Features\n"
                "- [x] [Feature 01: Authentication](https://github.com/org/repo/blob/main/features/feat-01-auth.md)\n"
            )

        repo = WorkspaceRepository(tmpdir)
        validator = UmlValidator()
        findings = validator.validate(repo)
        
        flow_findings = [f for f in findings if "must contain at least 3 detailed Alternate/Exception flows" in str(f) or "use-case-requires-alternate-and-exception-flows" in str(f)]
        
        # Demonstrating the bug: The linter missed the 3 validation constraints under H2 '## 2. Validation & Constraints'
        assert len(flow_findings) > 0, (
            "BUG REPRODUCED (#354): uml.py ignored 3 feature validation constraints under H2 header '## 2. Validation & Constraints', "
            f"allowing Use Case with 2 flows to pass! Total findings: {findings}"
        )
    finally:
        import shutil
        shutil.rmtree(tmpdir)

