# java-static-audit (pure static source analysis)

Scans a Java multi-project monorepo to compute basic metrics and detect heuristic issues **purely from source code**:
- Cohesion (LCOM approximation per class using field usage overlap)
- Simple cyclomatic complexity estimate per method (keyword-based)
- Idempotency heuristics (POST + writes, time/random/state use in handlers)
- Resilience heuristics (no timeouts, catch-all, unbounded executors, etc.)
- Aggregated Markdown report + CSV exports

## Install
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
```
python run.py /path/to/your/java/monorepo --out out
```

Options:
- `--include-tests` : also scan `src/test/java` (default off)
- `--max-file-size` : skip files bigger than N bytes (default 800_000)
- `--limit`         : analyze at most N files (for quick test)
- `--csv`           : also emit CSV files

Output:
- `out/report.md` : human-readable findings
- `out/files.csv`, `out/classes.csv`, `out/findings.csv` (if `--csv` set)

## Notes & Limitations
- This is a static heuristic analyzer; results require engineering judgment.
- LCOM is approximated with field usage overlap. It is useful for ranking refactor targets, not a formal proof.
- Complexity is estimated by counting decision keywords; for exact CC, integrate external tools if desired.
- Extend the regex patterns in `heuristics_*.py` for your codebase idioms.
