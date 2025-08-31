import re

# Simple cyclomatic complexity estimate by counting decision points.
DECISION_TOKENS = re.compile(r"\b(if|for|while|case|catch|&&|\|\||\?)\b")

def estimate_complexity(java_source: str) -> int:
    """Very rough CC estimate via keyword counting. Useful for ranking only."""
    return len(DECISION_TOKENS.findall(java_source))

def count_loc(java_source: str) -> tuple[int, int]:
    """Return (total_lines, logical_lines_without_comments)."""
    lines = java_source.splitlines()
    total = len(lines)
    logical = 0
    in_block = False
    for line in lines:
        s = line.strip()
        if not in_block:
            if s.startswith("/*"):
                in_block = True
                if s.endswith("*/") and len(s) > 3:
                    in_block = False
                continue
            if s.startswith("//") or s == "":
                continue
            logical += 1
        else:
            if "*/" in s:
                in_block = False
    return total, logical
