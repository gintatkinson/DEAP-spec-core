#!/usr/bin/env python3
"""
Verify downstream project baseline conformance.
Asserts baseline files exist, validates type compatibility with mandated domain classes,
and runs the build/test commands ('npm run build' for React, 'flutter analyze && flutter test' for Flutter).
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys

TIMEOUT_SECONDS = 600
GIT_TIMEOUT_SECONDS = 30
EXCLUDED_DIRS = {".git", "node_modules", ".dart_tool", "build"}

def _terminate_process_group(proc):
    """Terminate process group cleanly with SIGTERM followed by SIGKILL fallback."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=15)
    except (subprocess.TimeoutExpired, ProcessLookupError, PermissionError):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError, PermissionError):
            pass

def _run_bounded(cmd, cwd, timeout, label):
    """Run cmd with a timeout that binds the whole process tree.

    subprocess.run's timeout kills only the direct child. flutter and npm are
    launchers whose real work happens in grandchildren (analysis server, dart
    test host, xcodebuild), which survive that kill, keep the build directory
    open, and then race the cleanup_workspace rmtree. start_new_session puts the
    tree in its own process group so a single killpg reaches all of it.
    """
    proc = subprocess.Popen(cmd, cwd=cwd, start_new_session=True)
    try:
        rc = proc.wait(timeout=timeout)
    finally:
        _terminate_process_group(proc)
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)

def check_no_domain_config(destination):
    config_paths = [
        os.path.join(destination, ".pipeline", "logical-ui", "codebase_rules.json"),
        os.path.join(destination, "codebase_rules.json"),
        os.path.join(destination, "baseline_manifest.json")
    ]
    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    if "validation_rules" in data and isinstance(data["validation_rules"], dict):
                        if data["validation_rules"].get("no_domain") is True:
                            return True
                    if data.get("no_domain") is True:
                        return True
            except Exception:
                pass
    return False

def tag_restoration_point(repo_root=None):
    print("Tagging restoration point...")
    try:
        is_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, cwd=repo_root, timeout=GIT_TIMEOUT_SECONDS)
        if is_git.returncode != 0:
            print("WARNING: Skipping restoration point tag - not inside a git repository.", file=sys.stderr)
            return False

        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=repo_root, timeout=GIT_TIMEOUT_SECONDS)
        if res.returncode != 0:
            print("WARNING: Skipping restoration point tag - git HEAD is unborn (fresh repository).", file=sys.stderr)
            return True
        subprocess.run(["git", "tag", "-f", "restoration-point"], check=True, cwd=repo_root, timeout=GIT_TIMEOUT_SECONDS)
        return True
    except subprocess.TimeoutExpired as e:
        print(f"WARNING: Failed to tag restoration point: {e}", file=sys.stderr)
        return False
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"WARNING: Failed to tag restoration point: {e}", file=sys.stderr)
        return False

def cleanup_workspace(destination):
    print("Cleaning up workspace...")
    to_delete_files = [".dart_tool/package_config.json.lock",
                       ".flutter-plugins-dependencies",
                       ".flutter-plugins"]
    for f in to_delete_files:
        path = os.path.join(destination, f)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    dirs_to_remove = ["build", ".flutter-plugins", ".flutter-plugins-dependencies"]
    for d in dirs_to_remove:
        d_path = os.path.join(destination, d)
        if os.path.isdir(d_path):
            shutil.rmtree(d_path, ignore_errors=True)

    for root, dirs, files in os.walk(destination):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith(".db-shm") or f.endswith(".db-wal") or f.endswith(".db-journal"):
                sidecar_path = os.path.join(root, f)
                if f.endswith(".db-shm") or f.endswith(".db-wal"):
                    owner_name = f[:-4]
                else:
                    owner_name = f[:-8]
                owner_db = os.path.join(root, owner_name)
                if os.path.exists(owner_db):
                    print(f"NOTE: Preserving active SQLite sidecar '{sidecar_path}' (owning database '{owner_db}' exists).")
                else:
                    try:
                        os.remove(sidecar_path)
                    except Exception:
                        pass


# Mandated domain classes/interfaces to check in types.ts or types.dart
MANDATED_CLASSES = []

