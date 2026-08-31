import os
import sys
import tempfile
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.verify_downstream_baseline import (
    check_no_domain_config,
    check_domain_agnostic_ast_cleanliness,
    check_no_duplicate_master_blueprints,
)


class TestCheckNoDomainConfigAndCleanliness(unittest.TestCase):
    def test_check_domain_agnostic_ast_cleanliness_on_clean_repo(self):
        """Verify Check 19 passes on the clean upstream repository."""
        check_domain_agnostic_ast_cleanliness(repo_root)

    def test_check_domain_agnostic_ast_cleanliness_detects_violation(self):
        """Verify Check 19 catches and raises SystemExit on hardcoded domain variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create upstream marker
            upstream_dir = os.path.join(tmpdir, ".pipeline", "upstream")
            os.makedirs(upstream_dir, exist_ok=True)

            scripts_dir = os.path.join(tmpdir, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)

            # Write a bad python file containing a forbidden domain token
            bad_file = os.path.join(scripts_dir, "bad_tool.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write("def calculate():\n    wingspan_m = 2.5\n    return wingspan_m\n")

            with self.assertRaises(SystemExit) as cm:
                check_domain_agnostic_ast_cleanliness(tmpdir)
            self.assertEqual(cm.exception.code, 1)

    def test_check_domain_agnostic_ast_cleanliness_skips_downstream(self):
        """Verify Check 19 skips cleanly when no upstream marker is present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No .pipeline/upstream
            scripts_dir = os.path.join(tmpdir, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            bad_file = os.path.join(scripts_dir, "downstream_spec.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write("def test():\n    wingspan_m = 10\n")

            # Should not raise
            check_domain_agnostic_ast_cleanliness(tmpdir)

    def test_check_no_duplicate_master_blueprints_skips_upstream(self):
        """Verify Check 12 skips cleanly when upstream marker .pipeline/upstream is present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            upstream_dir = os.path.join(tmpdir, ".pipeline", "upstream")
            os.makedirs(upstream_dir, exist_ok=True)
            # Upstream can have master blueprints
            with open(os.path.join(tmpdir, "DEAP_MASTER_ARCHITECTURE.md"), "w", encoding="utf-8") as f:
                f.write("# Master Architecture\n")

            # Should not raise
            check_no_duplicate_master_blueprints(tmpdir)

    def test_check_no_duplicate_master_blueprints_detects_duplicate_in_downstream_root_or_docs(self):
        """Verify Check 12 catches duplicate master blueprints anywhere in downstream repo_root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Downstream repo (no upstream marker)
            docs_dir = os.path.join(tmpdir, "docs", "architecture")
            os.makedirs(docs_dir, exist_ok=True)
            with open(os.path.join(docs_dir, "THREE_TIER_GOVERNANCE_BLUEPRINT.md"), "w", encoding="utf-8") as f:
                f.write("# Duplicate Blueprint\n")

            with self.assertRaises(SystemExit) as cm:
                check_no_duplicate_master_blueprints(tmpdir)
            self.assertEqual(cm.exception.code, 1)

    def test_check_no_duplicate_master_blueprints_passes_on_clean_downstream(self):
        """Verify Check 12 passes when downstream repository has zero master core blueprints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = os.path.join(tmpdir, "docs", "conops")
            os.makedirs(docs_dir, exist_ok=True)
            with open(os.path.join(docs_dir, "CONOPS.md"), "w", encoding="utf-8") as f:
                f.write("# CONOPS\n")

            # Should not raise
            check_no_duplicate_master_blueprints(tmpdir)


if __name__ == "__main__":
    unittest.main()
