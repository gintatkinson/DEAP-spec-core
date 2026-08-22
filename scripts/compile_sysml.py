import sys
import json
import re

def parse_sysml(content):
    ast = {
        "packages": [],
        "part_defs": [],
        "attribute_defs": [],
        "port_defs": [],
        "requirement_defs": [],
        "state_defs": []
    }
    for match in re.finditer(r'package\s+(\w+)', content):
        ast["packages"].append(match.group(1))
    for match in re.finditer(r'part\s+def\s+(\w+)', content):
        ast["part_defs"].append(match.group(1))
    for match in re.finditer(r'attribute\s+def\s+(\w+)', content):
        ast["attribute_defs"].append(match.group(1))
    for match in re.finditer(r'port\s+def\s+(\w+)', content):
        ast["port_defs"].append(match.group(1))
    for match in re.finditer(r'requirement\s+def\s+(\w+)', content):
        ast["requirement_defs"].append(match.group(1))
    for match in re.finditer(r'state\s+def\s+(\w+)', content):
        ast["state_defs"].append(match.group(1))
    return ast

def main():
    if len(sys.argv) < 2:
        print("Usage: compile_sysml.py <file.sysml>")
        sys.exit(1)
    with open(sys.argv[1], 'r') as f:
        content = f.read()
    print(json.dumps(parse_sysml(content), indent=2))

if __name__ == '__main__':
    main()
