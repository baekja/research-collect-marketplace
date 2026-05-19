from unittest.mock import MagicMock, patch

import httpx
import pytest

from research_collect.pdf_downloader import download_pdf, resolve_oa_url


def _resp(status=200, content=b"%PDF-1.5\nfake content", ctype="application/pdf"):
    r = MagicMock()
    r.status_code = status
    r.content = content
    r.headers = {"content-type": ctype}
    return r


# ---- download_pdf ---------------------------------------------------------


def test_returns_none_on_empty_url(tmp_path):
    assert download_pdf("", tmp_path, "bibkey") is None


def test_returns_none_on_non_200(tmp_path):
    with patch("research_collect.pdf_downloader.httpx.get",
               return_value=_resp(status=404, content=b"<html>not found</html>", ctype="text/html")):
        assert download_pdf("https://example.com/x.pdf", tmp_path, "bibkey") is None


def test_returns_none_when_content_is_html(tmp_path):
    """Paywalls often serve HTML at a .pdf URL — must be rejected via content-type and magic bytes."""
    with patch("research_collect.pdf_downloader.httpx.get",
               return_value=_resp(status=200, content=b"<html>paywall</html>", ctype="text/html")):
        assert download_pdf("https://example.com/paywall.pdf", tmp_path, "bibkey") is None


def test_accepts_pdf_via_content_type(tmp_path):
    body = b"%PDF-1.7\nactual pdf bytes"
    with patch("research_collect.pdf_downloader.httpx.get",
               return_value=_resp(status=200, content=body, ctype="application/pdf")):
        path = download_pdf("https://example.com/ok.pdf", tmp_path, "smith2024")
    assert path is not None
    assert path.name == "smith2024.pdf"
    assert path.read_bytes() == body


def test_accepts_pdf_via_magic_bytes_when_ctype_wrong(tmp_path):
    """Some servers send the wrong content-type — magic bytes still identify a PDF."""
    body = b"%PDF-1.4\nmis-typed pdf"
    with patch("research_collect.pdf_downloader.httpx.get",
               return_value=_resp(status=200, content=body, ctype="application/octet-stream")):
        path = download_pdf("https://example.com/x.pdf", tmp_path, "test")
    assert path is not None
    assert path.read_bytes() == body


def test_returns_none_on_network_error(tmp_path):
    with patch("research_collect.pdf_downloader.httpx.get",
               side_effect=httpx.ConnectError("boom")):
        assert download_pdf("https://example.com/x.pdf", tmp_path, "bibkey") is None


# ---- resolve_oa_url -------------------------------------------------------


def _unpaywall_resp(payload: dict, status: int = 200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


def test_resolve_oa_url_returns_pdf_url_when_oa():
    resp = _unpaywall_resp({
        "is_oa": True,
        "best_oa_location": {"url_for_pdf": "https://example.com/oa.pdf"},
    })
    with patch("research_collect.pdf_downloader.httpx.get", return_value=resp):
        url = resolve_oa_url("10.1234/x", "test@example.com")
    assert url == "https://example.com/oa.pdf"


def test_resolve_oa_url_returns_empty_when_not_oa():
    resp = _unpaywall_resp({"is_oa": False, "best_oa_location": None})
    with patch("research_collect.pdf_downloader.httpx.get", return_value=resp):
        assert resolve_oa_url("10.1234/x", "test@example.com") == ""


def test_resolve_oa_url_returns_empty_when_best_lacks_pdf():
    """OA found but only landing page, no direct PDF URL → treat as miss."""
    resp = _unpaywall_resp({
        "is_oa": True,
        "best_oa_location": {"url": "https://example.com/abstract", "url_for_pdf": None},
    })
    with patch("research_collect.pdf_downloader.httpx.get", return_value=resp):
        assert resolve_oa_url("10.1234/x", "test@example.com") == ""


def test_resolve_oa_url_empty_inputs():
    assert resolve_oa_url("", "test@example.com") == ""
    assert resolve_oa_url("10.1234/x", "") == ""


def test_resolve_oa_url_handles_http_error():
    with patch("research_collect.pdf_downloader.httpx.get",
               side_effect=httpx.ConnectError("boom")):
        assert resolve_oa_url("10.1234/x", "test@example.com") == ""


def test_resolve_oa_url_handles_404():
    resp = _unpaywall_resp({}, status=404)
    with patch("research_collect.pdf_downloader.httpx.get", return_value=resp):
        assert resolve_oa_url("10.bad/doi", "test@example.com") == ""
