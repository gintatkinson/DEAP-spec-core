#!/usr/bin/env python3
"""
Subagent Output Integrity Validator, Escape Tokens Gate, & Prompt Linter (Mechanism 3 & 4)

Verifies subagent output artifacts and prompt payloads:
1. Non-zero file size
2. File creation proof (existence on filesystem)
3. Valid Mermaid diagram headers and closed code fences
4. Zero unreplaced {{REQUIRED_*}} escape tokens
5. Mechanical validation of subagent prompt payloads (single-task atomicity, template match, zero inline issue body)

Usage:
    python3 scripts/verify_subagent_output.py [--files file1 file2 ...] [--dir docs] [--logs-dir dir] [--report report.json]
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from scripts.lint_subagent_prompt import (
        lint_prompt_payload,
        extract_prompts_from_transcript,
    )
except ImportError:
    repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root_dir not in sys.path:
        sys.path.insert(0, repo_root_dir)
    from scripts.lint_subagent_prompt import (
        lint_prompt_payload,
        extract_prompts_from_transcript,
    )


VALID_MERMAID_HEADERS = (
    'classDiagram',
    'graph TD',
    'graph LR',
    'graph TB',
    'graph BT',
    'graph RL',
    'flowchart TD',
    'flowchart LR',
    'flowchart TB',
    'flowchart BT',
    'flowchart RL',
    'sequenceDiagram',
    'stateDiagram-v2',
    'stateDiagram',
    'erDiagram',
    'gantt',
    'pie',
    'mindmap',
    'timeline',
)


def verify_file(file_path: str) -> Tuple[Dict[str, Any], bool]:
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


def verify_prompt_payload(prompt_text: str) -> Tuple[Dict[str, Any], bool]:
    """Validates prompt text payloads for untruncated skill directives and mechanical rules:
    1. Asserts presence of view_file on SKILL.md by explicit path as step 1.
    2. Asserts presence of gh issue create for audit skills.
    3. Rejects summarized or truncated prompt payloads.
    4. Forbids gh issue close in agent prompts (reserved for Product Owner review).
    5. Executes mechanical prompt payload linter (lint_prompt_payload).
    
    Returns (check_result_dict, is_pass_bool)
    """
    check_result = {
        'view_file_step_1': False,
        'audit_issue_create': True,
        'untruncated': True,
        'forbid_issue_close': True,
        'mechanical_linter_pass': True,
        'reasons': []
    }

    if not prompt_text or not isinstance(prompt_text, str):
        check_result['untruncated'] = False
        check_result['reasons'].append("Prompt payload is empty or not a string.")
        return check_result, False

    # Check for truncation / summarization indicators
    truncation_patterns = [
        r'\[\s*\.\.\.\s*\]',
        r'\[\s*summarized?\s*\]',
        r'\[\s*truncated?\s*\]',
        r'\bsummarized\s+(?:prompt|instructions?|directives?|payload)\b',
        r'\btruncated\s+(?:prompt|instructions?|directives?|payload)\b',
        r'\bsummary\s+of\s+skill\b',
        r'\bshortcut\b',
        r'\bsee\s+skill\s+for\s+details\b',
        r'\bsee\s+SKILL\.md\s+for\s+details\b',
    ]
    for pat in truncation_patterns:
        if re.search(pat, prompt_text, re.IGNORECASE):
            check_result['untruncated'] = False
            check_result['reasons'].append(f"Prompt payload contains truncation/summarization indicator matching '{pat}'.")

    # Forbid gh issue close in agent prompts
    if re.search(r'\bgh\s+issue\s+close\b', prompt_text, re.IGNORECASE):
        check_result['forbid_issue_close'] = False
        check_result['reasons'].append("Prompt payload contains forbidden 'gh issue close' (issue closure is reserved for Product Owner review).")

    # Assert presence of view_file on SKILL.md by explicit path as step 1
    has_view_file = 'view_file' in prompt_text
    has_skill_md = 'SKILL.md' in prompt_text
    step1_match = re.search(
        r'(?:step\s*1|very\s*first\s*step|first\s*step|as\s*its\s*very\s*first\s*step).*view_file.*SKILL\.md|view_file.*SKILL\.md.*(?:step\s*1|very\s*first\s*step|first\s*step|as\s*its\s*very\s*first\s*step)',
        prompt_text,
        re.IGNORECASE | re.DOTALL
    )
    if has_view_file and has_skill_md and step1_match:
        check_result['view_file_step_1'] = True
    else:
        check_result['reasons'].append("Prompt payload missing explicit view_file on SKILL.md as step 1.")

    # Asserts presence of gh issue create for audit skills
    if re.search(r'\baudits?\b|\bauditor\b', prompt_text, re.IGNORECASE):
        if 'gh issue create' in prompt_text:
            check_result['audit_issue_create'] = True
        else:
            check_result['audit_issue_create'] = False
            check_result['reasons'].append("Audit skill prompt missing 'gh issue create'.")

    # Execute mechanical prompt payload linter
    linter_violations = lint_prompt_payload(prompt_text)
    if linter_violations:
        check_result['mechanical_linter_pass'] = False
        check_result['reasons'].extend(linter_violations)

    is_pass = (
        check_result['view_file_step_1'] and
        check_result['audit_issue_create'] and
        check_result['untruncated'] and
        check_result['forbid_issue_close'] and
        check_result['mechanical_linter_pass']
    )
    return check_result, is_pass


def scan_transcript_logs(logs_dir: Optional[str] = None) -> Tuple[List[Dict[str, Any]], bool]:
    """Scans active transcript logs in .system_generated/logs/ (or specified logs_dir)
    for invoke_subagent prompt payloads and executes lint_prompt_payload on each payload.

    Returns:
        (results_list, is_all_passed)
    """
    if logs_dir is None:
        # Check standard default locations
        cwd_logs = os.path.join(os.getcwd(), ".system_generated", "logs")
        script_repo_logs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".system_generated", "logs")
        if os.path.isdir(cwd_logs):
            logs_dir = cwd_logs
        elif os.path.isdir(script_repo_logs):
            logs_dir = script_repo_logs
        else:
            return [], True

    if not os.path.isdir(logs_dir):
        return [], True

    results: List[Dict[str, Any]] = []
    all_passed = True

    # Find transcript files (.jsonl, .log, .json)
    for root, _, files in os.walk(logs_dir):
        for fname in sorted(files):
            if fname.endswith(('.jsonl', '.log', '.json')):
                fpath = os.path.join(root, fname)
                try:
                    prompts = extract_prompts_from_transcript(fpath)
                    for line_no, prompt_text in prompts:
                        violations = lint_prompt_payload(prompt_text)
                        passed = (len(violations) == 0)
                        if not passed:
                            all_passed = False
                        results.append({
                            'file_path': fpath,
                            'line_number': line_no,
                            'passed': passed,
                            'violations': violations,
                            'prompt_preview': prompt_text.strip()[:120] + "..." if len(prompt_text.strip()) > 120 else prompt_text.strip()
                        })
                except Exception as e:
                    all_passed = False
                    results.append({
                        'file_path': fpath,
                        'line_number': 0,
                        'passed': False,
                        'violations': [f"Error reading transcript: {e}"],
                        'prompt_preview': ""
                    })

    return results, all_passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify subagent output artifacts integrity and prompt payload quality gates."
    )
    parser.add_argument("--files", nargs="*", help="List of file paths to verify")
    parser.add_argument("--dir", help="Directory containing files to verify")
    parser.add_argument("--logs-dir", help="Directory containing transcript logs to scan (default: .system_generated/logs if present)")
    parser.add_argument("--scan-transcripts", action="store_true", help="Explicitly scan active transcripts in .system_generated/logs/")
    parser.add_argument("--transcripts", nargs="*", help="Specific transcript files to scan")
    parser.add_argument("--prompt", "--prompts", nargs="*", help="List of prompt strings or file paths containing prompt text to verify")
    parser.add_argument("--report", help="Path to write JSON report")
    args = parser.parse_args()

    target_files: List[str] = []
    if args.files:
        target_files.extend(args.files)
    if args.dir and os.path.exists(args.dir):
        for root, _, files in os.walk(args.dir):
            for f in files:
                if f.endswith('.md'):
                    target_files.append(os.path.join(root, f))

    prompt_inputs: List[str] = []
    if args.prompt:
        prompt_inputs.extend(args.prompt)

    # Determine transcript scanning target
    logs_dir = args.logs_dir
    transcript_files: List[str] = []
    if args.transcripts:
        transcript_files.extend(args.transcripts)

    transcript_results: List[Dict[str, Any]] = []
    transcripts_passed = True

    # Scan explicit transcript files if provided
    if transcript_files:
        for tpath in transcript_files:
            if os.path.isfile(tpath):
                prompts = extract_prompts_from_transcript(tpath)
                for line_no, prompt_text in prompts:
                    violations = lint_prompt_payload(prompt_text)
                    passed = (len(violations) == 0)
                    if not passed:
                        transcripts_passed = False
                    transcript_results.append({
                        'file_path': tpath,
                        'line_number': line_no,
                        'passed': passed,
                        'violations': violations,
                        'prompt_preview': prompt_text.strip()[:120] + "..." if len(prompt_text.strip()) > 120 else prompt_text.strip()
                    })

    # Auto-scan or scan specified logs directory
    scanned_results, scanned_passed = scan_transcript_logs(logs_dir)
    transcript_results.extend(scanned_results)
    if not scanned_passed:
        transcripts_passed = False

    if not target_files and not prompt_inputs and not transcript_results:
        print("No files, prompts, or active transcript logs specified for verification.")
        sys.exit(0)

    checks: List[Dict[str, Any]] = []
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

    for p_in in prompt_inputs:
        p_text = p_in
        if os.path.isfile(p_in):
            with open(p_in, 'r', encoding='utf-8', errors='replace') as pf:
                p_text = pf.read()
        p_res, is_pass = verify_prompt_payload(p_text)
        checks.append({
            'prompt_input': p_in,
            'view_file_step_1': p_res['view_file_step_1'],
            'audit_issue_create': p_res['audit_issue_create'],
            'untruncated': p_res['untruncated'],
            'forbid_issue_close': p_res['forbid_issue_close'],
            'mechanical_linter_pass': p_res['mechanical_linter_pass'],
            'reasons': p_res['reasons']
        })
        if not is_pass:
            overall_status = "FAIL"

    if not transcripts_passed:
        overall_status = "FAIL"

    # Print transcript check details
    if transcript_results:
        print(f"\nSubagent Prompt Transcript Validation: {len(transcript_results)} prompt(s) evaluated.")
        for tr in transcript_results:
            loc = f"{os.path.basename(tr['file_path'])}:L{tr['line_number']}"
            if tr['passed']:
                print(f"  [PASS] {loc}: {tr['prompt_preview']}")
            else:
                print(f"  [FAIL] {loc}: {tr['prompt_preview']}")
                for v in tr['violations']:
                    print(f"    - {v}")

    report = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': overall_status,
        'checks': checks,
        'transcript_checks': transcript_results
    }

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as rf:
            json.dump(report, rf, indent=2)

    if overall_status == "PASS":
        print(f"\nSubagent output verification PASSED ({len(target_files)} files, {len(prompt_inputs)} prompts, {len(transcript_results)} transcript prompt checks).")
        sys.exit(0)
    else:
        print(f"\nSubagent output verification FAILED ({len(target_files)} files, {len(prompt_inputs)} prompts, {len(transcript_results)} transcript prompt checks).")
        sys.exit(1)


if __name__ == "__main__":
    main()
