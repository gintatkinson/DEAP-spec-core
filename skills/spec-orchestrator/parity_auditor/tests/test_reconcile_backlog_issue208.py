import os
import sys
import tempfile

# Ensure skills/spec-orchestrator/scripts is in sys.path
SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from reconcile_backlog import write_markdown_file, deduplicate_markdown_sections

def test_deduplicate_markdown_sections():
    content = (
        "# Title\n\n"
        "## 1. Description\n"
        "Some description text.\n\n"
        "## 2. Source References\n"
        "First reference section.\n\n"
        "## 2. Source References\n"
        "Duplicate reference section.\n"
    )
    result = deduplicate_markdown_sections(content)
    assert result.count("## 2. Source References") == 1
    assert "First reference section." in result
    assert "Duplicate reference section." not in result

def test_write_markdown_file_deduplicates():
    content = (
        "# Title\n\n"
        "## 1. Description\n"
        "Some description text.\n\n"
        "## 2. Source References\n"
        "First reference section.\n\n"
        "## 2. Source References\n"
        "Duplicate reference section.\n"
    )
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md") as tmp:
        tmp_path = tmp.name

    try:
        written_content = write_markdown_file(tmp_path, content)
        with open(tmp_path, "r", encoding="utf-8") as f:
            disk_content = f.read()
        
        assert written_content == disk_content
        assert disk_content.count("## 2. Source References") == 1
        assert "First reference section." in disk_content
        assert "Duplicate reference section." not in disk_content
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
