import argparse
from pathlib import Path

from analyzer.fs import iter_java_files
from analyzer.metrics import estimate_complexity, count_loc
from analyzer.java_ast import classes_with_lcom_with_fallback
from analyzer.heuristics_idempotency import scan as scan_idemp
from analyzer.heuristics_resilience import scan as scan_res
from analyzer.report import write_html, write_csvs

def main():
    ap = argparse.ArgumentParser(description="Pure static Java source analyzer")
    ap.add_argument("repo", help="Path to repo root")
    ap.add_argument("--out", default="out", help="Output directory")
    ap.add_argument("--include-tests", action="store_true", help="Also scan src/test/java")
    ap.add_argument("--max-file-size", type=int, default=800_000, help="Skip files larger than this (bytes)")
    ap.add_argument("--limit", type=int, default=0, help="Stop after N files (0=all)")
    ap.add_argument("--csv", action="store_true", help="Emit CSV files")
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files_rows = []
    class_rows = []
    findings_rows = []

    count = 0
    for f in iter_java_files(str(root), include_tests=args.include_tests):
        if args.limit and count >= args.limit:
            break
        try:
            size = f.stat().st_size
            if size > args.max_file_size:
                continue
            src = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        total, logical = count_loc(src)
        cc = estimate_complexity(src)

        files_rows.append({
            "file": str(f.relative_to(root)),
            "loc_total": total,
            "loc_logical": logical,
            "complexity_est": cc,
        })

        for row in classes_with_lcom_with_fallback(src, str(f.relative_to(root))):
            if str(row.get('class')) == '<PARSE_ERROR>':
                findings_rows.append({
                    'file': row.get('file', str(f.relative_to(root))),
                    'rule': 'PARSE_ERROR',
                    'message': row.get('error', '(no message)')
                })
                continue
            class_rows.append(row)

        for rule, msg in scan_idemp(src):
            findings_rows.append({"file": str(f.relative_to(root)), "rule": rule, "message": msg})
        for rule, msg in scan_res(src):
            findings_rows.append({"file": str(f.relative_to(root)), "rule": rule, "message": msg})

        count += 1

    write_html(out_dir, files_rows, class_rows, findings_rows)
    if args.csv:
        write_csvs(out_dir, files_rows, class_rows, findings_rows)

    print(f"Scanned files: {len(files_rows)}")
    print(f"Classes parsed: {len(class_rows)}")
    print(f"Findings: {len(findings_rows)}")
    print(f"Report (index): {out_dir / 'index.html'}")

if __name__ == "__main__":
    main()
