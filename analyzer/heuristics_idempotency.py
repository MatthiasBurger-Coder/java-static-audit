import re
from typing import List, Tuple

POST_MAPPING = re.compile(r"@PostMapping|@RequestMapping\s*\([^)]*method\s*=\s*RequestMethod\.POST", re.DOTALL | re.IGNORECASE)
DB_WRITE = re.compile(r"\b(save|insert|persist|merge|update)\s*\(", re.IGNORECASE)
TIME_CALLS = re.compile(r"\b(System\.currentTimeMillis|LocalDateTime\.now|Instant\.now|new\s+Date\s*\()", re.MULTILINE)
RAND_CALLS = re.compile(r"\b(Random\s*\(|Math\.random\(\))", re.MULTILINE)
STATIC_STATE = re.compile(r"\bstatic\b(?!\s+final\b)[^;=]*=", re.MULTILINE)

LOGGER_HINT = re.compile(r"\bLogger\b|\bSlf4j\b|\bLogFactory\b", re.IGNORECASE)

def scan(java_source: str) -> List[Tuple[str, str]]:
    findings: List[Tuple[str, str]] = []
    if POST_MAPPING.search(java_source) and DB_WRITE.search(java_source):
        findings.append(("POST_WRITE_NO_IDEMPOTENCY_HINT",
                        "POST endpoint appears to write to DB without visible dedupe/idempotency key."))
    if TIME_CALLS.search(java_source) and RAND_CALLS.search(java_source):
        findings.append(("NON_DETERMINISM",
                        "Uses time and randomness together; consider injecting time/PRNG for repeatability."))
    if STATIC_STATE.search(java_source) and not LOGGER_HINT.search(java_source):
        findings.append(("STATIC_STATE_MUTATION",
                        "Static mutable state found; may break idempotent retries unless guarded."))
    return findings
