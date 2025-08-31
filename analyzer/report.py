from pathlib import Path
import pandas as pd
import re
from typing import List, Dict, Tuple

# --- Thresholds for normalized lack of cohesion ---
RED_THR = 0.80
YEL_THR = 0.40

# Classes that often have legitimately low cohesion (pattern exceptions)
EXEMPTION_PATTERNS = re.compile(r"(Aspect|State|NullObject|Repository|Listener)", re.IGNORECASE)

# Rule -> default severity
RULE_SEVERITY = {
    "PARSE_ERROR": "🟨",
    "STATIC_STATE_MUTATION": "🟨",
    "REST_NO_TIMEOUT": "🟥",
    "CATCH_GENERIC_EXCEPTION": "🟨",
    "UNBOUNDED_THREADPOOL": "🟥",
    "WEBCLIENT_NO_TIMEOUT": "🟥",
    "FEIGN_NO_TIMEOUTS": "🟥",
    "POST_WRITE_NO_IDEMPOTENCY_HINT": "🟥",
    "NON_DETERMINISM": "🟨",
}

def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _normalized_lack_of_cohesion(methods: int, lcom: float) -> float:
    if methods is None or lcom is None:
        return 0.0
    m = int(methods)
    if m < 2:
        return 0.0
    denom = m * (m - 1) / 2.0
    if denom <= 0:
        return 0.0
    val = float(lcom) / denom
    return max(0.0, min(1.0, val))

def _class_severity(methods: int, lcom: float, class_name: str) -> Tuple[str, str, float]:
    nlc = _normalized_lack_of_cohesion(methods, lcom)
    if nlc >= RED_THR:
        sev = "🟥"
    elif nlc >= YEL_THR:
        sev = "🟨"
    else:
        sev = "🟩"
    note = ""
    if EXEMPTION_PATTERNS.search(class_name or "") and sev != "🟩":
        note = "Pattern exception (type tends to have low cohesion); downgraded by one level."
        sev = "🟨" if sev == "🟥" else "🟩"
    return sev, note, nlc

def _path_to_package(path: str) -> str:
    p = (path or "").replace("\\", "/")
    if "/java/" in p:
        pkg_part = p.split("/java/", 1)[1]
        if "/" in pkg_part:
            pkg_part = pkg_part.rsplit("/", 1)[0]
        return pkg_part.replace("/", ".")
    if "/" in p:
        pkg_part = p.rsplit("/", 1)[0]
        return pkg_part.replace("/", ".")
    return ""

def _style() -> str:
    return """
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
      h1,h2,h3 { margin-top: 1.2em; }
      table { border-collapse: collapse; width: 100%; margin: 12px 0; }
      th, td { border: 1px solid #ddd; padding: 8px; }
      th { background: #f5f5f5; text-align: left; }
      tr:nth-child(even) { background: #fafafa; }
      .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-weight: 600; }
      .r { background: #ffe5e5; }
      .y { background: #fff4cc; }
      .g { background: #e6ffed; }
      .muted { color: #666; font-size: 0.9em; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
      .card { border: 1px solid #eee; border-radius: 12px; padding: 12px; }
      a { color: #0b6bcb; text-decoration: none; }
      a:hover { text-decoration: underline; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .explain { margin: 10px 0 20px; padding: 12px; background: #f9fafb; border: 1px dashed #dcdcdc; border-radius: 10px;}
    </style>
    """

def _sev_class(emoji: str) -> str:
    return {"🟥": "pill r", "🟨": "pill y", "🟩": "pill g"}.get(emoji, "pill")

def _write_html(path: Path, html: str) -> None:
    path.write_text(html, encoding="utf-8")

def _header(title: str, subtitle: str = "") -> str:
    sub = f"<p class='muted'>{_html_escape(subtitle)}</p>" if subtitle else ""
    return f"<head><meta charset='utf-8'><title>{_html_escape(title)}</title>{_style()}</head><body><h1>{_html_escape(title)}</h1>{sub}"

