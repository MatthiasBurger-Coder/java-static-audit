import re
from typing import List, Tuple

RESTTEMPLATE = re.compile(r"new\s+RestTemplate\s*\(")
CATCH_ALL = re.compile(r"catch\s*\(\s*Exception\s*[)\s]")
CACHED_POOL = re.compile(r"Executors\.newCachedThreadPool\s*\(")
WEBCLIENT = re.compile(r"WebClient\.builder\s*\(\s*\)")
FEIGN = re.compile(r"@FeignClient\(")

def scan(java_source: str) -> List[Tuple[str, str]]:
    findings: List[Tuple[str, str]] = []
    if RESTTEMPLATE.search(java_source):
        # Skip if there are obvious timeout hints or a custom RequestFactory in the same file
        timeout_hints = (
            "setConnectTimeout" in java_source or
            "setReadTimeout" in java_source or
            "ClientHttpRequestFactory" in java_source or
            "HttpComponentsClientHttpRequestFactory" in java_source or
            "RequestFactory" in java_source
        )
        if not timeout_hints:
            findings.append(("REST_NO_TIMEOUT",
                            "RestTemplate instantiation detected; ensure custom RequestFactory with connect/read timeouts."))
    if CATCH_ALL.search(java_source):
        findings.append(("CATCH_GENERIC_EXCEPTION",
                        "Catching generic Exception; prefer specific exceptions or rethrow with context."))
    if CACHED_POOL.search(java_source):
        findings.append(("UNBOUNDED_THREADPOOL",
                        "newCachedThreadPool is unbounded; consider bounded pools/Bulkhead patterns."))
    if WEBCLIENT.search(java_source) and "responseTimeout" not in java_source:
        findings.append(("WEBCLIENT_NO_TIMEOUT",
                        "WebClient builder found without explicit responseTimeout; define timeouts."))
    if FEIGN.search(java_source) and "connectTimeout" not in java_source and "readTimeout" not in java_source:
        findings.append(("FEIGN_NO_TIMEOUTS",
                        "Feign client annotation found; ensure connectTimeout/readTimeout in config."))
    return findings
