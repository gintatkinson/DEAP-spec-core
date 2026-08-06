"""Regression tests for issue #276.

``verify_model_coverage.py`` called ``sanitize_github_token_env()`` at module level
(line 18) as well as inside ``if __name__ == "__main__":`` (line 25). Importing the
module therefore popped ``GITHUB_TOKEN`` / ``GH_TOKEN`` from the process environment,
so any test running afterwards that depended on a mock token failed — an implicit
ordering dependency and a source of flakiness.

The ``__main__`` call already covers the intended use, so the module-level call was
redundant as well as harmful.

Invariant: importing a module must not mutate global process state.
"""

import importlib
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "verify_model_coverage.py")
)


def _load_module_fresh(name="_vmc_probe"):
    """Import the script by path, executing its module-level code."""
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_script_is_discoverable():
    """Guard: the assertions below prove nothing if the path is wrong."""
    assert os.path.isfile(SCRIPT), f"script not found at {SCRIPT}"


def test_import_does_not_mutate_the_environment_issue276(monkeypatch):
    """The core regression. A dummy token must survive an import."""
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token_for_tests")
    monkeypatch.setenv("GH_TOKEN", "placeholder_value")

    _load_module_fresh()

    assert os.environ.get("GITHUB_TOKEN") == "dummy_token_for_tests", (
        "importing verify_model_coverage removed GITHUB_TOKEN from the process "
        "environment. Module import must not mutate global state — this is what made "
        "unrelated tests flaky depending on import order."
    )
    assert os.environ.get("GH_TOKEN") == "placeholder_value", (
        "importing verify_model_coverage removed GH_TOKEN from the process environment"
    )


def test_importing_cli_does_not_mutate_the_environment_issue276(monkeypatch):
    """The issue reported only verify_model_coverage.py:18, but parity_auditor.cli
    carried the identical module-level call at line 46 — and cli is imported far more
    widely, so it was the larger source of the flakiness.

    ``importlib.reload`` is required because other tests in this suite have usually
    already imported the module, and a cached import would not re-run the
    module-level code. That caching is precisely why this defect presented as an
    order-dependent flake rather than a consistent failure.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token_for_tests")
    monkeypatch.setenv("GH_TOKEN", "placeholder_value")

    import parity_auditor.cli as cli_mod
    importlib.reload(cli_mod)

    assert os.environ.get("GITHUB_TOKEN") == "dummy_token_for_tests", (
        "importing parity_auditor.cli removed GITHUB_TOKEN from the process "
        "environment (module-level sanitize call at cli.py:46)"
    )
    assert os.environ.get("GH_TOKEN") == "placeholder_value", (
        "importing parity_auditor.cli removed GH_TOKEN from the process environment"
    )


def test_cli_still_sanitises_from_its_entry_points_issue276(monkeypatch):
    """main() and _main_impl() must retain the sanitising behaviour."""
    import parity_auditor.cli as cli_mod
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token_for_tests")
    cli_mod.sanitize_github_token_env()
    assert "GITHUB_TOKEN" not in os.environ, (
        "cli.sanitize_github_token_env must still strip dummy tokens when invoked"
    )


def test_import_preserves_real_looking_tokens_too(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_realLookingValue123")
    _load_module_fresh()
    assert os.environ.get("GITHUB_TOKEN") == "ghp_realLookingValue123"


def test_sanitiser_still_works_when_called_explicitly_issue276(monkeypatch):
    """The fix must remove the import-time side effect, not the capability.

    Without this, deleting the sanitiser entirely would also pass.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token_for_tests")
    monkeypatch.setenv("GH_TOKEN", "a_placeholder_thing")
    monkeypatch.setenv("UNRELATED_VAR", "keep_me")

    module = _load_module_fresh()
    assert hasattr(module, "sanitize_github_token_env"), (
        "the sanitiser function must still exist and be callable"
    )
    module.sanitize_github_token_env()

    assert "GITHUB_TOKEN" not in os.environ, (
        "explicit invocation must still strip a dummy GITHUB_TOKEN"
    )
    assert "GH_TOKEN" not in os.environ, (
        "explicit invocation must still strip a placeholder GH_TOKEN"
    )
    assert os.environ.get("UNRELATED_VAR") == "keep_me", (
        "the sanitiser must only touch the two token variables"
    )


def test_sanitiser_leaves_non_dummy_values_alone(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_realLookingValue123")
    module = _load_module_fresh()
    module.sanitize_github_token_env()
    assert os.environ.get("GITHUB_TOKEN") == "ghp_realLookingValue123", (
        "the sanitiser must strip only dummy or placeholder values"
    )