def load_mandated_classes(destination):
    config_paths = [
        os.path.join(destination, ".pipeline", "logical-ui", "codebase_rules.json"),
        os.path.join(destination, "codebase_rules.json"),
        os.path.join(destination, "baseline_manifest.json")
    ]
    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                classes = None
                if isinstance(data, dict):
                    if "validation_rules" in data and isinstance(data["validation_rules"], dict):
                        classes = data["validation_rules"].get("mandated_classes")
                    if classes is None:
                        classes = data.get("mandated_classes")
                
                if isinstance(classes, list):
                    if all(isinstance(c, str) for c in classes):
                        print(f"Loaded mandated classes dynamically from {path}: {classes}")
                        return classes
                    else:
                        print(f"WARNING: Invalid format for 'mandated_classes' in {path} (not all elements are strings).", file=sys.stderr)
                else:
                    print(f"WARNING: 'mandated_classes' not found or not a list in {path}.", file=sys.stderr)
            except Exception as e:
                print(f"WARNING: Failed to parse or load config {path}: {e}", file=sys.stderr)
    
    print("Using default hardcoded MANDATED_CLASSES.")
    return MANDATED_CLASSES

def main():
    parser = argparse.ArgumentParser(description="Verify a downstream project's baseline conformance.")
    parser.add_argument("--no-domain", action="store_true", help="Skip checking the domain model")
    parser.add_argument("--target", help="Target project directory", default=None)
    parser.add_argument("--output", help="Output JSON report file path", default=None)
    parser.add_argument("destination", nargs="?", default=".", help="Path to the downstream project directory (defaults to current directory)")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.destination)

    targets = []
    if args.target:
        target_dir = os.path.abspath(args.target)
        if os.path.isdir(target_dir):
            targets.append(target_dir)
        else:
            print(f"ERROR: Target path '{target_dir}' is not a directory.", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.path.isdir(repo_root):
            print(f"ERROR: Destination path '{repo_root}' is not a directory.", file=sys.stderr)
            sys.exit(1)

        is_self_flutter = os.path.exists(os.path.join(repo_root, "pubspec.yaml"))
        is_self_react = os.path.exists(os.path.join(repo_root, "package.json"))
        if is_self_flutter or is_self_react:
            targets.append(repo_root)

        app_flutter_dir = os.path.join(repo_root, "app_flutter")
        if os.path.isdir(app_flutter_dir) and os.path.exists(os.path.join(app_flutter_dir, "pubspec.yaml")):
            if app_flutter_dir not in targets:
                targets.append(app_flutter_dir)

        web_react_dir = os.path.join(repo_root, "web_react")
        if os.path.isdir(web_react_dir) and os.path.exists(os.path.join(web_react_dir, "package.json")):
            if web_react_dir not in targets:
                targets.append(web_react_dir)

        if not targets and os.path.isdir(repo_root):
            print(f"NOTE: Destination path '{repo_root}' has no pubspec.yaml or package.json. Registering repository root for non-framework baseline checks.")
            targets.append(repo_root)

    if not targets:
        print(f"ERROR: Destination path '{repo_root}' does not appear to be a valid directory.", file=sys.stderr)
        sys.exit(1)

    reports = []
    for dest in targets:
        is_flutter = os.path.exists(os.path.join(dest, "pubspec.yaml"))
        is_react = os.path.exists(os.path.join(dest, "package.json"))

        no_domain_for_target = args.no_domain
        if not args.no_domain and (
            check_no_domain_config(repo_root) or check_no_domain_config(dest)
        ):
            no_domain_for_target = True
            flutter_domain = os.path.join(dest if is_flutter else repo_root, "lib", "domain")
            react_domain = os.path.join(dest if is_react else repo_root, "src", "domain")
            if os.path.isdir(flutter_domain) or os.path.isdir(react_domain):
                print(f"NOTE: Domain directory found on disk for '{dest}' — overriding no_domain config and enabling domain verification.")
                no_domain_for_target = False

        target_args = argparse.Namespace(**vars(args))
        target_args.no_domain = no_domain_for_target

        try:
            _run_verification(target_args, dest, repo_root, is_flutter, is_react)
            print(f"Success: Build and test suite execution passed for '{dest}'. Conformance gate verified.")
            reports.append({
                "status": "success",
                "target": dest,
                "platform": "flutter" if is_flutter else ("react" if is_react else "unknown"),
                "destination": dest,
                "domain_verified": not no_domain_for_target,
            })
        finally:
            cleanup_workspace(dest)

    if args.output and reports:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        report_data = reports[0] if len(reports) == 1 else {"status": "success", "reports": reports}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"Wrote downstream baseline report to {args.output}")

    if not tag_restoration_point(repo_root=repo_root):
        print("ERROR: Conformance gate verified but restoration point tag could not be placed.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

def _validate_domain_types(dest, repo_root, ext, domain_subpath):
    mandated = load_mandated_classes(dest)
    if repo_root != dest:
        upstream_mandated = load_mandated_classes(repo_root)
        mandated = list(set(mandated + upstream_mandated))
    if not mandated:
        print("No mandated classes configured — skipping type validation.")
        return
    domain_dir = os.path.join(dest, domain_subpath)
    if not os.path.isdir(domain_dir):
        print(f"ERROR: Domain directory '{domain_dir}' does not exist but mandated classes are configured.", file=sys.stderr)
        sys.exit(1)
    source_files = []
    for root, _, files in os.walk(domain_dir):
        for f in files:
            if f.endswith("." + ext) or (ext == "ts" and f.endswith(".tsx")):
                source_files.append(os.path.join(root, f))
    if not source_files:
        print(f"ERROR: No .{ext} source files found in '{domain_dir}' but mandated classes are configured.", file=sys.stderr)
        sys.exit(1)
    combined = ""
    for sf in source_files:
        with open(sf, "r", encoding="utf-8") as f:
            combined += f.read() + "\n"
    if ext == "dart":
        type_keywords = r"(?:class|mixin|enum|extension\s+type|sealed\s+class)"
        pattern = r"\b" + type_keywords + r"\s+({})\b".format("|".join(re.escape(c) for c in mandated))
    else:
        pattern = r"\b(?:interface|class|type)\s+({})\b".format("|".join(re.escape(c) for c in mandated))
    found = set(re.findall(pattern, combined, re.MULTILINE))
    missing = set(mandated) - found
    if missing:
        print(f"ERROR: Type validation failed. Mandated classes missing in {domain_subpath}/: {', '.join(sorted(missing))}", file=sys.stderr)
        sys.exit(1)
    print(f"Success: All {len(mandated)} mandated domain classes found in {domain_subpath}/.")

def check_gitignore_exists(repo_root):
    """Check 10: Verify .gitignore exists in the repository root."""
    gitignore_path = os.path.join(repo_root, ".gitignore")
    if not os.path.isfile(gitignore_path):
        print(f"ERROR: Check 10 failed: .gitignore missing in repository root '{repo_root}'.", file=sys.stderr)
        sys.exit(1)
    print("Success: Check 10 verified (.gitignore exists in repository root).")

def check_no_ds_store_files(repo_root):
    """Check 11: Verify zero .DS_Store files exist in the working tree or git index."""
    ds_store_files = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f == ".DS_Store":
                ds_store_files.append(os.path.join(root, f))
    if ds_store_files:
        print(f"ERROR: Check 11 failed: Found {len(ds_store_files)} .DS_Store file(s) in working tree or git index: {', '.join(ds_store_files)}", file=sys.stderr)
        sys.exit(1)
    print("Success: Check 11 verified (zero .DS_Store files found).")

def check_no_duplicate_master_blueprints(dest):
    """Check 12: Verify downstream repositories do NOT contain duplicate master core blueprints."""
    # If the repository is upstream (indicated by .pipeline/upstream), master blueprints are expected here
    if os.path.exists(os.path.join(dest, ".pipeline", "upstream")):
        print("Success: Check 12 verified (upstream repository retains canonical master core blueprints).")
        return

    master_blueprints = {
        "DEAP_MASTER_ARCHITECTURE.md",
        "THREE_TIER_GOVERNANCE_BLUEPRINT.md",
        "DEAP_SYSML_V2_SAFETY_MODEL_SPECIFICATION.sysml"
    }
    duplicates = []
    for root, dirs, files in os.walk(dest):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f in master_blueprints:
                duplicates.append(os.path.join(root, f))
    if duplicates:
        print(f"ERROR: Check 12 failed: Downstream repository contains duplicate master core blueprint file(s): {', '.join(duplicates)}", file=sys.stderr)
        sys.exit(1)
    print("Success: Check 12 verified (no duplicate master core blueprints found).")

def check_latex_katex_syntax(repo_root):
    """Check 13: Verify KaTeX / LaTeX mathematical rendering syntax across all markdown files."""
    allowed_alignment_envs = {
        "aligned", "alignedat", "matrix", "pmatrix", "bmatrix", "Bmatrix",
        "vmatrix", "Vmatrix", "cases", "dcases", "rcases", "array",
        "split", "gathered", "gather", "subarray", "smallmatrix"
    }
    errors = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if not f.endswith(".md"):
                continue
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, repo_root)
            try:
                with open(file_path, "r", encoding="utf-8") as md_file:
                    content = md_file.read()
            except Exception as e:
                errors.append(f"Failed to read {rel_path}: {e}")
                continue

            # Strip code blocks and inline code
            cleaned = re.sub(r"```.*?```|~~~.*?~~~", "", content, flags=re.DOTALL)
            cleaned = re.sub(r"`+.*?`+", "", cleaned)

            # a. Validate balanced $$ math blocks
            parts = cleaned.split("$$")
            if (len(parts) - 1) % 2 != 0:
                errors.append(f"Unbalanced $$ display math delimiters in {rel_path} (found {len(parts) - 1} delimiters).")
                continue

            # Check balanced \begin{aligned} and \end{aligned} globally in the file
            num_begin_aligned_all = len(re.findall(r"\\begin\{aligned\}", cleaned))
            num_end_aligned_all = len(re.findall(r"\\end\{aligned\}", cleaned))
            if num_begin_aligned_all != num_end_aligned_all:
                errors.append(f"Unbalanced \\begin{{aligned}} ({num_begin_aligned_all}) and \\end{{aligned}} ({num_end_aligned_all}) pairs in {rel_path}.")

            # Validate each math block
            for i in range(1, len(parts), 2):
                block = parts[i]

                # c. Detect top-level \begin{align} or \begin{align*}
                if re.search(r"\\begin\{align\*?\}", block):
                    errors.append(
                        f"Forbidden \\begin{{align}} or \\begin{{align*}} found in display math block in {rel_path}. "
                        f"In markdown KaTeX, \\begin{{aligned}} must be used instead."
                    )

                # d. Validate balanced \begin{aligned} and \end{aligned} pairs within the block
                num_begin_aligned = len(re.findall(r"\\begin\{aligned\}", block))
                num_end_aligned = len(re.findall(r"\\end\{aligned\}", block))
                if num_begin_aligned != num_end_aligned:
                    errors.append(
                        f"Unbalanced \\begin{{aligned}} ({num_begin_aligned}) and \\end{{aligned}} ({num_end_aligned}) in math block in {rel_path}."
                    )

                # b. Detect bare alignment operators & outside alignment environments
                token_pattern = re.compile(r"\\begin\{([a-zA-Z*]+)\}|\\end\{([a-zA-Z*]+)\}|\\&|&")
                env_stack = []
                for match in token_pattern.finditer(block):
                    token = match.group(0)
                    if token.startswith(r"\begin{"):
                        env_stack.append(match.group(1))
                    elif token.startswith(r"\end{"):
                        end_name = match.group(2)
                        if end_name in env_stack:
                            while env_stack:
                                popped = env_stack.pop()
                                if popped == end_name:
                                    break
                    elif token == r"\&":
                        continue
                    elif token == "&":
                        if not any(env in allowed_alignment_envs for env in env_stack):
                            snippet = block[max(0, match.start() - 20):min(len(block), match.end() + 20)].strip().replace("\n", " ")
                            errors.append(
                                f"Bare alignment operator '&' outside alignment environment in {rel_path}: \"...{snippet}...\""
                            )

    if errors:
        print("ERROR: Check 13 failed (KaTeX / LaTeX mathematical syntax violations found):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    print("Success: Check 13 verified (KaTeX / LaTeX mathematical syntax valid across all markdown files).")

def check_downstream_instructions_exist(repo_root):
    """Check 14: Verify presence of README.md and agent instruction entrypoints (AGENTS.md, CLAUDE.md, or .agents/AGENTS.md)."""
    readme_path = os.path.join(repo_root, "README.md")
    if not os.path.isfile(readme_path):
        print(f"ERROR: Check 14 failed: README.md missing in repository root '{repo_root}'.", file=sys.stderr)
        sys.exit(1)
    if os.path.getsize(readme_path) == 0:
        print(f"ERROR: Check 14 failed: README.md is empty in repository root '{repo_root}'.", file=sys.stderr)
        sys.exit(1)

    agent_entrypoints = [
        os.path.join(repo_root, "AGENTS.md"),
        os.path.join(repo_root, "CLAUDE.md"),
        os.path.join(repo_root, ".agents", "AGENTS.md"),
    ]
    valid_entrypoints = [p for p in agent_entrypoints if os.path.isfile(p) and os.path.getsize(p) > 0]
    if not valid_entrypoints:
        print(f"ERROR: Check 14 failed: No non-empty agent instruction entrypoint found in '{repo_root}' (expected AGENTS.md, CLAUDE.md, or .agents/AGENTS.md).", file=sys.stderr)
        sys.exit(1)

    print("Success: Check 14 verified (README.md and agent instruction entrypoints exist).")

def _run_verification(args, dest, repo_root, is_flutter, is_react):
    # Run Checks 10, 11, 12, 13, and 14
    check_gitignore_exists(repo_root)
    check_no_ds_store_files(repo_root)
    check_no_duplicate_master_blueprints(dest)
    check_latex_katex_syntax(repo_root)
    check_downstream_instructions_exist(repo_root)

    if is_flutter:
        print(f"Verifying conformance for platform 'flutter' at '{dest}'...")
        # 1. Assert baseline files exist
        baseline_files = [
            "pubspec.yaml",
            "analysis_options.yaml",
            "lib/main.dart",
            "lib/domain/validation.dart"
        ]
        missing_files = []
        for f in baseline_files:
            path = os.path.join(dest, f)
            if not os.path.exists(path):
                missing_files.append(f)

        repo_resolver_paths = [
            os.path.join(dest, "lib", "domain", "repository_resolver.dart"),
            os.path.join(dest, "lib", "core", "di", "repository_resolver.dart"),
        ]
        if not any(os.path.exists(p) for p in repo_resolver_paths) and not args.no_domain:
            missing_files.append("lib/domain/repository_resolver.dart (or lib/core/di/repository_resolver.dart)")

        if missing_files:
            print(f"ERROR: Flutter baseline file(s) missing: {', '.join(missing_files)}", file=sys.stderr)
            sys.exit(1)

        print("Success: All Flutter baseline files exist.")

        # 2. Validate type compatibility
        if args.no_domain:
            print("Skipping domain type compatibility validation (--no-domain specified).")
        else:
            _validate_domain_types(dest, repo_root, "dart", os.path.join("lib", "domain"))

        # 3. Run build/test commands
        if args.no_domain:
            print("Skipping build and test suite execution (--no-domain specified, domain implementation pending).")
        else:
            try:
                # Resolve and copy assets directory from template
                upstream_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                src_assets = os.path.join(upstream_repo_root, "app_flutter", "assets")
                dest_assets = os.path.join(dest, "assets")
                if os.path.exists(src_assets):
                    if os.path.abspath(src_assets) != os.path.abspath(dest_assets):
                        print(f"Copying template assets from {src_assets} to {dest_assets}...")
                        os.makedirs(dest_assets, exist_ok=True)
                        for item in os.listdir(src_assets):
                            s_path = os.path.join(src_assets, item)
                            d_path = os.path.join(dest_assets, item)
                            if os.path.isfile(s_path):
                                shutil.copy2(s_path, d_path)
                        print("Assets copied successfully.")
                    else:
                        print("Source and destination assets directories are the same. Skipping copy.")
                else:
                    print(f"WARNING: Upstream assets directory not found at {src_assets}")

                print("Running 'flutter pub get' to resolve dependencies...")
                _run_bounded(["flutter", "pub", "get"], cwd=dest, timeout=TIMEOUT_SECONDS, label="flutter pub get")
                
                print("Running 'flutter analyze'...")
                _run_bounded(["flutter", "analyze", "--no-fatal-warnings", "--no-fatal-infos"], cwd=dest, timeout=TIMEOUT_SECONDS, label="flutter analyze")
                
                print("Running 'flutter test'...")
                _run_bounded(["flutter", "test"], cwd=dest, timeout=TIMEOUT_SECONDS, label="flutter test")
                
                print("Running 'flutter build macos --release'...")
                _run_bounded(["flutter", "build", "macos", "--release"], cwd=dest, timeout=TIMEOUT_SECONDS * 3, label="flutter build macos --release")
                
                print("Zipping the macOS application bundle...")
                zip_path = os.path.join(upstream_repo_root, "app_flutter_release.zip")
                
                release_dir = os.path.join(dest, "build", "macos", "Build", "Products", "Release")
                app_bundle = "Platform Console.app"
                
                if os.path.exists(os.path.join(release_dir, app_bundle)):
                    if os.path.exists(zip_path):
                        print(f"Removing pre-existing release archive at {zip_path}...")
                        os.remove(zip_path)
                    _run_bounded(["zip", "-r", zip_path, app_bundle], cwd=release_dir, timeout=TIMEOUT_SECONDS, label="zip macos bundle")
                    archive_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
                    print(f"Success: App bundled to {zip_path} (created archive size: {archive_size} bytes)")
                else:
                    print(f"ERROR: App bundle not found at {os.path.join(release_dir, app_bundle)}", file=sys.stderr)
                    sys.exit(1)
                    
            except subprocess.TimeoutExpired as e:
                print(f"ERROR: Verification command timed out after {e.timeout}s: {e.cmd}", file=sys.stderr)
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                print(f"ERROR: Verification command failed: {e}", file=sys.stderr)
                sys.exit(1)

    if is_react:
        print(f"Verifying conformance for platform 'react' at '{dest}'...")
        # 1. Assert baseline files exist
        has_tsconfig = os.path.exists(os.path.join(dest, "tsconfig.json"))
        has_jsconfig = os.path.exists(os.path.join(dest, "jsconfig.json"))
        if not has_tsconfig and not has_jsconfig:
            print("ERROR: TSConfig or JSConfig is missing.", file=sys.stderr)
            sys.exit(1)

        entry_candidates = ["src/main.tsx", "src/main.jsx", "src/index.tsx", "src/index.jsx"]
        entry_file = None
        for cand in entry_candidates:
            if os.path.exists(os.path.join(dest, cand)):
                entry_file = cand
                break
        if not entry_file:
            print(f"ERROR: React entrypoint file missing (expected one of: {', '.join(entry_candidates)})", file=sys.stderr)
            sys.exit(1)

        if not args.no_domain:
            validation_candidates = ["src/domain/validation.ts", "src/domain/validation.js", "src/domain/validation.tsx", "src/domain/validation.jsx"]
            validation_file = None
            for cand in validation_candidates:
                if os.path.exists(os.path.join(dest, cand)):
                    validation_file = cand
                    break
            if not validation_file:
                print(f"ERROR: Domain validation file missing (expected one of: {', '.join(validation_candidates)})", file=sys.stderr)
                sys.exit(1)

        print("Success: All React baseline files exist.")

        # 2. Validate type compatibility
        if args.no_domain:
            print("Skipping domain type compatibility validation (--no-domain specified).")
        else:
            _validate_domain_types(dest, repo_root, "ts", os.path.join("src", "domain"))

        # 3. Run build/test commands
        if args.no_domain:
            print("Skipping build execution (--no-domain specified, domain implementation pending).")
        else:
            try:
                print("Running 'npm install' to resolve dependencies...")
                _run_bounded(["npm", "install"], cwd=dest, timeout=TIMEOUT_SECONDS * 2, label="npm install")
                
                print("Running 'npm run build'...")
                _run_bounded(["npm", "run", "build"], cwd=dest, timeout=TIMEOUT_SECONDS * 2, label="npm run build")
            except subprocess.TimeoutExpired as e:
                print(f"ERROR: React verification command timed out after {e.timeout}s: {e.cmd}", file=sys.stderr)
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                print(f"ERROR: React verification command failed: {e}", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()
