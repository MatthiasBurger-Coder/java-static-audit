import re
from typing import List, Tuple, Optional

# --- OCP ---
SWITCH = re.compile(r"\bswitch\s*\(", re.MULTILINE)
INSTANCEOF = re.compile(r"\binstanceof\b")
IF_CHAIN = re.compile(r"\bif\s*\(.*instanceof.*\)")

# --- LSP ---
UNSUPPORTED_IN_OVERRIDE = re.compile(r"@Override[\s\S]{0,200}?throw\s+new\s+UnsupportedOperationException", re.MULTILINE)

# --- ISP ---
INTERFACE_DECL_HEADER = re.compile(r"\binterface\s+([A-Za-z_]\w*)\b")
METHOD_SIGNATURE = re.compile(r"[;)]\s*;")
EMPTY_METHOD = re.compile(r"(?:@Override\s*)?(?:public|protected|private)?\s*(?:static\s+)?[\w<>\[\],\s]+\s+\w+\s*\([^)]*\)\s*\{\s*\}", re.MULTILINE)

# --- DIP ---
SPRING_COMPONENT_ANN = re.compile(r"@(?:Service|Component|Controller|RestController)", re.IGNORECASE)
NEW_CONCRETE = re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]+)\s*\(", re.MULTILINE)
CONCRETE_FIELD_IMPL = re.compile(r"\b([A-Z][A-Za-z0-9_]*Impl)\s+\w+\s*(=|;)", re.MULTILINE)

CLASS_HEADER = re.compile(r"\b(class|interface|enum)\s+([A-Za-z_]\w*)")

def _extract_class_blocks(java_source: str) -> List[tuple[str, str, int, int]]:
    """Return list of (kind, name, start_index, end_index) naive by brace counting from header."""
    blocks: List[tuple[str, str, int, int]] = []
    for m in CLASS_HEADER.finditer(java_source):
        kind, name = m.group(1), m.group(2)
        i = m.end()
        # find first '{' after header
        while i < len(java_source) and java_source[i] != "{":
            i += 1
        if i >= len(java_source):  # no body
            continue
        brace = 1
        j = i + 1
        while j < len(java_source) and brace > 0:
            if java_source[j] == "{":
                brace += 1
            elif java_source[j] == "}":
                brace -= 1
            j += 1
        blocks.append((kind, name, i+1, j-1 if brace == 0 else len(java_source)))
    return blocks

def scan(java_source: str) -> List[tuple]:
    """Return list of tuples:
       - (rule, message) for file-scoped
       - or (rule, message, class_name) for class-scoped
    """
    findings: List[tuple] = []

    # Per-class scan
    for kind, name, s, e in _extract_class_blocks(java_source):
        block = java_source[s:e]

        # OCP
        sw = len(SWITCH.findall(block))
        inst = len(INSTANCEOF.findall(block))
        if sw >= 1 and inst >= 2:
            findings.append(("OCP_SMELL_SWITCH_ON_TYPE", f"{name}: switch/instanceof chain suggests type-based branching.", name))
        elif len(IF_CHAIN.findall(block)) >= 2:
            findings.append(("OCP_SMELL_INSTANCEOF_CHAIN", f"{name}: multiple 'instanceof' branches detected.", name))

        # LSP
        if UNSUPPORTED_IN_OVERRIDE.search(block):
            findings.append(("LSP_VIOLATION_UNSUPPORTED", f"{name}: overridden method throws UnsupportedOperationException.", name))

        # ISP (interface fatness only for interfaces)
        if kind == "interface":
            # count method-like signatures in block
            sigs = len(METHOD_SIGNATURE.findall(block))
            if sigs >= 12:
                findings.append(("ISP_SMELL_FAT_INTERFACE", f"Interface {name} exposes {sigs} methods; consider splitting.", name))

        # ISP: many empty method bodies in class
        if kind == "class":
            empties = len(EMPTY_METHOD.findall(block))
            if empties >= 4:
                findings.append(("ISP_SMELL_EMPTY_IMPLEMENTATION", f"{name}: {empties} empty methods; interface may be too broad.", name))

        # DIP
        has_component = bool(SPRING_COMPONENT_ANN.search(java_source[:s])) or bool(SPRING_COMPONENT_ANN.search(block))
        if has_component:
            newc = len(NEW_CONCRETE.findall(block))
            impl_fields = len(CONCRETE_FIELD_IMPL.findall(block))
            if newc >= 2 or impl_fields >= 1:
                findings.append(("DIP_VIOLATION_CONCRETE_DEP", f"{name}: directly instantiates concretes or depends on *Impl; prefer abstractions.", name))

    return findings
