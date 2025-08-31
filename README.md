# java-static-audit

Fast, zero-build static analysis for Java codebases. Scan .java files and get a shareable HTML report that pinpoints cohesion issues, SOLID smells, resilience gaps, and idempotency risks — in minutes, without compiling.

- Per-class cohesion metrics (LCOM + normalized lack of cohesion) with traffic‑light severity
- Heuristic SOLID signals (S/O/L/I/D) at class and package level
- Resilience and idempotency checks for common production pitfalls
- Project overview (files, classes, findings) and optional CSV exports

This tool never runs your code; it parses text and applies lightweight heuristics so you can triage hotspots quickly.


## Demo

- Open the generated report: `out\index.html`
- Example package pages are emitted as `out\package-<pkg>.html`


## Why this tool?

- No build required — works directly on sources
- Spots low-cohesion classes (SRP suspects) fast
- Surfaces OCP/LSP/ISP/DIP smells via patterns
- Highlights resilience gaps (timeouts, unbounded executors) and idempotency risks (POST + DB write without dedupe)
- Produces a clean, static HTML overview you can share with teams


## Installation

Requirements:
- Python 3.10+ (recommended)
- Packages (see `requirements.txt`):
  - pandas==2.2.2
  - javalang==0.13.0
  - tree-sitter, tree-sitter-java (optional fallback parser)

Install:

- Using pip (virtual environment recommended):
  pip install -r requirements.txt

Tree-sitter is optional. If `javalang` fails to parse a file and tree-sitter is available, the analyzer falls back to tree-sitter to compute per-class metrics.


## Quick start

- Analyze a Java repository (skipping tests) and generate HTML in `out/`:
  python run.py path\to\java-repo --out out

- Include tests in the scan:
  python run.py path\to\java-repo --include-tests

- Also export CSVs next to the HTML:
  python run.py path\to\java-repo --csv

- Limit the number of processed files (useful for a dry run):
  python run.py path\to\java-repo --limit 200

- Skip very large files (default: 800000 bytes):
  python run.py path\to\java-repo --max-file-size 500000

Outputs are written to the chosen `--out` directory. The console prints a summary and the path to `index.html`.


## What you get

- out/index.html — Global overview
  - Totals: files, classes, findings
  - SOLID summary cards (S, O, L, I, D counts)
  - Top 20 risky classes ranked by normalized lack of cohesion and severity
  - Links to per-package reports

- out/package-<pkg>.html — Per-package details
  - Package summary and SOLID breakdown
  - Top risky classes within the package
  - Per-class explanations: methods count, LCOM, normalized lack of cohesion, severity, and notes
  - SOLID findings for each class and file-scope findings
  - All findings list and files table (LOC totals, logical LOC, heuristic complexity)

- Optional CSVs when using --csv
  - out/files.csv — file-level LOC and complexity
  - out/classes.csv — class metrics with normalized lack of cohesion and severity
  - out/findings.csv — all findings with rule, message, and location


## Heuristics and metrics

- Cohesion (LCOM) per class
  - LCOM computed from pairs of methods that do/do not share field usage
  - Normalized lack of cohesion = LCOM / (M*(M-1)/2) for M≥2, clamped to [0,1]
  - Severity (traffic light):
    - 🟥 Red: normalized ≥ 80%
    - 🟨 Yellow: 40% ≤ normalized < 80%
    - 🟩 Green: normalized < 40%
  - Pattern exceptions (Aspect/State/NullObject/Repository/Listener) are downgraded by one level

- SOLID signals (per class unless noted)
  - SRP_VIOLATION: High normalized LCOM with many methods (detected in runner) suggests too many responsibilities
  - OCP_SMELL_SWITCH_ON_TYPE / OCP_SMELL_INSTANCEOF_CHAIN: Type-based branching or instanceof chains
  - LSP_VIOLATION_UNSUPPORTED: @Override that throws UnsupportedOperationException
  - ISP_SMELL_FAT_INTERFACE: Interfaces exposing many members (≥12)
  - ISP_SMELL_EMPTY_IMPLEMENTATION: Classes with many empty methods (≥4) hinting overly broad interfaces
  - DIP_VIOLATION_CONCRETE_DEP: Spring component instantiates concretes (new ...) or depends on *Impl