def _footer() -> str:
    return "</body>"

def _legend() -> str:
    return f"""
    <div class='card'>
      <h3>Traffic Light Criteria (Lack of Cohesion, normalized)</h3>
      <ul>
        <li><span class='{_sev_class("🟥")}'>&nbsp;🟥 Red&nbsp;</span> normalized ≥ {int(RED_THR*100)}%</li>
        <li><span class='{_sev_class("🟨")}'>&nbsp;🟨 Yellow&nbsp;</span> {int(YEL_THR*100)}% ≤ normalized &lt; {int(RED_THR*100)}%</li>
        <li><span class='{_sev_class("🟩")}'>&nbsp;🟩 Green&nbsp;</span> normalized &lt; {int(YEL_THR*100)}%</li>
      </ul>
      <p class='muted'>Pattern exceptions (Aspect/State/NullObject/Repository/Listener) are downgraded by one level.</p>
    </div>
    """

def _package_slug(pkg: str) -> str:
    return (pkg or "root").replace(".", "-").replace("/", "-")

def _top_classes_table(df) -> str:
    rows = ["<table><tr><th>Class</th><th>Methods</th><th>LCOM</th><th>Lack of Cohesion (normalized)</th><th>Severity</th><th>Note</th></tr>"]
    for _, r in df.iterrows():
        nlc = int(round((r.get("normalized_lack_of_cohesion") or 0.0) * 100))
        sev = r.get("severity","🟨")
        rows.append(
            f"<tr><td><span class='mono'>{_html_escape(r.get('class',''))}</span></td>"
            f"<td>{int(r.get('methods',0) or 0)}</td>"
            f"<td>{_html_escape(str(r.get('lcom','')))}</td>"
            f"<td>{nlc}%</td>"
            f"<td><span class='{_sev_class(sev)}'>&nbsp;{sev}&nbsp;</span></td>"
            f"<td>{_html_escape(r.get('note',''))}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)

def _findings_list(dff) -> str:
    out = []
    if dff.empty:
        return "<p class='muted'>No findings.</p>"
    for _, r in dff.head(300).iterrows():
        rule = str(r.get("rule",""))
        sev = r.get("sev", RULE_SEVERITY.get(rule, "🟨"))
        msg = r.get("message", "(no message)") or "(no message)"
        file = r.get("file","")
        out.append(f"<li><span class='{_sev_class(sev)}'>&nbsp;{sev}&nbsp;</span> <span class='mono'>{_html_escape(file)}</span> — <b>{_html_escape(rule)}</b>: {_html_escape(msg)}</li>")
    return "<ul>" + "\n".join(out) + "</ul>"

def _files_table(dffiles) -> str:
    if dffiles.empty:
        return "<p class='muted'>No files.</p>"
    rows = ["<table><tr><th>File</th><th>Lines (total)</th><th>Lines (logical)</th><th>Complexity (heuristic)</th></tr>"]
    for _, r in dffiles.iterrows():
        rows.append(
            f"<tr><td><span class='mono'>{_html_escape(r.get('file',''))}</span></td>"
            f"<td>{int(r.get('loc_total',0) or 0)}</td>"
            f"<td>{int(r.get('loc_logical',0) or 0)}</td>"
            f"<td>{int(r.get('complexity_est',0) or 0)}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)

def _augment_class_df(dfc: pd.DataFrame) -> pd.DataFrame:
    dfc2 = dfc.copy()
    dfc2["class"] = dfc2["class"].fillna("")
    dfc2["package"] = dfc2["file"].map(_path_to_package)
    dfc2["normalized_lack_of_cohesion"] = dfc2.apply(lambda r: _normalized_lack_of_cohesion(int(r.get("methods", 0) or 0), float(r.get("lcom") or 0.0)), axis=1)
    sev_note_nlc = dfc2.apply(lambda r: _class_severity(int(r.get("methods", 0) or 0), float(r.get("lcom") or 0.0), str(r.get("class",""))), axis=1)
    dfc2["severity"] = [t[0] for t in sev_note_nlc]
    dfc2["note"]      = [t[1] for t in sev_note_nlc]
    dfc2["nlc"]       = [t[2] for t in sev_note_nlc]
    return dfc2

def _augment_files_df(df_files: pd.DataFrame) -> pd.DataFrame:
    dff = df_files.copy()
    dff["package"] = dff["file"].map(_path_to_package)
    return dff

def _augment_findings_df(dff: pd.DataFrame) -> pd.DataFrame:
    dff2 = dff.copy()
    if not dff2.empty:
        dff2["package"] = dff2["file"].map(_path_to_package)
        dff2["sev"] = dff2["rule"].map(lambda r: RULE_SEVERITY.get(str(r), "🟨"))
    return dff2

def _class_interpretation(row: Dict) -> str:
    """Generate an English explanation of the class metrics & meaning."""
    cls = str(row.get("class",""))
    m = int(row.get("methods",0) or 0)
    lcom = row.get("lcom", None)
    nlc = float(row.get("normalized_lack_of_cohesion") or 0.0)
    sev = row.get("severity","🟨")
    note = row.get("note","")
    nlc_pct = int(round(nlc*100))
    meaning = []
    meaning.append(f"<b>{_html_escape(cls)}</b> has <b>{m}</b> methods. ")
    meaning.append(f"The <i>normalized lack of cohesion</i> is <b>{nlc_pct}%</b> ")
    meaning.append(f"(<span class='{_sev_class(sev)}'>&nbsp;{sev}&nbsp;</span>), ")
    if sev == "🟥":
        meaning.append("which indicates methods rarely share state. Consider splitting responsibilities (SRP), extracting cohesive components, or injecting collaborators. ")
    elif sev == "🟨":
        meaning.append("which is moderate; review the class responsibilities and check for utility/god-class smells. ")
    else:
        meaning.append("which suggests good cohesion. ")
    if isinstance(lcom, (int, float)):
        meaning.append(f"Raw LCOM = <code>{lcom}</code>. ")
    if note:
        meaning.append(f"Note: { _html_escape(note) } ")
    meaning.append("Heuristic tip: if methods mainly call collaborators (e.g., <code>repo.save(...)</code>), cohesion can still be good even with low field sharing.")
    return "".join(meaning)

def write_html(out_dir: Path, files_rows: List[Dict], class_rows: List[Dict], findings_rows: List[Dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df_files = pd.DataFrame(files_rows)
    dfc_raw = pd.DataFrame(class_rows)
    dff_raw = pd.DataFrame(findings_rows)

    dfc = _augment_class_df(dfc_raw) if not dfc_raw.empty else pd.DataFrame(columns=["file","class","methods","lcom","package","normalized_lack_of_cohesion","severity","note"])
    dff = _augment_findings_df(dff_raw) if not dff_raw.empty else pd.DataFrame(columns=["file","rule","message","package","sev"])
    dffiles = _augment_files_df(df_files) if not df_files.empty else pd.DataFrame(columns=["file","package"])

    # --- INDEX.HTML ---
    title = "Static Audit Report"
    html = [_header(title, "Global overview"), _legend()]
    # summary cards
    html.append("<div class='grid'>")
    html.append(f"<div class='card'><div class='muted'>Files</div><div><b>{len(df_files)}</b></div></div>")
    html.append(f"<div class='card'><div class='muted'>Classes</div><div><b>{len(dfc)}</b></div></div>")
    html.append(f"<div class='card'><div class='muted'>Findings</div><div><b>{len(dff)}</b></div></div>")
    html.append("</div>")

    # Top risky classes (global)
    if not dfc.empty:
        sev_rank = {'🟥':2,'🟨':1,'🟩':0}
        top = dfc.assign(sev_rank=dfc["severity"].map(sev_rank)).sort_values(["sev_rank","normalized_lack_of_cohesion"], ascending=[False,False]).head(20)
        html.append("<h2>Top 20 risky classes (global)</h2>")
        html.append(_top_classes_table(top))

    # Package list with links
    pkgs = sorted([p for p in dfc["package"].dropna().unique()]) if not dfc.empty else []
    if pkgs:
        html.append("<h2>Packages</h2><ul>")
        for p in pkgs:
            slug = _package_slug(p)
            html.append(f"<li><a href='package-{_html_escape(slug)}.html'><span class='mono'>{_html_escape(p)}</span></a></li>")
        html.append("</ul>")
    else:
        html.append("<p class='muted'>No packages detected.</p>")

    html.append(_footer())
    _write_html(out_dir / "index.html", "\n".join(html))

    # --- PER-PACKAGE REPORTS ---
    if pkgs:
        for p in pkgs:
            slug = _package_slug(p)
            sub = [ _header(f"Package: {p}", "Detailed package report"), _legend() ]
            # filter
            dfc_pkg = dfc[dfc["package"] == p]
            dff_pkg = dff[dff["package"] == p]
            dffiles_pkg = dffiles[dffiles["package"] == p]

            # summary
            sub.append("<div class='grid'>")
            sub.append(f"<div class='card'><div class='muted'>Files</div><div><b>{len(dffiles_pkg)}</b></div></div>")
            sub.append(f"<div class='card'><div class='muted'>Classes</div><div><b>{len(dfc_pkg)}</b></div></div>")
            sub.append(f"<div class='card'><div class='muted'>Findings</div><div><b>{len(dff_pkg)}</b></div></div>")
            sub.append("</div>")

            # top classes in package
            if not dfc_pkg.empty:
                sev_rank = {'🟥':2,'🟨':1,'🟩':0}
                top_pkg = dfc_pkg.assign(sev_rank=dfc_pkg["severity"].map(sev_rank)).sort_values(["sev_rank","normalized_lack_of_cohesion"], ascending=[False,False]).head(20)
                sub.append("<h2>Top classes (package)</h2>")
                sub.append(_top_classes_table(top_pkg))

                # full classes table
                sub.append("<h3>All classes</h3>")
                all_tbl = dfc_pkg.sort_values(['severity','normalized_lack_of_cohesion'], ascending=[True,False])
                sub.append(_top_classes_table(all_tbl))

                # explanations per class
                sub.append("<h2>Per-class explanations</h2>")
                for _, row in all_tbl.iterrows():
                    sub.append(f"<div class='explain'>{_class_interpretation(row.to_dict())}</div>")

            # findings
            sub.append("<h2>Findings</h2>")
            sub.append(_findings_list(dff_pkg))

            # files
            sub.append("<h2>Files in package</h2>")
            sub.append(_files_table(dffiles_pkg))

            sub.append("<p><a href='index.html'>&larr; Back to overview</a></p>")
            sub.append(_footer())

            _write_html(out_dir / f"package-{slug}.html", "\n".join(sub))

def write_csvs(out_dir: Path, files_rows: List[Dict], class_rows: List[Dict], findings_rows: List[Dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(files_rows).to_csv(out_dir / "files.csv", index=False)
    dfc = pd.DataFrame(class_rows)
    if not dfc.empty:
        dfc = dfc.copy()
        dfc["normalized_lack_of_cohesion"] = dfc.apply(lambda r: _normalized_lack_of_cohesion(int(r.get("methods", 0) or 0), float(r.get("lcom") or 0.0)), axis=1)
        sev_note_nlc = dfc.apply(lambda r: _class_severity(int(r.get("methods", 0) or 0), float(r.get("lcom") or 0.0), str(r.get("class",""))), axis=1)
        dfc["severity"] = [t[0] for t in sev_note_nlc]
        dfc["note"]     = [t[1] for t in sev_note_nlc]
    dfc.to_csv(out_dir / "classes.csv", index=False)
    pd.DataFrame(findings_rows).to_csv(out_dir / "findings.csv", index=False)
