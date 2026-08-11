#!/usr/bin/env python3
# Copyright Gint Atkinson, gint.atkinson@gmail.com

"""
Backlog reconciliation script that synchronises local markdown spec files
with an external issue tracker (e.g. GitHub Issues).

Scans epics/, features/, user-stories/ and use-cases/ directories,
resolves issue-ID placeholders, updates dependency checklists, syncs
issue bodies, and marks completed items Fixed / Resolved.
A spec file is matched to its issue by the canonical `issue_id` in its YAML
frontmatter; normalized-title matching is a warning-only fallback for a spec
that has none yet.  See resolve_spec_issue_number and
constitution.md:57-59 § Unique Backlog Identifiers (#314, #316).
Never closes an issue: constitution.md:161 reserves Closed for Product Owner
validation (#309).  Hard-exits on any
referenced issue that does not exist in the tracker (hallucination gate).
"""

#!/usr/bin/env python3
import os
import re
import subprocess
import json
import sys
import yaml
import traceback
import shutil

def sanitize_github_token_env():
    """
    Sanitize environment by removing dummy or placeholder GITHUB_TOKEN and GH_TOKEN
    values that interfere with git/gh terminal operations.
    """
    dummy_keywords = ("antigravity", "dummy", "placeholder", "invalid", "mock")
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(var)
        if val and any(kw in val.lower() for kw in dummy_keywords):
            os.environ.pop(var, None)

sanitize_github_token_env()

def load_codebase_rules(workspace_dir):
    rules_path = os.path.join(workspace_dir, ".pipeline", "logical-ui", "codebase_rules.json")
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load codebase_rules.json: {e}")
    return {}

def get_git_remote_repo(workspace_dir):
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        url = res.stdout.strip()
        if url.endswith(".git"):
            url = url[:-4]
        if "github.com" in url:
            url = re.split(r'github\.com[:/]', url)[-1]
        parts = url.split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
    except Exception as e:
        print(f"Warning: Failed to auto-detect git remote: {e}")
    return None

def get_upstream_repository(rules, workspace_dir):
    env_repo = os.environ.get("UPSTREAM_REPOSITORY") or os.environ.get("GIT_REMOTE_ORIGIN")
    if env_repo:
        return env_repo
    git_repo = get_git_remote_repo(workspace_dir)
    if git_repo:
        return git_repo
    if rules and isinstance(rules, dict):
        return rules.get("meta", {}).get("upstream_repository", "gintatkinson/digital-pipeline-repo")
    return "gintatkinson/digital-pipeline-repo"

def format_issue_reference(issue_id, tracker_rules):
    issue_id_str = str(issue_id)
    if issue_id_str.isdigit():
        prefix = tracker_rules.get("numeric_prefix", "#")
        return f"{prefix}{issue_id_str}"
    else:
        prefix = tracker_rules.get("alphanumeric_prefix", "")
        return f"{prefix}{issue_id_str}"

def normalize_title(title, rules=None):
    if not title:
        return ""
    # Strip quotes and leading/trailing whitespace
    title = title.strip().strip('"\'')
    # Strip common prefixes (e.g., epic-01:, feat-02:, us-03:, uc-04:, etc.)
    regex = r'^(epic|feature|feat|user[- ]story|use[- ]case|us|uc)[s]?(?:[- ]*\d+)?\s*[:\-]?\s*'
    stripped = re.sub(regex, '', title, flags=re.IGNORECASE)
    if stripped.strip():
        title = stripped
    # Normalize hyphens to spaces to handle typographic variations
    title = title.replace("-", " ")
    # Strip any remaining punctuation and normalize spacing
    title = re.sub(r'[^\w\s]', '', title)
    title = " ".join(title.split())
    return title.lower()


def normalize_spec_slug(title, rules=None):
    """
    Standardized slugification that preserves stop words.
    Converts 'Fiber Cable and Strand Inventory' to 'fiber-cable-and-strand-inventory'.
    """
    if not title:
        return ""
    # Strip quotes and leading/trailing whitespace
    title = title.strip().strip('"\'')
    # Strip common prefixes
    regex = r'^(epic|feature|feat|user[- ]story|use[- ]case|us|uc)[s]?(?:[- ]*\d+)?\s*[:\-]?\s*'
    stripped = re.sub(regex, '', title, flags=re.IGNORECASE)
    if stripped.strip():
        title = stripped
    # Normalize hyphens to spaces to handle typographic variations
    title = title.replace("-", " ")
    # Strip any remaining punctuation and normalize spacing
    title = re.sub(r'[^\w\s]', '', title)
    # Join with hyphens to form a slug, preserving all words
    title = "-".join(title.split())
    return title.lower()


def normalize_label(label):
    """Reduce a tracker label to the form every label comparison happens in (#329).

    The reconciler compared labels for exact equality, so an issue filed with
    `"User Story"` lowercased to `"user story"`, never matched the configured
    `"user-story"`, was bucketed nowhere, and stayed orphaned while its specification
    reported "no issue on the tracker". Case and word separators are presentation, not
    identity: `"User Story"`, `"user story"` and `"user_story"` all name one label.

    Only whitespace, underscores and hyphens fold. A namespaced label such as
    `status:fixed-resolved` keeps its colon, because that *is* part of the name.

    #313 (package N3) introduced `issue_has_label` with deliberately exact matching and
    recorded case-insensitivity as belonging to this issue. Every comparison site in the
    module now routes through here so there is one rule rather than two.
    """
    if not label:
        return ""
    text = str(label).strip().lower()
    if not text:
        return ""
    return re.sub(r"[\s_\-]+", "-", text).strip("-")


# The spec type a reference declares about itself, keyed by the spelling found. The
# values are the constitutional type names; `SPEC_TYPE_ALIASES` is consulted only with a
# separator-folded key, so one entry covers "User Story", "user-story" and "user_story".
SPEC_TYPE_ALIASES = {
    "epic": "epic",
    "epics": "epic",
    "feature": "feature",
    "features": "feature",
    "feat": "feature",
    "user story": "user-story",
    "user stories": "user-story",
    "us": "user-story",
    "use case": "use-case",
    "use cases": "use-case",
    "uc": "use-case",
}

# A type word only marks a type when a separator, a digit or the end of the reference
# follows it. Without that boundary `us` would claim "User Access Control" and `uc`
# would claim "UCS Migration" — the same over-eager prefix stripping that produced #319
# in the first place, reintroduced in the code meant to contain it.
_REFERENCE_TYPE_RE = re.compile(
    r'^\s*["\'#]*\s*'
    r'(?P<type>epics?|features?|feat|user[-_ ]?stor(?:y|ies)|use[-_ ]?cases?|us|uc)'
    r'(?=[\s\-_:.#]|\d|$)',
    re.IGNORECASE,
)


def spec_type_of_reference(reference):
    """The spec type a reference names explicitly, or None when it is type-neutral.

    `"feat-07-geo-location"` declares itself a Feature; `"Geo Location"` and `"#101"`
    declare nothing. This is the namespace discriminator #319 asks for: entity
    resolution must isolate namespaces by entity type, and a reference that names its
    own type is the only evidence available for doing so.
    """
    if reference is None:
        return None
    match = _REFERENCE_TYPE_RE.match(str(reference))
    if not match:
        return None
    key = re.sub(r"[\s\-_]+", " ", match.group("type").strip().lower())
    return SPEC_TYPE_ALIASES.get(key)


def extract_title(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2048)  # Read first 2KB
        
        # Try finding title in YAML frontmatter
        title_match = re.search(r'^title:\s*(["\']?)(.*?)\1\s*$', content, re.MULTILINE)
        if title_match:
            return title_match.group(2).strip()
            
        # Fallback to # H1 title
        h1_match = re.search(r'^#\s+(.*?)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
    except Exception as e:
        print(f"Error reading title from {filepath}: {e}")
    return None

def extract_epic_from_body(body_content):
    """
    Extracts the parent epic reference (filename, slug, or issue ID) from markdown body content.
    """
    if not body_content:
        return None
        
    # 1. Search for any markdown link pointing to an epic file under /epics/ or epics/ or starting with epic-
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body_content)
    for link_text, link_url in links:
        url_lower = link_url.lower()
        if "epics/" in url_lower or "epic-" in url_lower:
            filename = os.path.basename(link_url)
            if filename.endswith(".md"):
                filename = filename[:-3]
            if "epic" in filename.lower():
                return filename
            if "epic" in link_text.lower():
                return link_text

    # 2. Line-by-line scanning for "Parent Epic" heading/section or inline references
    lines = body_content.splitlines()
    parent_epic_section = False
    for line in lines:
        line_stripped = line.strip()
        if re.search(r'^#+\s+Parent\s+Epic', line_stripped, re.IGNORECASE):
            parent_epic_section = True
            continue
        
        is_parent_epic_line = "parent epic" in line_stripped.lower()
        if parent_epic_section or is_parent_epic_line:
            # Check for issue ID first (e.g. #101)
            issue_match = re.search(r'#(\d+)\b', line_stripped)
            if issue_match:
                return issue_match.group(0)
                
            # Check for issue ID placeholder with potential link (e.g. - [ ] #[EpicID] - [Title](../epics/epic-01.md))
            placeholder_match = re.search(r'#\[EpicIssueID\]|#\[EpicID\]', line_stripped, re.IGNORECASE)
            if placeholder_match:
                link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line_stripped)
                if link_match:
                    link_text, link_url = link_match.groups()
                    filename = os.path.basename(link_url)
                    if filename.endswith(".md"):
                        filename = filename[:-3]
                    return filename
            
            # Check for generic markdown link in Parent Epic line/section
            link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line_stripped)
            if link_match:
                link_text, link_url = link_match.groups()
                filename = os.path.basename(link_url)
                if filename.endswith(".md"):
                    filename = filename[:-3]
                return filename
                
            # Check for explicit text pattern e.g. "Parent Epic: epic-01-geo-location"
            val_match = re.search(r'(?:parent\s+epic\s*[:\-]\s*|\*\*\s*parent\s+epic\s*\*\*\s*[:\-]\s*)([^\n]+)', line_stripped, re.IGNORECASE)
            if val_match:
                val = val_match.group(1).strip().strip('[]-* ')
                if val:
                    return val
            
            # If we hit another heading, stop section scan
            if parent_epic_section and line_stripped.startswith('#'):
                parent_epic_section = False
                
    # 3. Global fallback scan for "Parent Epic" inline references
    for line in lines:
        line_stripped = line.strip()
        if "parent epic" in line_stripped.lower():
            link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line_stripped)
            if link_match:
                link_text, link_url = link_match.groups()
                filename = os.path.basename(link_url)
                if filename.endswith(".md"):
                    filename = filename[:-3]
                return filename
            issue_match = re.search(r'#(\d+)\b', line_stripped)
            if issue_match:
                return issue_match.group(0)
                
    return None