- Resilience heuristics (file-scope)
  - REST_NO_TIMEOUT: RestTemplate without custom RequestFactory/explicit timeouts
  - WEBCLIENT_NO_TIMEOUT: WebClient builder without responseTimeout
  - FEIGN_NO_TIMEOUTS: Feign client missing connectTimeout/readTimeout
  - UNBOUNDED_THREADPOOL: Executors.newCachedThreadPool
  - CATCH_GENERIC_EXCEPTION: catch (Exception ...)

- Idempotency heuristics (file-scope)
  - POST_WRITE_NO_IDEMPOTENCY_HINT: @PostMapping + DB write without obvious dedupe key handling
  - NON_DETERMINISM: Uses time and randomness together; consider injection of time/PRNG
  - STATIC_STATE_MUTATION: Mutable static fields (excluding common logger hints)

- Additional per-file stats
  - LOC (total and logical without comments/blank lines)
  - Heuristic complexity estimate: counts if/for/while/case/catch/&&/||/? tokens


## CLI reference

Usage:
  python run.py REPO_PATH [--out OUT_DIR] [--include-tests] [--max-file-size BYTES] [--limit N] [--csv]

Arguments:
- REPO_PATH: path to the root of the Java project to scan
- --out: output directory (default: out)
- --include-tests: also scan src/test/java (default: off)
- --max-file-size: skip files larger than this in bytes (default: 800000)
- --limit: process at most N files (0 = no limit)
- --csv: write CSVs in addition to HTML


## How it works (brief)

- Files: Traverses the repo, skipping common build/IDE/output directories; optionally excludes test sources
- Parsing and metrics: Attempts to parse with javalang; on parse errors and if tree-sitter is available, uses a tree-sitter Java grammar fallback to extract class names, fields, methods, and compute LCOM
- Heuristics: Applies regex-based detectors for SOLID, resilience, and idempotency hints (lightweight and fast)
- Reporting: Aggregates results with pandas and emits a static HTML report (global + per-package pages); CSVs are optional


## Troubleshooting / FAQ

- Do I need tree-sitter? No. It is optional. The analyzer uses `javalang` by default and falls back to tree-sitter only if installed and `javalang` cannot parse a file.
- Windows tips: Use backslashes in paths (as shown). If PowerShell complains about execution policies, run Python with `python` explicitly.
- Pandas/javalang not found: Ensure `pip install -r requirements.txt` completed successfully in your active virtual environment.
- Large repositories: Use `--limit` for a quick preview and adjust `--max-file-size` to skip giant files.


## Development

- Code layout:
  - run.py — CLI entrypoint and main loop
  - analyzer/fs.py — file iteration and exclusions
  - analyzer/metrics.py — LOC and heuristic complexity
  - analyzer/java_ast.py — class parsing + LCOM (javalang with tree-sitter fallback)
  - analyzer/heuristics_*.py — SOLID, resilience, idempotency detectors
  - analyzer/report.py — HTML and CSV generation

- Running from source:
  - Ensure dependencies are installed
  - Execute commands as in Quick start; HTML will be written under the chosen output directory

- Contributing:
  - Keep detectors lightweight and add unit tests where feasible
  - Consider configurability (thresholds, exemptions) if adding new rules


## License

This project is provided as-is. If a LICENSE file is present in the repository, its terms apply. Otherwise, consult the repository owner for licensing and usage permissions.


## What's new (2025-08-31)

- Global Top 20 risky classes on index.html
  - The overview page now includes a "Top classes (global)" table ranked by severity (🟥 > 🟨 > 🟩) and normalized lack of cohesion.
- Heuristic complexity counts operators
  - The heuristic complexity metric now correctly counts &&, ||, and ? tokens in addition to if/for/while/case/catch.
- REST timeout heuristic refined
  - REST_NO_TIMEOUT will no longer trigger if the same file shows clear timeout hints (e.g., setConnectTimeout/setReadTimeout) or usage of a custom ClientHttpRequestFactory.

## Heuristic nuances

- Complexity is a rough estimate intended for ranking; it simply counts occurrences of decision-like tokens.
- REST_NO_TIMEOUT is intentionally conservative but tries to reduce noise by ignoring files that appear to configure timeouts or a custom RequestFactory.
