import os
from pathlib import Path
from typing import Iterator

EXCLUDE_DIRS = {
    ".git", ".gradle", "build", "out", "target", ".idea", ".vscode", ".settings",
    "bin", "generated", "node_modules", ".svn", ".hg"
}

def iter_java_files(root: str, include_tests: bool = False) -> Iterator[Path]:
    """Yield all .java files under root, excluding common build dirs.
    Optionally skip test sources by path heuristic.
    """
    rootp = Path(root)
    for dirpath, dirnames, filenames in os.walk(rootp):
        # prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        p = Path(dirpath)
        if not include_tests:
            if "src" in p.parts and "test" in p.parts:
                # skip test sources
                continue
        for f in filenames:
            if f.endswith(".java"):
                yield p / f