def get_all_issues(rules=None):
    if not rules:
        raise ValueError("Configuration rules are missing.")
    tracker_rules = rules.get("tracker_rules")
    if not tracker_rules:
        raise ValueError("Missing 'tracker_rules' in codebase_rules.json")
    provider = tracker_rules.get("provider")
    if not provider:
        raise ValueError("Missing 'tracker_rules.provider' in codebase_rules.json")
    commands = tracker_rules.get("commands")
    if not commands or "list_issues" not in commands:
        raise ValueError("Missing 'tracker_rules.commands.list_issues' in codebase_rules.json")
    
    print(f"Fetching active and closed issues from tracker provider '{provider}'...")
    cmd = commands["list_issues"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise Exception(f"Failed to fetch issues: {res.stderr.strip()}")
    return json.loads(res.stdout)

def update_checklist_in_file(filepath, issue_dict, rules=None):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    pattern = tracker_rules.get("dependency_regex", r"(-\s*\[\s*([ xX])\s*\]\s*(#|#\[|\#\s*)?([A-Za-z0-9\-]+))")
    PLACEHOLDER_PATTERN = re.compile(r'^(IssueID|EpicIssueID|StoryIssueID|FeatureIssueID|UseCaseIssueID|StoryID|N/A)\]?$')
    
    updated_content = content
    all_deps_closed = True
    has_deps = False
    
    keys = tracker_rules.get("keys", {})
    state_key = keys.get("state", "state")
    closed_state = keys.get("closed_state_value", "CLOSED").upper()
    
    matches = re.findall(pattern, content)
    for match_tuple in matches:
        # Support variable number of groups depending on user-configured regex
        if isinstance(match_tuple, str):
            full_match = match_tuple
            mark = ' '
            prefix = ''
            dep_num_str = match_tuple
        else:
            full_match = match_tuple[0]
            mark = match_tuple[1]
            prefix = match_tuple[2] if len(match_tuple) > 2 else ''
            dep_num_str = match_tuple[3] if len(match_tuple) > 3 else match_tuple[-1]

        # 1. Skip plain markdown checkboxes that have no issue reference prefix
        if not prefix:
            continue

        # 2. Skip unresolved template placeholders
        if isinstance(dep_num_str, str) and PLACEHOLDER_PATTERN.match(dep_num_str):
            ref_str = format_issue_reference(dep_num_str, tracker_rules)
            print(f"  [Deferred] Unresolved placeholder {ref_str} in {os.path.basename(filepath)} — skipping")
            continue
        has_deps = True
        dep_num = int(dep_num_str) if dep_num_str.isdigit() else dep_num_str
        dep_issue = issue_dict.get(dep_num)
        
        if dep_issue is None:
            ref_str = format_issue_reference(dep_num, tracker_rules)
            print(f"  [Warning] Dependency {ref_str} not found in tracker for {os.path.basename(filepath)} — skipping item")
            continue
            
        is_closed = (str(dep_issue[state_key]).upper() == closed_state)
        target_mark = 'x' if is_closed else ' '
        
        if mark != target_mark:
            # Replace the specific checkbox character
            old_box = f"[{mark}]"
            new_box = f"[{target_mark}]"
            updated_content = updated_content.replace(full_match, full_match.replace(old_box, new_box, 1), 1)
            ref_str = format_issue_reference(dep_num, tracker_rules)
            print(f"  [Checklist] Updated dependency {ref_str} to [{target_mark}] in {os.path.basename(filepath)}")
            
        if not is_closed:
            all_deps_closed = False

    if updated_content != content:
        updated_content = write_markdown_file(filepath, updated_content)
            
    return updated_content, (has_deps and all_deps_closed)

def convert_frontmatter_to_table(content):
    if not content.startswith("---"):
        return content
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
        
    frontmatter_text = parts[1]
    body_text = parts[2].lstrip()
    
    try:
        data = yaml.safe_load(frontmatter_text.replace('\x01', ''))
        if not isinstance(data, dict):
            return content
    except Exception as e:
        print(f"Error parsing frontmatter YAML: {e}")
        return content
    
    table_lines = [
        "| Metadata | Value |",
        "| --- | --- |"
    ]
    
    for key, value in data.items():
        if isinstance(value, list):
            val = ", ".join(str(item) for item in value)
        elif value is None:
            val = ""
        else:
            val = str(value)
        
        val = val.replace('\n', '<br>').replace('|', '\\|')
        key_str = str(key).replace('\n', '<br>').replace('|', '\\|')
        table_lines.append(f"| **{key_str}** | {val} |")
        
    table_text = "\n".join(table_lines) + "\n\n"
    return table_text + body_text

def deduplicate_markdown_sections(content):
    lines = content.splitlines()
    seen_headers = set()
    output_lines = []
    skip_section = False
    for line in lines:
        header_match = re.match(r'^(#+)\s+(.*)$', line)
        if header_match:
            header_level = header_match.group(1)
            header_title = header_match.group(2).strip().lower()
            norm_title = re.sub(r'^\d+\.\s*', '', header_title)
            section_key = f"{header_level} {norm_title}"
            if section_key in seen_headers:
                skip_section = True
            else:
                seen_headers.add(section_key)
                skip_section = False
        if not skip_section:
            output_lines.append(line)
    return "\n".join(output_lines) + "\n"

def rewrite_header_repository_urls(content, active_repo):
    if not content or not active_repo:
        return content
    parts = active_repo.split('/')
    active_name = parts[-1].lower()
    active_owner = parts[0].lower() if len(parts) > 1 else ""

    def replacer(match):
        full_url = match.group(0)
        url_owner = match.group(1)
        url_repo = match.group(2)
        url_owner_lower = url_owner.lower()
        url_repo_lower = url_repo.lower()

        is_target_repo = (
            (url_owner_lower == active_owner and url_repo_lower == active_name) or
            (url_repo_lower == active_name) or
            (url_repo_lower == "digital-pipeline-repo") or
            ("pipeline-repo" in url_repo_lower)
        )

        if is_target_repo:
            return f"https://github.com/{active_repo}/blob/"
        return full_url

    pattern = r'https://github\.com/([^/]+)/([^/]+)/blob/'
    return re.sub(pattern, replacer, content)

def sanitize_source_references(content, workspace_dir=None, rules=None):
    if not content:
        return content

    if workspace_dir is None:
        workspace_dir = find_workspace_dir(os.getcwd())

    upstream_repo = get_upstream_repository(rules, workspace_dir) or "gintatkinson/digital-pipeline-repo"
    content = rewrite_header_repository_urls(content, upstream_repo)
    branch = get_current_branch(workspace_dir)
    if not branch or branch == "HEAD":
        branch = "main"

    github_base = f"https://github.com/{upstream_repo}/blob/{branch}"

    abs_workspace = os.path.abspath(workspace_dir).rstrip("/\\")
    real_workspace = os.path.realpath(workspace_dir).rstrip("/\\")
    repo_name = upstream_repo.split("/")[-1] if "/" in upstream_repo else upstream_repo

    def replacer(match):
        full_uri = match.group(0)
        path_part = match.group(1)

        if abs_workspace != "/" and path_part.startswith(abs_workspace):
            rel = path_part[len(abs_workspace):].lstrip("/")
            return f"{github_base}/{rel}"
        elif real_workspace != "/" and path_part.startswith(real_workspace):
            rel = path_part[len(real_workspace):].lstrip("/")
            return f"{github_base}/{rel}"

        repo_substr = f"/{repo_name}/"
        if repo_substr in path_part:
            rel = path_part.split(repo_substr, 1)[1]
            return f"{github_base}/{rel}"

        parts = path_part.split("/")
        if len(parts) > 3 and parts[1] in ("Users", "home"):
            rel = "/".join(parts[3:])
            return f"{github_base}/{rel}"

        return full_uri

    pattern = r'file://(/[^\s\)\>"\']+)'
    return re.sub(pattern, replacer, content)

def sanitize_mermaid_diagrams(content):
    if not content or "```mermaid" not in content:
        return content

    lines = content.splitlines()
    in_mermaid = False
    sanitized_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```mermaid"):
            in_mermaid = True
            sanitized_lines.append(line)
            i += 1
            continue
        elif in_mermaid and stripped.startswith("```"):
            in_mermaid = False
            sanitized_lines.append(line)
            i += 1
            continue

        if in_mermaid and i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.strip()
            if not next_stripped.startswith("```"):
                arrow_match = re.search(r'(-+>+|=+>+|--|-\.->?|-\.)\s*$', stripped)
                starts_with_gt = next_stripped.startswith('>')

                if arrow_match or starts_with_gt:
                    arrow_op = arrow_match.group(1) if arrow_match else ""
                    rest_next = next_stripped

                    if starts_with_gt:
                        if arrow_op == "->":
                            line = re.sub(r'->\s*$', '->>', line)
                        elif arrow_op == "--":
                            line = re.sub(r'--\s*$', '-->', line)
                        rest_next = re.sub(r'^>\s*', '', next_stripped)

                    joined = f"{line.rstrip()} {rest_next}"
                    sanitized_lines.append(joined)
                    i += 2
                    continue

        sanitized_lines.append(line)
        i += 1

    return "\n".join(sanitized_lines) + ("\n" if content.endswith("\n") else "")

def write_markdown_file(filepath, content, workspace_dir=None, rules=None):
    if workspace_dir is None:
        workspace_dir = find_workspace_dir(filepath)
    sanitized_content = sanitize_source_references(content, workspace_dir=workspace_dir, rules=rules)
    sanitized_content = sanitize_mermaid_diagrams(sanitized_content)
    deduped_content = deduplicate_markdown_sections(sanitized_content)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(deduped_content)
    return deduped_content

DEFAULT_STRUCTURAL_LABELS = {
    "epic": "epic",
    "feature": "feature",
    "user_story": "user-story",
    "use_case": "use-case",
}

STRUCTURAL_LABEL_DESCRIPTION_TEMPLATE = (
    "{item_type} specification item, applied by the backlog reconciler."
)


def structural_label_key(issue_type):
    """Reduce an item type ("User Story") to its `tracker_rules.labels` key.

    The four spec loops name their type in prose; the configuration keys it in snake
    case. Deriving one from the other keeps the taxonomy in a single place — the
    configuration — instead of restating it at four call sites.
    """
    return re.sub(r"[\s\-]+", "_", str(issue_type or "").strip().lower())


def get_structural_label(issue_type, rules=None):
    """The configured tracker label for an item type, or None if it has none.

    `.pipeline/constitution.md:93-95` § *Labeling Taxonomy* fixes exactly four label
    types "or as defined by the issue tracker configuration", so the names are read
    from `tracker_rules.labels` and never hardcoded here (#313). The module-level
    default exists only so a configuration predating this key still labels correctly,
    mirroring how `get_resolved_label` defaults.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    key = structural_label_key(issue_type)
    labels = tracker_rules.get("labels", {})
    return labels.get(key) or DEFAULT_STRUCTURAL_LABELS.get(key)


def issue_has_label(issue_record, label):
    """Does this tracker record already carry `label`?

    Tracker payloads express labels either as objects with a "name" or as bare strings,
    so both are accepted — the same shapes `is_already_resolved` handles.

    Comparison folds case and word separators through `normalize_label` (#329). It was
    exact when #313 added this function, which meant an issue already carrying
    `"User Story"` was re-labelled on every run; the module now has one comparison rule.
    """
    target = normalize_label(label)
    if not target:
        return False
    for item in (issue_record or {}).get("labels") or []:
        name = item.get("name", "") if isinstance(item, dict) else str(item)
        if normalize_label(name) == target:
            return True
    return False


def sync_issue_title_to_tracker(issue_num, filepath, rules=None, issue_record=None):
    """Push the frontmatter title to the tracker when the two have drifted (#315).

    Tracker issues are created with a generic title derived from the schema node, while
    the spec's YAML `title` is refined afterwards; nothing ever pushed the refined value
    back, so the two diverged permanently and normalized-title matching gained
    collisions it need not have had.

    The edit is issued **only when the titles actually differ**. `AGENTS.md` § *Backlog
    Reconciliation Mandate* runs this script before every merge, so an unconditional
    edit would rewrite an unchanged title on every run and bury real changes in tracker
    noise. When no tracker record is available the title is sent, because correctness of
    the sync outranks the noise it costs.

    Returns True when an edit was issued.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    title = extract_title(filepath)
    if not title:
        return False

    keys = tracker_rules.get("keys", {})
    current_title = (issue_record or {}).get(keys.get("title", "title"))
    if current_title is not None and str(current_title) == title:
        return False

    template = tracker_rules.get("commands", {}).get("edit_issue_title")
    if not template:
        print(
            "  [Warning] No 'tracker_rules.commands.edit_issue_title' configured; the "
            f"tracker title for {format_issue_reference(issue_num, tracker_rules)} will "
            "stay out of sync with the specification frontmatter (#315).",
            file=sys.stderr,
        )
        return False

    cmd = [
        str(issue_num) if c == "{number}" else (title if c == "{title}" else c)
        for c in template
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    return True


def apply_structural_label(issue_num, issue_type, rules=None, issue_record=None):
    """Apply the configured structural label for this item type (#313).

    Bootstrapping reuses the `create_label` command #309 added — `--force` makes it a
    no-op where the label already exists — because a fresh downstream repository has no
    such label and applying one that does not exist fails the sync. This is the same
    just-in-time provisioning #309 established; making it install-time is issue #323 and
    is not attempted here.

    Idempotent: an issue already carrying the label produces no tracker traffic at all,
    and neither bootstrap nor application changes anything when repeated.

    Returns True when the label was applied.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    commands = tracker_rules.get("commands", {})
    label = get_structural_label(issue_type, rules)
    if not label:
        print(
            f"  [Warning] No structural label configured for item type '{issue_type}' "
            "in tracker_rules.labels; skipping (#313).",
            file=sys.stderr,
        )
        return False

    if issue_has_label(issue_record, label):
        return False

    create_template = commands.get("create_label")
    if create_template:
        description = STRUCTURAL_LABEL_DESCRIPTION_TEMPLATE.format(item_type=issue_type)
        cmd = [
            label if c == "{label}" else (description if c == "{description}" else c)
            for c in create_template
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

    add_template = commands.get("add_label") or commands.get("resolve_issue")
    if not add_template:
        print(
            "  [Warning] No 'tracker_rules.commands.add_label' configured; structural "
            f"label '{label}' cannot be applied to "
            f"{format_issue_reference(issue_num, tracker_rules)} (#313).",
            file=sys.stderr,
        )
        return False

    cmd = [
        str(issue_num) if c == "{number}" else (label if c == "{label}" else c)
        for c in add_template
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    print(f"  [Sync Issue Body] Applied structural label '{label}'.")
    return True


def sync_issue_body_to_tracker(issue_num, filepath, issue_type="Feature", rules=None,
                               issue_record=None):
    """Push the specification to its tracker issue: body, title (#315) and label (#313).

    `issue_record` is the tracker's own payload for this issue, when the caller has it.
    It is what makes the two additions conditional rather than unconditional — the title
    is only re-sent when it differs, and the label only applied when it is absent.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    ref_str = format_issue_reference(issue_num, tracker_rules)
    print(f"  [Sync Issue Body] Syncing {ref_str} ({issue_type}) to tracker...")
    
    temp_path = filepath + ".temp-body"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        workspace_dir = find_workspace_dir(filepath)
        content = sanitize_source_references(content, workspace_dir=workspace_dir, rules=rules)
        content = sanitize_mermaid_diagrams(content)
        content = convert_frontmatter_to_table(content)
        content = deduplicate_markdown_sections(content)
            
        val_rules = rules.get("validation_rules", {}) if rules else {}
        max_body_chars = val_rules.get("max_body_characters", 65536)
        trunc_limit = max_body_chars - 5536
        
        if len(content) > trunc_limit:
            truncation_headers = tracker_rules.get("truncation_headers", ["## Acceptance Criteria", "## User Stories"])
            header_index = -1
            for header in truncation_headers:
                header_index = content.find(header)
                if header_index != -1:
                    break
            
            project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
            rel_path = os.path.relpath(filepath, project_root)
            
            truncation_template = tracker_rules.get("truncation_message_template", (
                "\n\n---\n*Warning: This issue body has been truncated because it exceeds the tracker size limit of {max_body_chars} characters.*\n"
                "*Please refer to the full specification file in the repository at `{rel_path}` for the complete details.*\n\n"
            )).format(max_body_chars=max_body_chars, rel_path=rel_path)
            
            if header_index != -1:
                preserved_tail = content[header_index:]
                avail_head_len = trunc_limit - len(preserved_tail) - len(truncation_template)
                if avail_head_len > 0:
                    content = content[:avail_head_len] + truncation_template + preserved_tail
                else:
                    content = content[:trunc_limit] + truncation_template
            else:
                content = content[:trunc_limit] + truncation_template
            
        with open(temp_path, "w", encoding="utf-8") as tf:
            tf.write(content)
        
        edit_cmd_template = tracker_rules.get("commands", {}).get("edit_issue")
        if not edit_cmd_template:
            raise ValueError("Missing 'tracker_rules.commands.edit_issue' in codebase_rules.json")
        cmd = [str(issue_num) if c == "{number}" else (temp_path if c == "{temp_path}" else c) for c in edit_cmd_template]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # The body is only part of the update. The tracker title drifts from the frontmatter
    # (#315) and generated issues carry no structural tier (#313); both are this call
    # site sending too little.
    sync_issue_title_to_tracker(issue_num, filepath, rules=rules, issue_record=issue_record)
    apply_structural_label(issue_num, issue_type, rules=rules, issue_record=issue_record)

RESOLVED_LABEL_DESCRIPTION = (
    "Dev complete, tests pass, merged to main. Awaiting Product Owner validation."
)


def get_resolved_label(rules=None):
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    return tracker_rules.get("labels", {}).get("resolved", "status:fixed-resolved")


def is_already_resolved(issue_record, rules=None):
    """Has this issue already been marked Fixed / Resolved?

    This guard replaces closing (#309). The call sites were gated on the issue being
    open, so closing it was what stopped the next run from acting again. Without a
    replacement guard the reconciler would re-post the completion comment on every run,
    and AGENTS.md requires a run before every merge.

    Tracker payloads express labels either as objects with a "name" or as bare strings,
    so both are accepted. Comparison folds through `normalize_label` for the same reason
    `issue_has_label` does (#329): a case variant read as "not resolved" would re-post
    the completion comment on the next run, which is exactly what this guard prevents.
    """
    label = normalize_label(get_resolved_label(rules))
    if not label:
        return False
    for item in (issue_record or {}).get("labels") or []:
        name = item.get("name", "") if isinstance(item, dict) else str(item)
        if normalize_label(name) == label:
            return True
    return False


def resolve_issue_on_tracker(issue_num, comment, rules=None):
    """Mark an issue Fixed / Resolved. Never closes it.

    `.pipeline/constitution.md:161` makes `Closed` unreachable without Product Owner
    validation. This function applies the resolved label and posts the evidence comment,
    leaving the issue open for that decision.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    commands = tracker_rules.get("commands", {})
    label = get_resolved_label(rules)
    ref_str = format_issue_reference(issue_num, tracker_rules)
    print(f"  [Resolve Issue] Marking {ref_str} Fixed / Resolved via label '{label}'...")

    # Bootstrap the label first — a downstream repository will not have it, and applying
    # a non-existent label fails. --force makes this idempotent where it already exists.
    create_template = commands.get("create_label")
    if create_template:
        cmd = [
            label if c == "{label}" else (RESOLVED_LABEL_DESCRIPTION if c == "{description}" else c)
            for c in create_template
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

    resolve_template = commands.get("resolve_issue")
    if not resolve_template:
        raise ValueError("Missing 'tracker_rules.commands.resolve_issue' in codebase_rules.json")
    cmd = [
        str(issue_num) if c == "{number}" else (label if c == "{label}" else c)
        for c in resolve_template
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)

    comment_template = commands.get("comment_issue")
    if comment_template and comment:
        cmd = [
            str(issue_num) if c == "{number}" else (comment if c == "{comment}" else c)
            for c in comment_template
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)

def blocked_specs_from_linter_output(output_text, workspace_dir, rules=None):
    """Specification files the linter rejected, from its output.

    Intersected with the files that actually exist in the backlog directories. A bare
    regex over the output also catches documents merely *cited* by a finding — a
    remediation note reading "see rules/document-references.md" made the reconciler
    skip the constitution, which it had never been asked to validate. Only items the
    linter genuinely rejected belong in the skip set (#321).
    """
    mentioned = set(re.findall(r"([\w.-]+\.md)", output_text or ""))
    if not mentioned:
        return set()

    backlog = (rules or {}).get("backlog_directories", {}) or {}
    spec_names = set()
    for key in ("epics", "features", "user_stories", "use_cases"):
        rel = backlog.get(key) if isinstance(backlog, dict) else getattr(backlog, key, None)
        if not rel:
            continue
        target = os.path.join(workspace_dir, rel)
        if os.path.isdir(target):
            spec_names.update(n for n in os.listdir(target) if n.endswith(".md"))
    return mentioned & spec_names


def get_current_branch(workspace_dir):
    res = subprocess.run(["git", "branch", "--show-current"], cwd=workspace_dir, capture_output=True, text=True, timeout=30)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace_dir, capture_output=True, text=True, timeout=30)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return "master"

def extract_metadata(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                data = yaml.safe_load(frontmatter_text.replace('\x01', ''))
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print(f"Error parsing metadata from {filepath}: {e}")
    return {}

def lookup_canonical_issue_key(raw_id, issue_dict):
    """Return the key under which `raw_id` sits in `issue_dict`, or None if absent.

    `issue_dict` is keyed twice per issue — once int, once str — because tracker
    payloads and frontmatter disagree about the type. Frontmatter may also quote the
    value or write it as a reference (`"901"`, `#901`), so all three spellings are
    reduced to the one key the caller can index with.
    """
    if raw_id is None or isinstance(raw_id, bool):
        return None
    if isinstance(raw_id, int):
        candidates = [raw_id, str(raw_id)]
    else:
        text = str(raw_id).strip().strip('"\'').lstrip("#").strip()
        if not text:
            return None
        candidates = [text, int(text)] if text.isdigit() else [text]
    for candidate in candidates:
        if candidate in issue_dict:
            return candidate
    return None


def resolve_spec_issue_number(filepath, title, title_map, issue_dict, rules=None,
                              item_type="Feature", claimed=None):
    """Resolve a local spec file to its tracker issue. Canonical `issue_id` first.

    `.pipeline/constitution.md:57-59` § *Unique Backlog Identifiers* mandates an
    `issue_id: <int>` in every spec's frontmatter and states that "Matching by title
    normalization is prohibited as a primary selector." This function is where that
    precedence is enforced (#314), and it is the only resolution path the four spec
    loops in main() use (#316).

    Order:

    1. Frontmatter `issue_id` present and on the tracker — used, full stop.
    2. Frontmatter `issue_id` present but absent from the tracker — **hard error**. A
       fall-through to title matching here is exactly #316: the title can match some
       unrelated issue, and `sync_issue_body_to_tracker` would then overwrite that
       issue's body. It is also the same class of defect as the referenced-but-missing
       issue the module already refuses to invent.
    3. No `issue_id` yet (first registration) — title normalization, with a warning
       naming the file, because the constitution allows it only as a fallback.

    `claimed` is an optional dict shared across all four loops. Two spec files
    resolving to one issue number means one of them is about to be overwritten, so it
    fails loudly with both paths rather than syncing.
    """
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    meta = extract_metadata(filepath)
    fm_id = meta.get("issue_id")
    basename = os.path.basename(filepath)

    declared = str(fm_id).strip().strip('"\'').lstrip("#").strip() if fm_id is not None else ""

    issue_num = None
    if declared:
        issue_num = lookup_canonical_issue_key(fm_id, issue_dict)
        if issue_num is None:
            declared_ref = format_issue_reference(declared, tracker_rules)
            print(
                f"[FATAL] {item_type} '{basename}' declares issue_id {declared_ref}, "
                "which does not exist on the tracker. Refusing to fall back to title "
                "matching: that is how an unrelated issue's body gets overwritten "
                f"(#316). Correct or remove the issue_id in {filepath}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        issue_num = title_map.get(normalize_title(title, rules))
        if issue_num is not None:
            print(
                f"  [Warning] {item_type} '{basename}' has no issue_id in its "
                f"frontmatter; fell back to matching by normalized title and resolved "
                f"{format_issue_reference(issue_num, tracker_rules)}. "
                ".pipeline/constitution.md:58-59 prohibits title normalization as a "
                f"primary selector — add 'issue_id: {issue_num}' to {filepath}"
            )

    if issue_num is None:
        return None

    if claimed is not None:
        key = str(issue_num)
        previous = claimed.get(key)
        if previous is not None and os.path.abspath(previous) != os.path.abspath(filepath):
            print(
                "[FATAL] Two specification files resolve to the same issue "
                f"{format_issue_reference(issue_num, tracker_rules)}: "
                f"{previous} and {filepath}. Syncing both would overwrite one body with "
                "the other (#316). Give each file its own issue_id.",
                file=sys.stderr,
            )
            sys.exit(1)
        claimed[key] = filepath

    return issue_num


def build_epic_alias_map(epics_dir, rules=None):
    """Every spelling an Epic can be referenced by -> that Epic's canonical normalized title.

    The map resolves *cross-references between items* — the `epic:` frontmatter key and
    the parent-epic link in a body — so that a child ends up in the right Epic's
    checklist. It has never resolved a file's own identity, and after #314/#316 it must
    not: `resolve_spec_issue_number` is the sole authority there, and an alias that
    claimed a Feature's slug would assert an identity the resolver never granted.

    Aliases are deliberately generous, including type-erased ones: an Epic titled
    "Epic 07: Geo Location" is reachable as `geo location`, because children routinely
    name their parent by bare title. #319 is what that generosity cost — `feat-07-geo-
    location` normalizes to `geo location` too, so a Feature-typed reference resolved to
    the Epic. The gate for that is at *lookup* time in `resolve_epic_reference`, on the
    type the reference declares about itself, rather than by deleting the alias: deleting
    it would break every legitimate reference-by-title, which is the common case.

    What is enforced here is the other half of the collision. An alias claimed by two
    Epics with different canonical titles is dropped rather than kept, because keeping it
    resolves by `os.listdir` order — a filesystem accident, not a resolution rule.
    """
    alias_map = {}
    ambiguous = set()
    if not epics_dir or not os.path.exists(epics_dir):
        return alias_map

    for fn in sorted(os.listdir(epics_dir)):
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(epics_dir, fn)
        title = extract_title(fp)
        meta = extract_metadata(fp)
        canonical_norm = normalize_title(title, rules) if title else ""
        if not canonical_norm:
            canonical_norm = fn[:-3].lower()

        aliases = set()
        if title:
            aliases.add(title.strip().strip('"\'').lower())
            aliases.add(normalize_title(title, rules))
            aliases.add(re.sub(r'^\w+[- ]*\d+\s*[:\-]?\s*', '', title, flags=re.IGNORECASE).strip().lower())

        fn_slug = fn[:-3]
        aliases.add(fn_slug.lower())
        aliases.add(fn_slug.lower().replace("-", " "))
        aliases.add(normalize_title(fn_slug, rules))

        fm_id = meta.get("id") or meta.get("epic")
        if fm_id:
            fm_id_str = str(fm_id).strip().strip('"\'')
            aliases.add(fm_id_str.lower())
            aliases.add(fm_id_str.lower().replace("-", " "))
            aliases.add(normalize_title(fm_id_str, rules))

        for sample in [title, fn_slug, str(fm_id) if fm_id else ""]:
            if sample:
                m = re.search(r'\b(epic[- ]*\d+)\b', sample, re.IGNORECASE)
                if m:
                    id_prefix = m.group(1).lower()
                    aliases.add(id_prefix)
                    aliases.add(id_prefix.replace("-", " "))
                    aliases.add(id_prefix.replace(" ", "-"))

        for alias in sorted(a for a in aliases if a):
            if alias in ambiguous:
                continue
            existing = alias_map.get(alias)
            if existing is not None and existing != canonical_norm:
                print(
                    f"  [Warning] Epic alias '{alias}' is claimed by both "
                    f"'{existing}' and '{canonical_norm}'; dropping it rather than "
                    "resolving by directory order (#319). Reference the intended Epic "
                    "by its filename slug or issue number."
                )
                del alias_map[alias]
                ambiguous.add(alias)
                continue
            alias_map[alias] = canonical_norm

    return alias_map


def resolve_epic_reference(epic_ref, epic_alias_map, epic_id_to_norm, rules=None):
    """Resolve a parent-epic reference to the referenced Epic's normalized title.

    Order: issue number first, then the alias map, then bare normalization.

    The namespace gate for #319 sits between those last two. A reference that names its
    own type — `feat-07-geo-location`, `us-03-operator`, `uc-04-device-state` — is not an
    Epic reference, so the alias map is not consulted for it and no epic is returned.
    Falling through to `normalize_title` instead would not be enough: the whole point of
    the collision is that a Feature and an Epic sharing a suffix normalize to the same
    string, so the bare normalization matches the Epic's canonical title just as the
    alias did.

    Returning None is reported rather than silent. A parent link that quietly fails to
    resolve is indistinguishable from a specification that declares no parent at all,
    and the reference itself is the thing that needs correcting.
    """
    if not epic_ref:
        return None

    if isinstance(epic_ref, int):
        if epic_ref in epic_id_to_norm:
            return epic_id_to_norm[epic_ref]
        ref_str = str(epic_ref)
    else:
        ref_str = str(epic_ref).strip().strip('"\'')

    clean_ref = ref_str
    if clean_ref.startswith('#'):
        clean_ref = clean_ref[1:].strip()

    if clean_ref in epic_id_to_norm:
        return epic_id_to_norm[clean_ref]
    if clean_ref.isdigit() and int(clean_ref) in epic_id_to_norm:
        return epic_id_to_norm[int(clean_ref)]

    declared_type = spec_type_of_reference(ref_str)
    if declared_type is not None and declared_type != "epic":
        print(
            f"  [Warning] Parent-epic reference '{ref_str}' names a {declared_type}, "
            "not an Epic; refusing to resolve it through the Epic alias map (#319). A "
            "type-erased alias would otherwise attach this item to an unrelated Epic "
            "sharing the same title suffix."
        )
        return None

    if ref_str.lower() in epic_alias_map:
        return epic_alias_map[ref_str.lower()]
    norm = normalize_title(ref_str, rules)
    if norm in epic_alias_map:
        return epic_alias_map[norm]
    ref_space = ref_str.lower().replace("-", " ")
    if ref_space in epic_alias_map:
        return epic_alias_map[ref_space]
    return norm


def resolve_type_context(line, filepath, section_context):
    # 1. URL path check
    link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
    if link_match:
        path = link_match.group(2)
        if "docs/features" in path or "/features/" in path:
            return "feature"
        elif "docs/user-stories" in path or "/user-stories/" in path:
            return "user-story"
        elif "docs/use-cases" in path or "/use-cases/" in path:
            return "use-case"
        elif "docs/epics" in path or "/epics/" in path:
            return "epic"
            
    # 2. Section context check
    if section_context:
        return section_context
        
    # 3. Line prefix/keywords check
    line_lower = line.lower()
    if "use case" in line_lower or "use-case" in line_lower or "uc-" in line_lower:
        return "use-case"
    if "user story" in line_lower or "user-story" in line_lower or "us-" in line_lower:
        return "user-story"
    if "feature" in line_lower or "feat-" in line_lower:
        return "feature"
    if "epic" in line_lower:
        return "epic"
        
    # 4. File folder context check (default fallback)
    parent_dir = os.path.basename(os.path.dirname(filepath))
    if "features" in parent_dir:
        return "feature"
    elif "user-stories" in parent_dir:
        return "user-story"
    elif "use-cases" in parent_dir:
        return "use-case"
    elif "epics" in parent_dir:
        return "epic"
        
    return None

def resolve_issue_ids_in_file(filepath, epic_titles, feature_titles, story_titles, usecase_titles, rules=None):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    tracker_rules = rules.get("tracker_rules", {}) if rules else {}
    placeholder = tracker_rules.get("issue_id_placeholder", "#[IssueID]")
    title_extraction_prefixes_regex = tracker_rules.get("title_extraction_prefixes_regex", r"(?:Feature\s+\d+\s*:\s*|Use\s+Case\s+\d+\s*:\s*|User\s+Story\s+\d+\s*:\s*)?")
    
    if placeholder not in content and "#[EpicIssueID]" not in content:
        return content
        
    lines = content.splitlines()
    updated = False
    
    section_context = None
    for i, line in enumerate(lines):
        # Track section context based on headers
        header_match = re.match(r'^(#+)\s+(.*)$', line)
        if header_match:
            header_text = header_match.group(2).lower()
            if "use case" in header_text:
                section_context = "use-case"
            elif "user story" in header_text or "user-story" in header_text:
                section_context = "user-story"
            elif "feature" in header_text or "requirement" in header_text:
                section_context = "feature"
            elif "epic" in header_text:
                section_context = "epic"
                
        if placeholder not in line and "#[EpicIssueID]" not in line:
            continue
            
        active_placeholder = placeholder if placeholder in line else "#[EpicIssueID]"
        escaped_active = re.escape(active_placeholder)
        
        title = None
        link_label_match = re.search(r'\[([^\]]+)\]\(', line)
        if link_label_match:
            title = link_label_match.group(1).strip()
        else:
            pattern = escaped_active + r'(?:\s*[-:]\s*)?' + title_extraction_prefixes_regex + r'(.*)$'
            dash_match = re.search(pattern, line)
            if dash_match:
                title = dash_match.group(1).strip()
                title = re.sub(r'\(.*?\)', '', title).strip()
                title = title.strip('[]-* ')
                
        if (not title or not title.strip()) and re.search(r'issue[\s\-_]*id\s*:', line, re.IGNORECASE):
            title = extract_title(filepath)

        if title:
            norm = normalize_title(title, rules)
            type_context = resolve_type_context(line, filepath, section_context)
            if active_placeholder == "#[EpicIssueID]":
                type_context = "epic"
            issue_num = None
            if type_context == "epic":
                issue_num = epic_titles.get(norm)
            elif type_context == "feature":
                issue_num = feature_titles.get(norm)
            elif type_context == "user-story":
                issue_num = story_titles.get(norm)
            elif type_context == "use-case":
                issue_num = usecase_titles.get(norm)
                
            if not issue_num:
                issue_num = (feature_titles.get(norm) or 
                             story_titles.get(norm) or 
                             usecase_titles.get(norm) or 
                             epic_titles.get(norm))
                             
            if issue_num:
                ref_str = format_issue_reference(issue_num, tracker_rules)
                lines[i] = line.replace(active_placeholder, ref_str)
                updated = True
                print(f"  [Resolve ID] Resolved {active_placeholder} to {ref_str} for '{title}' (type: {type_context}) in {os.path.basename(filepath)}")
            else:
                print(f"  [Warning] Could not resolve {active_placeholder} for title '{title}' in {os.path.basename(filepath)}")
                
    if updated:
        new_content = "\n".join(lines) + "\n"
        return write_markdown_file(filepath, new_content)
        
    return content

def reconcile_epic_checklists(filepath, child_features, child_stories, child_usecases, epic_titles, feature_titles, story_titles, usecase_titles, rules):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    
    idx_req = -1
    idx_usecases = -1
    idx_stories = -1
    idx_next = -1
    
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean.startswith("## 2. Requirements & Checklist") or (line_clean.startswith("## 2.") and "Checklist" in line_clean):
            idx_req = idx
        elif re.match(r'^#{3,4}\s+Associated\s+Use\s+Cases(?!\s*(?:&|and)\s*User\s+Stories)', line_clean, re.IGNORECASE):
            idx_usecases = idx
        elif re.match(r'^#{3,4}\s+Associated\s+User\s+Stories', line_clean, re.IGNORECASE):
            idx_stories = idx
        elif idx_req != -1 and line_clean.startswith("## ") and idx > idx_req and not line_clean.startswith("## 2."):
            if idx_next == -1:
                idx_next = idx

    if idx_usecases == -1:
        for idx, line in enumerate(lines):
            if re.match(r'^#{3,4}\s+Associated\s+Use\s+Cases', line.strip(), re.IGNORECASE):
                idx_usecases = idx
                break

    def extract_items_from_range(start_idx, end_idx):
        items = []
        if start_idx == -1:
            return items
        limit = end_idx if end_idx != -1 else len(lines)
        for i in range(start_idx + 1, limit):
            l = lines[i].strip()
            if l.startswith("## "):
                break
            if l.startswith("### ") or l.startswith("#### "):
                continue
            if l.startswith("- [ ]") or l.startswith("- [x]") or l.startswith("- [X]"):
                l_lower = l.lower()
                ignore_exact = {
                    "feat-xx-name",
                    "uc-xx-name",
                    "us-xx-name",
                    "feature title",
                    "use case title",
                    "user story title",
                    "epic title",
                }
                prefix_patterns = {"feature 1:", "use case 1:", "user story 1:"}
                title_part = re.sub(r'^-\s*\[[ xX]\]\s*', '', l_lower)
                if any(p == title_part for p in ignore_exact):
                    continue
                if any(title_part.startswith(p) for p in prefix_patterns):
                    continue
                items.append(lines[i])
        return items

    PLACEHOLDER_PATTERNS = [
        re.compile(r'^\s*[-*]*\s*\(?\s*\*?To be populated.*?\*?\)?\s*$', re.IGNORECASE),
        re.compile(r'^\s*[-*]*\s*\*?TBD\*?\s*$', re.IGNORECASE),
        re.compile(r'^\s*[-*]*\s*\*?N/A\*?\s*$', re.IGNORECASE),
    ]

    def filter_content_lines(slice_lines):
        filtered = []
        for l in slice_lines:
            stripped = l.strip()
            if stripped and not any(p.match(stripped) for p in PLACEHOLDER_PATTERNS):
                filtered.append(l)
            elif not stripped:
                filtered.append(l)
        return filtered

    end_req = idx_usecases if idx_usecases != -1 else (idx_stories if idx_stories != -1 else idx_next)
    end_usecases = idx_stories if idx_stories != -1 else idx_next
    end_stories = idx_next
    
    existing_features = extract_items_from_range(idx_req, end_req)
    existing_usecases = extract_items_from_range(idx_usecases, end_usecases)
    existing_stories = extract_items_from_range(idx_stories, end_stories)
    
    indent = ""
    for item in existing_features + existing_usecases + existing_stories:
        m = re.match(r'^(\s*)', item)
        if m and m.group(1):
            indent = m.group(1)
            break

    workspace_root = find_workspace_dir(filepath)
    upstream_repo = get_upstream_repository(rules, workspace_root)
    repo_base = upstream_repo
    if not repo_base.startswith("http"):
        repo_base = f"https://github.com/{repo_base}"
    branch_name = get_current_branch(workspace_root)
    
    def format_item(item_type, filename, title, issue_num):
        tracker_rules = rules.get("tracker_rules", {}) if rules else {}
        ref_str = format_issue_reference(issue_num, tracker_rules) if (issue_num and issue_num != 0) else tracker_rules.get("issue_id_placeholder", "#[IssueID]")
        
        if item_type == "feature":
            path_part = f"docs/features/{filename}.md"
        elif item_type == "use-case":
            path_part = f"docs/use-cases/{filename}.md"
        else:
            path_part = f"docs/user-stories/{filename}.md"
            
        return f"{indent}- [ ] {ref_str} - [{title}]({repo_base}/blob/{branch_name}/{path_part}) (semantic linkage justification)"

    def get_filename_key(item_str):
        m = re.search(r'(?:docs/)?(features|use-cases|user-stories)/([a-zA-Z0-9_\-]+)\.md', item_str)
        if m:
            return m.group(2)
        return None

    def sanitize_existing_item(item, title_map, child_list):
        tracker_rules = rules.get("tracker_rules", {}) if rules else {}
        placeholder = tracker_rules.get("issue_id_placeholder", "#[IssueID]")
        if "#0" in item or "#[" in item:
            title = None
            m_title = re.search(r'\[([^\]]+)\]\(', item)
            if m_title:
                title = m_title.group(1)
            else:
                key = get_filename_key(item)
                if key and child_list:
                    for fn, t in child_list:
                        if fn == key:
                            title = t
                            break
            issue_num = None
            if title:
                issue_num = title_map.get(normalize_title(title, rules))
            if issue_num and issue_num != 0:
                ref_str = format_issue_reference(issue_num, tracker_rules)
                item = re.sub(r'#0\b|#\[(?:IssueID|FeatureIssueID|UseCaseIssueID|StoryIssueID)\]', ref_str, item)
            else:
                item = re.sub(r'#0\b', placeholder, item)
        return item

    final_features = []
    seen_feats = set()
    for item in existing_features:
        key = get_filename_key(item)
        sanitized = sanitize_existing_item(item, feature_titles, child_features)
        if key:
            seen_feats.add(key)
        final_features.append(sanitized)
            
    for fn, title in child_features:
        if fn not in seen_feats:
            issue_num = feature_titles.get(normalize_title(title, rules))
            final_features.append(format_item("feature", fn, title, issue_num))
            seen_feats.add(fn)
            
    final_usecases = []
    seen_ucs = set()
    for item in existing_usecases:
        key = get_filename_key(item)
        sanitized = sanitize_existing_item(item, usecase_titles, child_usecases)
        if key:
            seen_ucs.add(key)
        final_usecases.append(sanitized)
            
    for fn, title in child_usecases:
        if fn not in seen_ucs:
            issue_num = usecase_titles.get(normalize_title(title, rules))
            final_usecases.append(format_item("use-case", fn, title, issue_num))
            seen_ucs.add(fn)
            
    final_stories = []
    seen_stories = set()
    for item in existing_stories:
        key = get_filename_key(item)
        sanitized = sanitize_existing_item(item, story_titles, child_stories)
        if key:
            seen_stories.add(key)
        final_stories.append(sanitized)
            
    for fn, title in child_stories:
        if fn not in seen_stories:
            issue_num = story_titles.get(normalize_title(title, rules))
            final_stories.append(format_item("user-story", fn, title, issue_num))
            seen_stories.add(fn)

    def is_item_or_placeholder(line):
        l = line.strip()
        if not l:
            return False
        if l.startswith("- [ ]") or l.startswith("- [x]") or l.startswith("- [X]"):
            return True
        if any(p.match(l) for p in PLACEHOLDER_PATTERNS):
            return True
        return False

    def filter_non_item_lines(slice_lines):
        filtered = []
        prev_blank = False
        for l in slice_lines:
            if is_item_or_placeholder(l):
                continue
            stripped = l.strip()
            if not stripped:
                if not prev_blank:
                    filtered.append(l)
                    prev_blank = True
            else:
                filtered.append(l)
                prev_blank = False
        return filtered

    new_lines = []
    if idx_req != -1:
        new_lines.extend(lines[:idx_req + 1])
        if not final_features:
            new_lines.append(f"{indent}*To be populated after Phase 3*")
        else:
            new_lines.extend(final_features)
        
        if idx_usecases != -1:
            end_req = idx_usecases
            new_lines.extend(filter_non_item_lines(lines[idx_req + 1 : end_req]))
            new_lines.append(lines[idx_usecases])
        else:
            end_req = idx_stories if idx_stories != -1 else (idx_next if idx_next != -1 else len(lines))
            new_lines.extend(filter_non_item_lines(lines[idx_req + 1 : end_req]))
            new_lines.append("")
            new_lines.append(f"{indent}### Associated Use Cases & User Stories")
            new_lines.append("")
            new_lines.append(f"{indent}#### Associated Use Cases")
            
        if not final_usecases:
            new_lines.append(f"{indent}*To be populated after Phase 3*")
        else:
            new_lines.extend(final_usecases)
        
        if idx_stories != -1:
            end_usecases = idx_stories
            start_usecases = idx_usecases if idx_usecases != -1 else idx_req
            new_lines.extend(filter_non_item_lines(lines[start_usecases + 1 : end_usecases]))
            new_lines.append(lines[idx_stories])
        else:
            end_usecases = idx_next if idx_next != -1 else len(lines)
            start_usecases = idx_usecases if idx_usecases != -1 else idx_req
            new_lines.extend(filter_non_item_lines(lines[start_usecases + 1 : end_usecases]))
            new_lines.append("")
            new_lines.append(f"{indent}#### Associated User Stories")
            
        if not final_stories:
            new_lines.append(f"{indent}*To be populated after Phase 3*")
        else:
            new_lines.extend(final_stories)
        
        start_after_stories = idx_stories if idx_stories != -1 else (idx_usecases if idx_usecases != -1 else idx_req)
        if idx_next != -1:
            new_lines.extend(filter_non_item_lines(lines[start_after_stories + 1 : idx_next]))
            new_lines.extend(lines[idx_next:])
        else:
            new_lines.extend(filter_non_item_lines(lines[start_after_stories + 1 :]))
    else:
        return

    new_content = "\n".join(new_lines) + "\n"
    if new_content != content:
        write_markdown_file(filepath, new_content)
        print(f"  [Reconcile Checklist] Updated checklists in {os.path.basename(filepath)}")

def find_workspace_dir(start_path):
    curr = os.path.abspath(start_path)
    if os.path.isfile(curr):
        curr = os.path.dirname(curr)
    while True:
        if os.path.exists(os.path.join(curr, ".pipeline", "logical-ui", "codebase_rules.json")):
            return curr
        if os.path.exists(os.path.join(curr, ".git")):
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.dirname(os.path.abspath(start_path)) if os.path.isfile(start_path) else os.path.abspath(start_path)

def assert_no_mock_cli(workspace_dir=None):
    if not workspace_dir:
        workspace_dir = find_workspace_dir(os.getcwd())
    workspace_dir = os.path.abspath(workspace_dir)
    scratch_dir = os.path.abspath(os.path.join(workspace_dir, "scratch"))
    scratch_bin = os.path.join(scratch_dir, "bin")
    forbidden_cmds = ["gh", "git", "flutter"]

    for cmd in forbidden_cmds:
        binary_path = os.path.join(scratch_bin, cmd)
        if os.path.exists(binary_path):
            print(f"[FATAL] Zero-mocking policy violation: Forbidden mock CLI binary detected at {binary_path}", file=sys.stderr)
            sys.exit(1)

        resolved = shutil.which(cmd)
        if resolved:
            resolved_abs = os.path.abspath(resolved)
            if resolved_abs.startswith(scratch_dir + os.sep) or resolved_abs == scratch_dir:
                print(f"[FATAL] Zero-mocking policy violation: Forbidden mock CLI binary detected at {resolved_abs}", file=sys.stderr)
                sys.exit(1)

def main():
    sanitize_github_token_env()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = find_workspace_dir(script_dir)
    assert_no_mock_cli(workspace_dir)

    # Programmatic gate: Run linter before proceeding with reconciliation
    blocked_specs = set()
    try:
        with open(os.path.join(workspace_dir, ".pipeline", "logical-ui",
                               "codebase_rules.json"), encoding="utf-8") as _fh:
            rules_preview = json.load(_fh)
    except Exception:
        rules_preview = {}
    print("Running pre-reconciliation linter validation...")
    linter_script = os.path.join(workspace_dir, "skills", "spec-orchestrator", "scripts", "verify_model_coverage.py")
    cmd = [sys.executable, linter_script, "--spec-only", "--allow-missing-specs"]
    try:
        res = subprocess.run(cmd, cwd=workspace_dir, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            output_text = (res.stdout or "") + "\n" + (res.stderr or "")
            lines = [line.strip() for line in output_text.splitlines()]
            error_lines = [line for line in lines if line.startswith("- ")]
            
            is_exclusive_checklist_placeholder = False
            if error_lines:
                is_exclusive_checklist_placeholder = True
                for err in error_lines:
                    err_lower = err.lower()
                    if "placeholder" not in err_lower and "checklist" not in err_lower and "required features matrix" not in err_lower:
                        is_exclusive_checklist_placeholder = False
                        break
            
            if is_exclusive_checklist_placeholder:
                print("[Warning] Pre-reconciliation linter validation found only checklist warning issues/placeholders. Proceeding with warnings.", file=sys.stderr)
                for err in error_lines:
                    print(f"  [Warning Detail] {err}", file=sys.stderr)
            else:
                # Issue #321 - a failing linter used to abort the entire run, so one
                # incomplete work-in-progress draft withheld synchronisation from every
                # finished, unrelated specification. The gate is not weakened: the
                # offending items are skipped and the run still exits non-zero at the
                # end. What changes is that valid work is no longer held hostage.
                blocked_specs = blocked_specs_from_linter_output(
                    output_text, workspace_dir, rules_preview
                )
                print("[BLOCKED] Pre-reconciliation linter validation failed for "
                      f"{len(blocked_specs)} specification(s). These will be SKIPPED; "
                      "everything else still synchronises, and this run will exit "
                      "non-zero.", file=sys.stderr)
                for name in sorted(blocked_specs):
                    print(f"  [Blocked] {name}", file=sys.stderr)
                print(res.stdout, file=sys.stderr)
        else:
            print("Pre-reconciliation linter validation passed successfully.")
    except subprocess.TimeoutExpired:
        print("[FATAL] Pre-reconciliation linter validation timed out after 30 seconds. Aborting.", file=sys.stderr)
        sys.exit(1)

    try:
        rules_path = os.path.join(workspace_dir, ".pipeline", "logical-ui", "codebase_rules.json")
        if not os.path.exists(rules_path):
            print(f"Error: codebase_rules.json not found at: {rules_path}")
            print("Please ensure the configuration file is present at '.pipeline/logical-ui/codebase_rules.json'.")
            sys.exit(1)

        rules = load_codebase_rules(workspace_dir)
        if not rules:
            print("Error: codebase_rules.json is empty, invalid, or could not be loaded.")
            print("Please check '.pipeline/logical-ui/codebase_rules.json' and ensure it contains valid configuration.")
            sys.exit(1)

        try:
            issues = get_all_issues(rules)
        except Exception as e:
            print(f"Error fetching issues: {e}")
            print("Please ensure issue tracker CLI is authenticated and configured.")
            sys.exit(1)

        tracker_rules = rules.get("tracker_rules", {}) if rules else {}
        keys = tracker_rules.get("keys", {})
        id_key = keys.get("issue_id", "number")
        title_key = keys.get("title", "title")
        labels_key = keys.get("labels", "labels")
        state_key = keys.get("state", "state")
        
        close_comments = tracker_rules.get("close_comments", {})
        epic_comment = close_comments.get("epic", "Epic completed. All constituent features successfully delivered and verified.")
        story_comment_template = close_comments.get("user_story", "Resolved. All dependent features/tasks for BDD scenario '{title}' have been completed and verified.")
        usecase_comment_template = close_comments.get("use_case", "Resolved. All dependent user stories and features for use case '{title}' are completed.")

        issue_dict = {}
        for issue in issues:
            raw_id = issue[id_key]
            issue_dict[raw_id] = issue
            if isinstance(raw_id, str) and raw_id.isdigit():
                issue_dict[int(raw_id)] = issue
            elif isinstance(raw_id, int):
                issue_dict[str(raw_id)] = issue

        epic_titles = {}
        story_titles = {}
        usecase_titles = {}
        feature_titles = {}

        # Both sides of every comparison fold through normalize_label (#329): an issue
        # filed as "User Story" lowercases to "user story", never matched "user-story",
        # and was bucketed nowhere — its specification then reported no issue on the
        # tracker and the duplicate stayed open and orphaned.
        labels_config = tracker_rules.get("labels", {})
        epic_label = normalize_label(labels_config.get("epic", "epic"))
        story_label = normalize_label(labels_config.get("user_story", "user-story"))
        usecase_label = normalize_label(labels_config.get("use_case", "use-case"))
        feature_label = normalize_label(labels_config.get("feature", "feature"))

        for num, issue in issue_dict.items():
            if isinstance(num, str) and num.isdigit() and int(num) in epic_titles:
                continue
            norm_title = normalize_title(issue[title_key], rules)
            labels = []
            for l in issue.get(labels_key, []):
                if isinstance(l, dict):
                    labels.append(normalize_label(l.get("name", "")))
                elif isinstance(l, str):
                    labels.append(normalize_label(l))

            if epic_label in labels:
                epic_titles[norm_title] = num
            elif story_label in labels:
                story_titles[norm_title] = num
            elif usecase_label in labels:
                usecase_titles[norm_title] = num
            elif feature_label in labels:
                feature_titles[norm_title] = num
            
        backlog_dirs = rules.get("backlog_directories")
        if not backlog_dirs:
            raise ValueError("Missing 'backlog_directories' in codebase_rules.json")
            
        epics_rel = backlog_dirs.get("epics")
        features_rel = backlog_dirs.get("features")
        stories_rel = backlog_dirs.get("user_stories")
        usecases_rel = backlog_dirs.get("use_cases")
        
        if not all([epics_rel, features_rel, stories_rel, usecases_rel]):
            raise ValueError("Missing epic, features, user_stories, or use_cases path in backlog_directories configuration")
            
        upstream_repo = get_upstream_repository(rules, workspace_dir)
        if not upstream_repo:
            raise ValueError("Missing 'meta.upstream_repository' in codebase_rules.json and remote origin is not configured")

        if len(sys.argv) > 1:
            docs_dir = os.path.abspath(sys.argv[1])
            epics_dir = os.path.join(docs_dir, os.path.basename(epics_rel))
            features_dir = os.path.join(docs_dir, os.path.basename(features_rel))
            stories_dir = os.path.join(docs_dir, os.path.basename(stories_rel))
            usecases_dir = os.path.join(docs_dir, os.path.basename(usecases_rel))
            print(f"Scanning backlog files in {docs_dir}...")
        else:
            epics_dir = os.path.join(workspace_dir, epics_rel)
            features_dir = os.path.join(workspace_dir, features_rel)
            stories_dir = os.path.join(workspace_dir, stories_rel)
            usecases_dir = os.path.join(workspace_dir, usecases_rel)
            print("Scanning backlog files...")

        # Build Epic Alias Map for robust child-to-epic title/ID resolution. Extracted to
        # module scope by #319 so the collision it used to contain is testable.
        epic_alias_map = build_epic_alias_map(epics_dir, rules)

        # Build reverse lookup map for Epic issue IDs to normalized titles
        epic_id_to_norm = {}
        for norm_title, issue_id in epic_titles.items():
            epic_id_to_norm[str(issue_id)] = norm_title
            if isinstance(issue_id, int):
                epic_id_to_norm[issue_id] = norm_title
            elif isinstance(issue_id, str) and issue_id.isdigit():
                epic_id_to_norm[int(issue_id)] = norm_title

        def resolve_epic_norm(epic_ref):
            return resolve_epic_reference(epic_ref, epic_alias_map, epic_id_to_norm, rules)

        # Dynamic relationship scanning
        feature_to_epic = {}
        if os.path.exists(features_dir):
            for fn in os.listdir(features_dir):
                if fn.endswith(".md"):
                    fp = os.path.join(features_dir, fn)
                    meta = extract_metadata(fp)
                    epic_name = meta.get("epic") or meta.get("parent_epic")
                    if not epic_name:
                        try:
                            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                                body_content = f.read()
                            epic_name = extract_epic_from_body(body_content)
                        except Exception as e:
                            print(f"Warning: Failed to extract epic from body of feature {fn}: {e}")
                    if epic_name:
                        resolved_epic = resolve_epic_norm(epic_name)
                        if resolved_epic:
                            feature_to_epic[fn[:-3]] = {resolved_epic}

        story_to_epic = {}
        if os.path.exists(stories_dir):
            for fn in os.listdir(stories_dir):
                if fn.endswith(".md"):
                    fp = os.path.join(stories_dir, fn)
                    meta = extract_metadata(fp)
                    epic_name = meta.get("epic") or meta.get("parent_epic")
                    if not epic_name:
                        try:
                            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                                body_content = f.read()
                            epic_name = extract_epic_from_body(body_content)
                        except Exception as e:
                            print(f"Warning: Failed to extract epic from body of story {fn}: {e}")
                    epics = set()
                    if epic_name:
                        resolved_epic = resolve_epic_norm(epic_name)
                        if resolved_epic:
                            epics.add(resolved_epic)
                    
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    feature_refs = re.findall(r'(?:docs/features/|/features/)([a-zA-Z0-9_\-]+)\.md', content)
                    realizes = meta.get("realizes", [])
                    if isinstance(realizes, list):
                        for r in realizes:
                            if isinstance(r, str):
                                # r might be a path like docs/features/foo.md or just foo
                                r_clean = os.path.basename(r)
                                if r_clean.endswith(".md"):
                                    r_clean = r_clean[:-3]
                                feature_refs.append(r_clean)
                                
                    for feat in feature_refs:
                        if feat in feature_to_epic:
                            epics.update(feature_to_epic[feat])
                    
                    story_to_epic[fn[:-3]] = epics

        usecase_to_epic = {}
        if os.path.exists(usecases_dir):
            for fn in os.listdir(usecases_dir):
                if fn.endswith(".md"):
                    fp = os.path.join(usecases_dir, fn)
                    meta = extract_metadata(fp)
                    epic_name = meta.get("epic") or meta.get("parent_epic")
                    if not epic_name:
                        try:
                            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                                body_content = f.read()
                            epic_name = extract_epic_from_body(body_content)
                        except Exception as e:
                            print(f"Warning: Failed to extract epic from body of use case {fn}: {e}")
                    epics = set()
                    if epic_name:
                        resolved_epic = resolve_epic_norm(epic_name)
                        if resolved_epic:
                            epics.add(resolved_epic)
                        
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    feature_refs = re.findall(r'(?:docs/features/|/features/)([a-zA-Z0-9_\-]+)\.md', content)
                    realizes = meta.get("realizes", [])
                    if isinstance(realizes, list):
                        for r in realizes:
                            if isinstance(r, str):
                                r_clean = os.path.basename(r)
                                if r_clean.endswith(".md"):
                                    r_clean = r_clean[:-3]
                                feature_refs.append(r_clean)
                                
                    for feat in feature_refs:
                        if feat in feature_to_epic:
                            epics.update(feature_to_epic[feat])
                    story_refs = re.findall(r'(?:docs/user-stories/|/user-stories/)([a-zA-Z0-9_\-]+)\.md', content)
                    for story in story_refs:
                        if story in story_to_epic:
                            epics.update(story_to_epic[story])
                            
                    usecase_to_epic[fn[:-3]] = epics

        # Reconcile Epic checklists
        if os.path.exists(epics_dir):
            for filename in sorted(os.listdir(epics_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(epics_dir, filename)
                if filename in blocked_specs:
                    print(f'  [Skipped] {filename} - blocked by linter findings (#321)')
                    continue
                title = extract_title(filepath)
                if not title:
                    continue
                epic_norm = normalize_title(title, rules)
                
                child_features = []
                if os.path.exists(features_dir):
                    for feat_fn in sorted(os.listdir(features_dir)):
                        if feat_fn.endswith(".md"):
                            feat_fp = os.path.join(features_dir, feat_fn)
                            if epic_norm in feature_to_epic.get(feat_fn[:-3], set()):
                                feat_title = extract_title(feat_fp)
                                if feat_title:
                                    child_features.append((feat_fn[:-3], feat_title))

                child_stories = []
                if os.path.exists(stories_dir):
                    for story_fn in sorted(os.listdir(stories_dir)):
                        if story_fn.endswith(".md"):
                            story_fp = os.path.join(stories_dir, story_fn)
                            if epic_norm in story_to_epic.get(story_fn[:-3], set()):
                                story_title = extract_title(story_fp)
                                if story_title:
                                    child_stories.append((story_fn[:-3], story_title))

                child_usecases = []
                if os.path.exists(usecases_dir):
                    for uc_fn in sorted(os.listdir(usecases_dir)):
                        if uc_fn.endswith(".md"):
                            uc_fp = os.path.join(usecases_dir, uc_fn)
                            if epic_norm in usecase_to_epic.get(uc_fn[:-3], set()):
                                uc_title = extract_title(uc_fp)
                                if uc_title:
                                    child_usecases.append((uc_fn[:-3], uc_title))

                reconcile_epic_checklists(
                    filepath, 
                    child_features, 
                    child_stories, 
                    child_usecases, 
                    epic_titles, 
                    feature_titles, 
                    story_titles, 
                    usecase_titles, 
                    rules
                )

        # One issue belongs to exactly one spec file. Shared across all four loops so a
        # collision is caught whatever type the colliding files are (#316).
        claimed_issues = {}

        # Process Epics
        if os.path.exists(epics_dir):
            for filename in sorted(os.listdir(epics_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(epics_dir, filename)
                if filename in blocked_specs:
                    print(f'  [Skipped] {filename} - blocked by linter findings (#321)')
                    continue
                resolve_issue_ids_in_file(filepath, epic_titles, feature_titles, story_titles, usecase_titles, rules=rules)
                title = extract_title(filepath)
                if not title:
                    continue
                
                issue_num = resolve_spec_issue_number(
                    filepath, title, epic_titles, issue_dict, rules=rules,
                    item_type="Epic", claimed=claimed_issues,
                )
                if issue_num is not None:
                    updated_content, completed = update_checklist_in_file(filepath, issue_dict, rules)
                    is_open = str(issue_dict[issue_num][state_key]).upper() == keys.get("open_state_value", "OPEN").upper()
                    if is_open:
                        sync_issue_body_to_tracker(
                            issue_num, filepath, issue_type="Epic", rules=rules,
                            issue_record=issue_dict[issue_num],
                        )
                        if completed and not is_already_resolved(issue_dict[issue_num], rules):
                            resolve_issue_on_tracker(
                                issue_num, 
                                epic_comment,
                                rules=rules
                            )
                            issue_dict[issue_num].setdefault("labels", []).append(
                                {"name": get_resolved_label(rules)}
                            )
                else:
                    print(
                        f"Warning: No Epic issue on the tracker for {filename} — "
                        f"no issue_id in its frontmatter and no title match for '{title}'"
                    )

        # Process Features
        if os.path.exists(features_dir):
            for filename in sorted(os.listdir(features_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(features_dir, filename)
                if filename in blocked_specs:
                    print(f'  [Skipped] {filename} - blocked by linter findings (#321)')
                    continue
                resolve_issue_ids_in_file(filepath, epic_titles, feature_titles, story_titles, usecase_titles, rules=rules)
                title = extract_title(filepath)
                if not title:
                    continue
                
                issue_num = resolve_spec_issue_number(
                    filepath, title, feature_titles, issue_dict, rules=rules,
                    item_type="Feature", claimed=claimed_issues,
                )
                if issue_num is not None:
                    is_open = str(issue_dict[issue_num][state_key]).upper() == keys.get("open_state_value", "OPEN").upper()
                    if is_open:
                        sync_issue_body_to_tracker(
                            issue_num, filepath, issue_type="Feature", rules=rules,
                            issue_record=issue_dict[issue_num],
                        )
                else:
                    print(
                        f"Warning: No Feature issue on the tracker for {filename} — "
                        f"no issue_id in its frontmatter and no title match for '{title}'"
                    )

        # Process User Stories
        if os.path.exists(stories_dir):
            for filename in sorted(os.listdir(stories_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(stories_dir, filename)
                if filename in blocked_specs:
                    print(f'  [Skipped] {filename} - blocked by linter findings (#321)')
                    continue
                resolve_issue_ids_in_file(filepath, epic_titles, feature_titles, story_titles, usecase_titles, rules=rules)
                title = extract_title(filepath)
                if not title:
                    continue
                
                issue_num = resolve_spec_issue_number(
                    filepath, title, story_titles, issue_dict, rules=rules,
                    item_type="User Story", claimed=claimed_issues,
                )
                if issue_num is not None:
                    _, completed = update_checklist_in_file(filepath, issue_dict, rules)
                    is_open = str(issue_dict[issue_num][state_key]).upper() == keys.get("open_state_value", "OPEN").upper()
                    if is_open:
                        sync_issue_body_to_tracker(
                            issue_num, filepath, issue_type="User Story", rules=rules,
                            issue_record=issue_dict[issue_num],
                        )
                        if completed and not is_already_resolved(issue_dict[issue_num], rules):
                            resolve_issue_on_tracker(
                                issue_num,
                                story_comment_template.format(title=title),
                                rules=rules
                            )
                            issue_dict[issue_num].setdefault("labels", []).append(
                                {"name": get_resolved_label(rules)}
                            )
                else:
                    print(
                        f"Warning: No User Story issue on the tracker for {filename} — "
                        f"no issue_id in its frontmatter and no title match for '{title}'"
                    )

        # Process Use Cases
        if os.path.exists(usecases_dir):
            for filename in sorted(os.listdir(usecases_dir)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(usecases_dir, filename)
                if filename in blocked_specs:
                    print(f'  [Skipped] {filename} - blocked by linter findings (#321)')
                    continue
                resolve_issue_ids_in_file(filepath, epic_titles, feature_titles, story_titles, usecase_titles, rules=rules)
                title = extract_title(filepath)
                if not title:
                    continue
                
                issue_num = resolve_spec_issue_number(
                    filepath, title, usecase_titles, issue_dict, rules=rules,
                    item_type="Use Case", claimed=claimed_issues,
                )
                if issue_num is not None:
                    _, completed = update_checklist_in_file(filepath, issue_dict, rules)
                    is_open = str(issue_dict[issue_num][state_key]).upper() == keys.get("open_state_value", "OPEN").upper()
                    if is_open:
                        sync_issue_body_to_tracker(
                            issue_num, filepath, issue_type="Use Case", rules=rules,
                            issue_record=issue_dict[issue_num],
                        )
                        if completed and not is_already_resolved(issue_dict[issue_num], rules):
                            resolve_issue_on_tracker(
                                issue_num,
                                usecase_comment_template.format(title=title),
                                rules=rules
                            )
                            issue_dict[issue_num].setdefault("labels", []).append(
                                {"name": get_resolved_label(rules)}
                            )
                else:
                    print(
                        f"Warning: No Use Case issue on the tracker for {filename} — "
                        f"no issue_id in its frontmatter and no title match for '{title}'"
                    )

        if blocked_specs:
            # Issue #321 - skipping is not tolerance. Everything valid has now been
            # synchronised, but the corpus still contains specifications the linter
            # rejected, so the run reports failure. A caller that treated a skipped
            # item as published would be the gate quietly disappearing.
            print(
                f"Backlog reconciliation complete for valid specifications. "
                f"{len(blocked_specs)} specification(s) were SKIPPED because the "
                f"linter rejected them: {', '.join(sorted(blocked_specs))}",
                file=sys.stderr,
            )
            sys.exit(1)

        print("Backlog reconciliation complete.")

    except BaseException as e:
        exit_code = 1
        if isinstance(e, SystemExit):
            if isinstance(e.code, int):
                exit_code = e.code
            elif e.code is None:
                exit_code = 0
        
        if exit_code != 0:
            tb_str = traceback.format_exc()
            print(tb_str, file=sys.stderr)
            try:
                # Insert the src directory of the parity_auditor package into sys.path
                src_dir = os.path.abspath(os.path.join(workspace_dir, "skills", "spec-orchestrator", "parity_auditor", "src"))
                if src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                from parity_auditor.utils.diagnostics import serialize_diagnostics
                serialize_diagnostics(
                    workspace_dir=workspace_dir,
                    tool_name="reconcile_backlog",
                    exit_code=exit_code,
                    errors=[str(e)],
                    traceback_str=tb_str
                )
            except Exception as diag_err:
                print(f"Warning: Failed to serialize diagnostics: {diag_err}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
# Refresh commit timestamp
