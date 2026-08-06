"""Tests for scripts/generate_spdx_sbom.py.

Verifies SPDX 2.3 SBOM generation from pubspec.yaml and requirements.txt
inputs, including edge cases (missing files, empty deps, SDK deps).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Adjust import path relative to repo root.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_spdx_sbom import (
    _parse_pubspec,
    _parse_requirements,
    _spdx_ref,
    generate_sbom,
)


class TestSpdxRef:
    """Tests for _spdx_ref helper."""

    def test_simple_name(self) -> None:
        assert _spdx_ref("my-package") == "SPDXRef-my-package"

    def test_replaces_underscores(self) -> None:
        assert _spdx_ref("my_package") == "SPDXRef-my-package"

    def test_replaces_special_chars(self) -> None:
        assert _spdx_ref("pkg@1.0") == "SPDXRef-pkg-1.0"


class TestParsePubspec:
    """Tests for _parse_pubspec."""

    def test_parses_dependencies(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text(
            "dependencies:\n"
            "  cupertino_icons: ^1.0.8\n"
            "  path: ^1.9.0\n"
        )

        packages = _parse_pubspec(pubspec)

        assert len(packages) == 2
        names = {p["name"] for p in packages}
        assert names == {"cupertino_icons", "path"}

    def test_skips_sdk_dependencies(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text(
            "dependencies:\n"
            "  flutter:\n"
            "    sdk: flutter\n"
            "  http: ^1.0.0\n"
        )

        packages = _parse_pubspec(pubspec)

        assert len(packages) == 1
        assert packages[0]["name"] == "http"

    def test_parses_dev_dependencies(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text(
            "dev_dependencies:\n"
            "  flutter_lints: ^6.0.0\n"
        )

        packages = _parse_pubspec(pubspec)

        assert len(packages) == 1
        assert packages[0]["name"] == "flutter_lints"

    def test_empty_dependencies_section(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("name: test\n")

        packages = _parse_pubspec(pubspec)

        assert packages == []

    def test_download_location(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("dependencies:\n  http: ^1.0.0\n")

        packages = _parse_pubspec(pubspec)

        assert packages[0]["downloadLocation"] == "https://pub.dev/packages/http"


class TestParseRequirements:
    """Tests for _parse_requirements."""

    def test_parses_packages(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("PyYAML>=6.0\npyang\n")

        packages = _parse_requirements(req)

        assert len(packages) == 2
        names = {p["name"] for p in packages}
        assert names == {"PyYAML", "pyang"}

    def test_skips_comments_and_blanks(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("# a comment\n\npyang\n")

        packages = _parse_requirements(req)

        assert len(packages) == 1

    def test_version_info_captured(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("PyYAML>=6.0\n")

        packages = _parse_requirements(req)

        assert packages[0]["versionInfo"] == ">=6.0"

    def test_noassertion_for_bare_name(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("pyang\n")

        packages = _parse_requirements(req)

        assert packages[0]["versionInfo"] == "NOASSERTION"

    def test_download_location(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("pyang\n")

        packages = _parse_requirements(req)

        assert packages[0]["downloadLocation"] == "https://pypi.org/project/pyang/"


class TestGenerateSbom:
    """Tests for the generate_sbom top-level function."""

    def test_spdx_version(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("name: test\n")
        req = tmp_path / "requirements.txt"
        req.write_text("")

        sbom = generate_sbom(pubspec, req)

        assert sbom["spdxVersion"] == "SPDX-2.3"

    def test_data_license(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("name: test\n")
        req = tmp_path / "requirements.txt"
        req.write_text("")

        sbom = generate_sbom(pubspec, req)

        assert sbom["dataLicense"] == "CC0-1.0"

    def test_combines_pubspec_and_requirements(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("dependencies:\n  http: ^1.0.0\n")
        req = tmp_path / "requirements.txt"
        req.write_text("pyang\n")

        sbom = generate_sbom(pubspec, req)

        assert len(sbom["packages"]) == 2
        names = {p["name"] for p in sbom["packages"]}
        assert names == {"http", "pyang"}

    def test_relationships_match_packages(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("dependencies:\n  http: ^1.0.0\n")
        req = tmp_path / "requirements.txt"
        req.write_text("")

        sbom = generate_sbom(pubspec, req)

        assert len(sbom["relationships"]) == len(sbom["packages"])
        for rel in sbom["relationships"]:
            assert rel["relationshipType"] == "DESCRIBES"

    def test_missing_pubspec_handled(self, tmp_path: Path) -> None:
        missing = tmp_path / "no_such_file.yaml"
        req = tmp_path / "requirements.txt"
        req.write_text("pyang\n")

        sbom = generate_sbom(missing, req)

        assert len(sbom["packages"]) == 1

    def test_missing_requirements_handled(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("dependencies:\n  http: ^1.0.0\n")
        missing = tmp_path / "no_req.txt"

        sbom = generate_sbom(pubspec, missing)

        assert len(sbom["packages"]) == 1

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("dependencies:\n  http: ^1.0.0\n")
        req = tmp_path / "requirements.txt"
        req.write_text("pyang\n")

        sbom = generate_sbom(pubspec, req)
        json_str = json.dumps(sbom)

        parsed = json.loads(json_str)
        assert parsed["spdxVersion"] == "SPDX-2.3"
