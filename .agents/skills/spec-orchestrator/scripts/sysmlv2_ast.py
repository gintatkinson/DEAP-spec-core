#!/usr/bin/env python3
"""
SysML v2 Abstract Syntax Tree (AST) Data Models

Provides Canonical SysML v2 AST elements:
- AttributeDef: Defines attributes (data elements / primitive types)
- PortDef: Defines ports (flow / interaction interfaces)
- ActionDef: Defines actions / operations / methods
- PartDef: Defines structural components (parts / blocks)
- SysMLPackage: Top-level or nested SysML v2 package container
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AttributeDef:
    name: str
    type_name: str = "String"
    doc: str = ""
    default_value: Optional[str] = None

    def to_sysml(self, indent: int = 4) -> str:
        pad = " " * indent
        doc_str = f"{pad}doc /* {self.doc} */\n" if self.doc else ""
        def_str = f" = {self.default_value}" if self.default_value is not None else ""
        return f"{doc_str}{pad}attribute {self.name} : {self.type_name}{def_str};"


@dataclass
class PortDef:
    name: str
    type_name: str = "Port"
    direction: str = "inout"
    doc: str = ""

    def to_sysml(self, indent: int = 4) -> str:
        pad = " " * indent
        doc_str = f"{pad}doc /* {self.doc} */\n" if self.doc else ""
        return f"{doc_str}{pad}port {self.name} : {self.type_name};"


@dataclass
class ActionDef:
    name: str
    doc: str = ""
    in_params: List[AttributeDef] = field(default_factory=list)
    out_params: List[AttributeDef] = field(default_factory=list)

    def to_sysml(self, indent: int = 4) -> str:
        pad = " " * indent
        doc_str = f"{pad}doc /* {self.doc} */\n" if self.doc else ""
        all_params = []
        for p in (self.in_params or []):
            all_params.append(f"in {p.name} : {p.type_name}")
        for p in (self.out_params or []):
            all_params.append(f"out {p.name} : {p.type_name}")
        params_str = f"({', '.join(all_params)})" if all_params else ""
        return f"{doc_str}{pad}action {self.name}{params_str};"


@dataclass
class PartDef:
    name: str
    doc: str = ""
    attributes: List[AttributeDef] = field(default_factory=list)
    ports: List[PortDef] = field(default_factory=list)
    actions: List[ActionDef] = field(default_factory=list)
    parts: List['PartDef'] = field(default_factory=list)

    def to_sysml(self, indent: int = 4) -> str:
        pad = " " * indent
        lines = []
        if self.doc:
            lines.append(f"{pad}doc /* {self.doc} */")
        lines.append(f"{pad}part def {self.name} {{")

        for attr in (self.attributes or []):
            lines.append(attr.to_sysml(indent + 4))
        for port in (self.ports or []):
            lines.append(port.to_sysml(indent + 4))
        for act in (self.actions or []):
            lines.append(act.to_sysml(indent + 4))
        for subpart in (self.parts or []):
            lines.append(subpart.to_sysml(indent + 4))

        lines.append(f"{pad}}}")
        return "\n".join(lines)


@dataclass
class SysMLPackage:
    name: str
    doc: str = ""
    part_defs: List[PartDef] = field(default_factory=list)
    attribute_defs: List[AttributeDef] = field(default_factory=list)
    port_defs: List[PortDef] = field(default_factory=list)
    action_defs: List[ActionDef] = field(default_factory=list)
    sub_packages: List['SysMLPackage'] = field(default_factory=list)

    def to_sysml(self, indent: int = 0) -> str:
        pad = " " * indent
        lines = []
        if self.doc:
            lines.append(f"{pad}doc /* {self.doc} */")
        lines.append(f"{pad}package {self.name} {{")

        for attr in (self.attribute_defs or []):
            lines.append(attr.to_sysml(indent + 4))
        for port in (self.port_defs or []):
            lines.append(port.to_sysml(indent + 4))
        for act in (self.action_defs or []):
            lines.append(act.to_sysml(indent + 4))
        for part in (self.part_defs or []):
            lines.append(part.to_sysml(indent + 4))
        for subpkg in (self.sub_packages or []):
            lines.append(subpkg.to_sysml(indent + 4))

        lines.append(f"{pad}}}")
        return "\n".join(lines)

    def node_counts(self) -> Dict[str, int]:
        counts = {
            "packages": 1,
            "part_defs": len(self.part_defs or []),
            "attribute_defs": len(self.attribute_defs or []),
            "port_defs": len(self.port_defs or []),
            "action_defs": len(self.action_defs or []),
            "containers": len(self.part_defs or []),
            "lists": len(self.action_defs or []),
            "leaves": len(self.attribute_defs or []),
            "typedefs": 0,
            "identities": 0,
            "groupings": 0,
        }
        for part in (self.part_defs or []):
            counts["attribute_defs"] += len(part.attributes or [])
            counts["port_defs"] += len(part.ports or [])
            counts["action_defs"] += len(part.actions or [])
            counts["leaves"] += len(part.attributes or [])
            counts["lists"] += len(part.actions or [])

        for sub in (self.sub_packages or []):
            sub_counts = sub.node_counts()
            for k in counts:
                counts[k] += sub_counts[k]
        return counts

    def get_all_node_names(self) -> List[str]:
        names = [self.name]
        for attr in (self.attribute_defs or []):
            names.append(attr.name)
        for port in (self.port_defs or []):
            names.append(port.name)
        for act in (self.action_defs or []):
            names.append(act.name)
        for part in (self.part_defs or []):
            names.append(part.name)
            for attr in (part.attributes or []):
                names.append(attr.name)
            for port in (part.ports or []):
                names.append(port.name)
            for act in (part.actions or []):
                names.append(act.name)
        for sub in (self.sub_packages or []):
            names.extend(sub.get_all_node_names())
        return sorted(list(set(names)))
