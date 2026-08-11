#!/usr/bin/env python3
"""
Subagent Output Integrity Validator & Escape Tokens Gate (Mechanism 3 & 4)

Verifies subagent output artifacts:
1. Non-zero file size
2. File creation proof (existence on filesystem)
3. Valid Mermaid diagram headers and closed code fences
4. Zero unreplaced {{REQUIRED_*}} escape tokens

Usage:
    python3 scripts/verify_subagent_output.py [--files file1 file2 ...] [--dir docs] [--report report.json]
"""

import argparse
import datetime
import json
import os
import re
import sys


VALID_MERMAID_HEADERS = (
    'classDiagram',
    'graph TD',
    'graph LR',
    'flowchart TD',
    'flowchart LR',
    'sequenceDiagram',
    'stateDiagram-v2',
    'stateDiagram',
    'erDiagram',
    'gantt',
    'pie',
)


def verify_file(file_path):
    check_result = {
        'file_path': str(file_path),
        'non_zero': False,
        'creation_proof': False,
        'escape_tokens_clear': True,
        'mermaid_valid': True,
        'issue_url_present': True
    }

    if not os.path.exists(file_path):
        return check_result, False

    check_result['creation_proof'] = True

    try:
        size = os.path.getsize(file_path)
        if size > 0:
            check_result['non_zero'] = True
        else:
            check_result['non_zero'] = False
            return check_result, False
    except OSError:
        return check_result, False

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Check unreplaced escape tokens
    if '{{REQUIRED_' in content:
        check_result['escape_tokens_clear'] = False

    # Check Mermaid diagrams if markdown file
    if file_path.endswith('.md'):
        mermaid_blocks = re.findall(r'```mermaid(.*?)```', content, re.DOTALL)
        # Also check for unclosed mermaid block
        open_fences = len(re.findall(r'```mermaid', content))
        closed_fences = len(re.findall(r'```mermaid.*?```', content, re.DOTALL))

        if open_fences != closed_fences:
            check_result['mermaid_valid'] = False

        for block in mermaid_blocks:
            stripped = block.strip()
            lines = [line.strip() for line in stripped.splitlines() if line.strip() and not line.strip().startswith('%%')]
            if not lines:
                check_result['mermaid_valid'] = False
                break
            first_line = lines[0]
            if not any(first_line.startswith(header) for header in VALID_MERMAID_HEADERS):
                check_result['mermaid_valid'] = False
                break

    is_pass = (
        check_result['non_zero'] and
        check_result['creation_proof'] and
        check_result['escape_tokens_clear'] and
        check_result['mermaid_valid']
    )

    return check_result, is_pass


def main():
    parser = argparse.ArgumentParser(description="Verify subagent output artifacts integrity.")
    parser.add_argument("--files", nargs="*", help="List of file paths to verify")
    parser.add_argument("--dir", help="Directory containing files to verify")
    parser.add_argument("--report", help="Path to write JSON report")
    args = parser.parse_args()

    target_files = []
    if args.files:
        target_files.extend(args.files)
    if args.dir and os.path.exists(args.dir):
        for root, _, files in os.walk(args.dir):
            for f in files:
                if f.endswith('.md'):
                    target_files.append(os.path.join(root, f))

    if not target_files:
        print("No files specified for verification.")
        sys.exit(0)

    checks = []
    overall_status = "PASS"

    for fpath in target_files:
        c_res, is_pass = verify_file(fpath)
        checks.append({
            'file_path': c_res['file_path'],
            'non_zero': c_res['non_zero'],
            'creation_proof': c_res['creation_proof'],
            'escape_tokens_clear': c_res['escape_tokens_clear']
        })
        if not is_pass:
            overall_status = "FAIL"

    report = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': overall_status,
        'checks': checks
    }

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as rf:
            json.dump(report, rf, indent=2)

    if overall_status == "PASS":
        print(f"Subagent output verification PASSED ({len(target_files)} files verified).")
        sys.exit(0)
    else:
        print(f"Subagent output verification FAILED ({len(target_files)} files checked).")
        sys.exit(42)


if __name__ == "__main__":
    main()
