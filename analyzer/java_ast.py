import javalang
from javalang.ast import Node
from typing import Dict, List, Set, Any, Iterable

def _collect_fields(type_decl: Any) -> Set[str]:
    fields = set()
    for m in getattr(type_decl, "fields", []):
        for decl in m.declarators:
            fields.add(decl.name)
    return fields

def _method_bodies(type_decl: Any) -> List[Any]:
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
    used = set()
    if not getattr(meth, "body", None):
        return used
    for node in _walk_ast(meth.body):
        if isinstance(node, javalang.tree.MemberReference):
            name = getattr(node, "member", None)
            qual = getattr(node, "qualifier", None)
            if name in candidate_fields and (qual is None or qual == "this"):
                used.add(name)
            if qual:
                last = str(qual).split(".")[-1]
                if last in candidate_fields:
                    used.add(last)
        if isinstance(node, javalang.tree.MethodInvocation):
            qual = getattr(node, "qualifier", None)
            if qual:
                last = str(qual).split(".")[-1]
                if last in candidate_fields:
                    used.add(last)
    return used

def classes_with_lcom(java_source: str, filename: str) -> list[dict]:
    results: list[dict] = []
    try:
        tree = javalang.parse.parse(java_source)
    except Exception as e:
        return [{"file": filename, "class": "<PARSE_ERROR>", "methods": 0, "lcom": None, "error": str(e)}]

    types = [t for t in getattr(tree, "types", []) if hasattr(t, "name")]
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

def _ts_available() -> bool:
    try:
        import tree_sitter_java  # noqa: F401
        from tree_sitter import Parser, Language  # noqa: F401
        return True
    except Exception:
        return False

def _classes_with_lcom_tree_sitter(java_source: str, filename: str) -> list[dict]:
    try:
        import tree_sitter_java as tsjava
        from tree_sitter import Parser, Language
        JAVA = Language(tsjava.language())
        parser = Parser(JAVA)

        src = java_source.encode("utf-8", errors="ignore")
        tree = parser.parse(src)
        root = tree.root_node

        def text(n): return src[n.start_byte:n.end_byte].decode("utf-8", errors="ignore")

        classes = []
        stack = [root]
        while stack:
            n = stack.pop()
            if n.type == "class_declaration":
                classes.append(n)
            stack.extend(reversed(n.children))

        results = []
        for c in classes:
            cname, cbody = None, None
            for ch in c.children:
                if ch.type == "identifier":
                    cname = text(ch)
                if ch.type == "class_body":
                    cbody = ch
            if cbody is None:
                continue

            fields = set()
            st = [cbody]
            while st:
                n = st.pop()
                if n.type == "field_declaration":
                    for ch in n.children:
                        if ch.type == "variable_declarator":
                            for ch2 in ch.children:
                                if ch2.type == "identifier":
                                    fields.add(text(ch2))
                st.extend(reversed(n.children))

            methods = []
            st = [cbody]
            while st:
                n = st.pop()
                if n.type == "method_declaration":
                    mname, mbody = None, None
                    for ch in n.children:
                        if ch.type == "identifier":
                            mname = text(ch)
                        if ch.type == "block":
                            mbody = ch
                    if mname:
                        methods.append((mname, mbody))
                st.extend(reversed(n.children))

            def used_fields(bnode):
                used = set()
                if bnode is None:
                    return used
                st2 = [bnode]
                while st2:
                    x = st2.pop()
                    if x.type == "field_access":
                        idents = [ch for ch in x.children if ch.type == "identifier"]
                        for idn in idents:
                            nm = text(idn)
                            if nm in fields:
                                used.add(nm)
                    elif x.type == "method_invocation":
                        idents = [ch for ch in x.children if ch.type == "identifier"]
                        if idents:
                            obj = text(idents[0]).split(".")[-1]
                            if obj in fields:
                                used.add(obj)
                    st2.extend(reversed(x.children))
                return used

            mf = {m: used_fields(b) for (m, b) in methods}
            meths = list(mf.keys())
            p_no, p_yes = 0, 0
            for i in range(len(meths)):
                for j in range(i+1, len(meths)):
                    if mf[meths[i]] & mf[meths[j]]:
                        p_yes += 1
                    else:
                        p_no += 1
            lcom = max(p_no - p_yes, 0)
            results.append({"file": filename, "class": cname or "<anon>", "methods": len(meths), "lcom": lcom, "fields": list(fields)})
        return results
    except Exception as e:
        return [{"file": filename, "class": "<PARSE_ERROR>", "methods": 0, "lcom": None, "error": f"tree-sitter-fallback-failed: {e}"}]

def classes_with_lcom_with_fallback(java_source: str, filename: str) -> list[dict]:
    try:
        res = classes_with_lcom(java_source, filename)
        if any(r.get("class") == "<PARSE_ERROR>" for r in res):
            if _ts_available():
                return _classes_with_lcom_tree_sitter(java_source, filename)
        return res
    except Exception:
        if _ts_available():
            return _classes_with_lcom_tree_sitter(java_source, filename)
        return [{"file": filename, "class": "<PARSE_ERROR>", "methods": 0, "lcom": None, "error": "no parser available"}]
