import javalang
from javalang.ast import Node
from typing import Dict, List, Set, Any, Iterable

def _collect_fields(type_decl: Any) -> Set[str]:
    """Collect declared field names of a class/interface."""
    fields = set()
    for m in getattr(type_decl, "fields", []):
        for decl in m.declarators:
            fields.add(decl.name)
    return fields

def _method_bodies(type_decl: Any) -> List[Any]:
    """Return list of method declarations with bodies (skip abstract/interface)."""
    out = []
    for m in getattr(type_decl, "methods", []):
        if getattr(m, "body", None) is not None:
            out.append(m)
    return out

def _walk_ast(obj: Any) -> Iterable[Node]:
    """Iterative walk that accepts Node or list/tuple and yields Node instances."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if cur is None:
            continue
        if isinstance(cur, Node):
            yield cur
            for ch in cur.children:  # children can be Node or sequences
                if isinstance(ch, (list, tuple)):
                    stack.extend(ch)
                else:
                    stack.append(ch)
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)

def _used_members_in_method(meth: Any, candidate_fields: Set[str]) -> Set[str]:
    """Approximate set of field names used in method body.
    Treats both MemberReference and MethodInvocation qualifiers as field usage.
    Supports qualifier chains like 'this.repo' or 'service.repo' by matching the last segment.
    """
    used = set()
    if not getattr(meth, "body", None):
        return used
    for node in _walk_ast(meth.body):
        # Direct member access, e.g., 'this.field' or 'field'
        if isinstance(node, javalang.tree.MemberReference):
            name = getattr(node, "member", None)
            qual = getattr(node, "qualifier", None)
            if name in candidate_fields and (qual is None or qual == "this"):
                used.add(name)
            # also consider qualifier chains like 'this.repo.field' – conservative: last segment
            if qual:
                last = str(qual).split(".")[-1]
                if last in candidate_fields:
                    used.add(last)

        # Method call on a field, e.g., 'repo.save(...)' or 'this.repo.save(...)'
        if isinstance(node, javalang.tree.MethodInvocation):
            qual = getattr(node, "qualifier", None)
            if qual:
                last = str(qual).split(".")[-1]
                if last in candidate_fields:
                    used.add(last)
    return used
    for node in _walk_ast(meth.body):
        if isinstance(node, javalang.tree.MemberReference):
            name = getattr(node, "member", None)
            qual = getattr(node, "qualifier", None)
            if name in candidate_fields and (qual is None or qual == "this"):
                used.add(name)
    return used

def classes_with_lcom(java_source: str, filename: str) -> list[dict]:
    """Parse a compilation unit and compute an LCOM-like cohesion metric per class.
    Returns list of dicts: {file, class, methods, lcom, fields}
    """
    results: list[dict] = []
    try:
        tree = javalang.parse.parse(java_source)
    except Exception as e:
        return [{"file": filename, "class": "<PARSE_ERROR>", "methods": 0, "lcom": None, "error": str(e)}]

    types = [t for t in tree.types if hasattr(t, "name")]
    for t in types:
        if t.__class__.__name__ in ("ClassDeclaration",):
            fields = _collect_fields(t)
            methods = _method_bodies(t)
            method_field_use: Dict[str, Set[str]] = {}
            for m in methods:
                used = _used_members_in_method(m, fields)
                method_field_use[m.name] = used

            meths = list(method_field_use.keys())
            p_no_share = 0
            p_share = 0
            for i in range(len(meths)):
                for j in range(i + 1, len(meths)):
                    a, b = meths[i], meths[j]
                    if method_field_use[a] & method_field_use[b]:
                        p_share += 1
                    else:
                        p_no_share += 1
            lcom = max(p_no_share - p_share, 0)
            results.append({
                "file": filename,
                "class": t.name,
                "methods": len(meths),
                "lcom": lcom,
                "fields": list(fields),
            })
    return results
