import sys
import os

# Add scripts directory to path to import reconcile_backlog
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../skills/spec-orchestrator/scripts')))
import reconcile_backlog

def test_frontmatter_control_character_parsing():
    content = "---\ntitle: \"Test \x01\"\n---\nbody"
    
    # We expect the frontmatter to be successfully parsed and converted to a table,
    # meaning the result should not be the original content.
    # Without sanitization, it returns the original content, so this will fail (RED).
    result = reconcile_backlog.convert_frontmatter_to_table(content)
    assert result != content

