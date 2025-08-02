import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def normalize_url(url: str) -> str:
    """Return a canonical form of *url* (lower-case scheme/host, strip tracking params, slash-clean)."""
    if not url:
        return url
    parsed = urlparse(url.strip())

    # Lower-case scheme + host, normalize to http for comparison
    scheme = "http"  # Always normalize to http for deduplication
    netloc = parsed.netloc.lower()

    # Remove default ports (both 80 and 443 since we normalize to http)
    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    if netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Remove "www." prefix
    netloc = re.sub(r"^www\.", "", netloc)

    # Clean query string
    query_pairs = [
        p
        for p in parse_qsl(parsed.query, keep_blank_values=False)
        if p[0] not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_pairs))

    # Normalise path – collapse multiple slashes
    path = re.sub(r"/+", "/", parsed.path) or "/"

    canonical = urlunparse((scheme, netloc, path.rstrip("/"), "", query, ""))
    return canonical
