"""Download PDF files via HTTP; resolve OA copies via the Unpaywall API."""
from pathlib import Path
from typing import Optional

import httpx

PDF_MAGIC = b"%PDF-"
UNPAYWALL_API = "https://api.unpaywall.org/v2"


def download_pdf(
    url: str,
    out_dir: Path,
    bibkey: str,
    timeout: float = 120.0,
) -> Optional[Path]:
    """Download a PDF to `out_dir/<bibkey>.pdf`.

    Returns the file path on success, or None when:
    - `url` is empty/falsy
    - HTTP status is not 200
    - The response is not a PDF (content-type lacks 'pdf' AND magic bytes don't match)
    - Any network/IO exception
    """
    if not url:
        return None
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None

    body = resp.content
    ctype = resp.headers.get("content-type", "").lower()
    is_pdf = "pdf" in ctype or body[:5] == PDF_MAGIC
    if not is_pdf:
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{bibkey}.pdf"
    path.write_bytes(body)
    return path


def resolve_oa_url(doi: str, email: str, timeout: float = 10.0) -> str:
    """Look up an open-access PDF URL for a DOI via Unpaywall.

    Returns the PDF URL on success, or '' if:
    - doi or email is empty (Unpaywall ToS requires an email)
    - DOI is not OA / no PDF in best_oa_location
    - API error / timeout / non-200
    """
    if not doi or not email:
        return ""
    try:
        resp = httpx.get(
            f"{UNPAYWALL_API}/{doi}",
            params={"email": email},
            timeout=timeout,
        )
    except httpx.HTTPError:
        return ""
    if resp.status_code != 200:
        return ""
    try:
        data = resp.json()
    except ValueError:
        return ""
    best = data.get("best_oa_location") or {}
    return best.get("url_for_pdf") or ""
