"""Unit tests for the attach-only entry point."""
import json
from unittest.mock import MagicMock, patch

import pytest

from research_collect.attach_only import (
    lookup_item_by_doi,
    resolve_pdf_for_spec,
    run_attach_only,
)


# ---- lookup_item_by_doi --------------------------------------------------


class TestLookupItemByDoi:
    def test_returns_key_on_match(self):
        zot = MagicMock()
        zot.items.return_value = [{"key": "AAA", "data": {"DOI": "10.1/x"}}]
        assert lookup_item_by_doi(zot, "10.1/x") == "AAA"

    def test_case_insensitive_doi(self):
        zot = MagicMock()
        zot.items.return_value = [{"key": "AAA", "data": {"DOI": "10.1/X"}}]
        assert lookup_item_by_doi(zot, "10.1/x") == "AAA"

    def test_returns_none_on_empty(self):
        zot = MagicMock()
        zot.items.return_value = []
        assert lookup_item_by_doi(zot, "10.1/x") is None

    def test_returns_none_on_exception(self):
        zot = MagicMock()
        zot.items.side_effect = RuntimeError("network")
        assert lookup_item_by_doi(zot, "10.1/x") is None

    def test_returns_none_on_empty_doi(self):
        zot = MagicMock()
        assert lookup_item_by_doi(zot, "") is None
        zot.items.assert_not_called()


# ---- resolve_pdf_for_spec ------------------------------------------------


class TestResolvePdfForSpec:
    def test_uses_pdf_path_when_file_exists(self, tmp_path):
        f = tmp_path / "x.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = resolve_pdf_for_spec({"pdf_path": str(f)}, tmp_path, "")
        assert result == str(f)

    def test_skips_pdf_path_when_file_missing(self, tmp_path):
        with patch("research_collect.attach_only.pdf_downloader.download_pdf") as dl:
            dl.return_value = None
            result = resolve_pdf_for_spec(
                {"pdf_path": str(tmp_path / "missing.pdf")}, tmp_path, ""
            )
        assert result is None

    def test_downloads_pdf_url(self, tmp_path):
        with patch("research_collect.attach_only.pdf_downloader.download_pdf") as dl:
            dl.return_value = tmp_path / "downloaded.pdf"
            result = resolve_pdf_for_spec(
                {"pdf_url": "https://x.com/y.pdf", "item_key": "K1"}, tmp_path, ""
            )
        assert result == str(tmp_path / "downloaded.pdf")
        dl.assert_called_once()

    def test_unpaywall_fallback(self, tmp_path):
        with patch("research_collect.attach_only.pdf_downloader.resolve_oa_url") as oa, \
             patch("research_collect.attach_only.pdf_downloader.download_pdf") as dl:
            oa.return_value = "https://oa.com/p.pdf"
            dl.return_value = tmp_path / "oa.pdf"
            result = resolve_pdf_for_spec({"doi": "10.1/x"}, tmp_path, "me@uni.edu")
        assert result == str(tmp_path / "oa.pdf")
        oa.assert_called_once_with("10.1/x", "me@uni.edu")

    def test_returns_none_when_no_source(self, tmp_path):
        result = resolve_pdf_for_spec({"item_key": "K"}, tmp_path, "")
        assert result is None


# ---- run_attach_only -----------------------------------------------------


class TestRunAttachOnly:
    @staticmethod
    def _write_specs(tmp_path, specs):
        p = tmp_path / "attach.json"
        p.write_text(json.dumps(specs), encoding="utf-8")
        return p

    def test_local_mode_raises(self, tmp_path):
        zot = MagicMock()
        items = self._write_specs(tmp_path, [{"item_key": "X", "pdf_path": "x"}])
        with pytest.raises(RuntimeError, match="cloud mode"):
            run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="local")

    def test_invalid_spec_no_key_no_doi(self, tmp_path):
        zot = MagicMock()
        items = self._write_specs(tmp_path, [{"pdf_path": str(tmp_path / "x.pdf")}])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        assert result["invalid"] == 1
        assert result["attached"] == 0
        zot.attachment_simple.assert_not_called()

    def test_doi_lookup_not_found(self, tmp_path):
        zot = MagicMock()
        zot.items.return_value = []
        items = self._write_specs(tmp_path, [{"doi": "10.1/ghost", "pdf_path": "x"}])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        assert result["not_found"] == 1
        zot.attachment_simple.assert_not_called()

    def test_attach_with_item_key(self, tmp_path):
        zot = MagicMock()
        f = tmp_path / "real.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        items = self._write_specs(tmp_path, [{"item_key": "ABC", "pdf_path": str(f)}])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        zot.attachment_simple.assert_called_once_with([str(f)], "ABC")
        assert result["attached"] == 1

    def test_attach_with_doi_lookup(self, tmp_path):
        zot = MagicMock()
        zot.items.return_value = [{"key": "DEF", "data": {"DOI": "10.1/x"}}]
        f = tmp_path / "real.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        items = self._write_specs(tmp_path, [{"doi": "10.1/x", "pdf_path": str(f)}])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        zot.attachment_simple.assert_called_once_with([str(f)], "DEF")
        assert result["attached"] == 1

    def test_skipped_when_no_pdf_source(self, tmp_path):
        zot = MagicMock()
        items = self._write_specs(tmp_path, [{"item_key": "K"}])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        zot.attachment_simple.assert_not_called()
        assert result["skipped"] == 1

    def test_mixed_specs_aggregated_counts(self, tmp_path):
        """One attach + one not_found + one invalid + one skipped in one run."""
        zot = MagicMock()
        zot.items.return_value = []  # all DOI lookups fail
        f = tmp_path / "real.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        items = self._write_specs(tmp_path, [
            {"item_key": "ABC", "pdf_path": str(f)},
            {"doi": "10.1/ghost", "pdf_path": "x"},
            {"pdf_path": str(f)},
            {"item_key": "NO_PDF"},
        ])
        result = run_attach_only(items, pdf_dir=tmp_path, zot=zot, mode="cloud")
        assert result["processed"] == 4
        assert result["attached"] == 1
        assert result["not_found"] == 1
        assert result["invalid"] == 1
        assert result["skipped"] == 1
