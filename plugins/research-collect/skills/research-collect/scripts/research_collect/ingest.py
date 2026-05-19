"""End-to-end orchestration: raw.json → markdown notes + Zotero registration (+ PDF in cloud mode)."""
import json
import os
from pathlib import Path
from typing import Any

from . import md_writer, normalize, pdf_downloader, zotero_writer


def _resolve_pdf_url(rec: dict, unpaywall_email: str) -> str:
    """Use record's pdf_url first; fall back to Unpaywall lookup when DOI present."""
    url = rec.get("pdf_url", "")
    if url:
        return url
    doi = rec.get("doi", "")
    if doi and unpaywall_email:
        return pdf_downloader.resolve_oa_url(doi, unpaywall_email)
    return ""


def run(
    raw_path: Path,
    out_dir: Path,
    collection: str = "AutoImport",
    batch: int = 30,
    zot: Any | None = None,
    mode: str | None = None,
    pdf_dir: Path | None = None,
) -> dict:
    """Read raw.json, write markdown, register Zotero items.

    - **local mode** (default when env vars absent): meta only, via connector.
    - **cloud mode** (when `ZOTERO_USER_ID` + `ZOTERO_API_KEY` set): meta via
      `create_items` + PDF download + `attachment_simple`. If a record's
      `pdf_url` is empty but `doi` is present and `UNPAYWALL_EMAIL` is set,
      tries Unpaywall to find an open-access copy.
    """
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    if zot is None:
        zot, mode = zotero_writer.connect()
    elif mode is None:
        mode = "local"

    pdf_dir = Path(pdf_dir) if pdf_dir else Path(out_dir).parent / "pdfs"
    collection_key = zotero_writer.ensure_collection(zot, collection)

    normalized = []
    items = []
    for rec in raw:
        rec = normalize.normalize_record(rec)
        md_writer.write_paper(rec, Path(out_dir))
        items.append(zotero_writer.build_item(rec, collection_key))
        normalized.append(rec)

    if mode == "cloud":
        create_result = zotero_writer.cloud_create_items(zot, items, chunk=batch)
        item_keys = create_result["item_keys"]
        unpaywall_email = os.environ.get("UNPAYWALL_EMAIL", "")

        pairs: list[tuple[str | None, str | None]] = []
        oa_resolved = 0
        for rec, item_key in zip(normalized, item_keys):
            url = _resolve_pdf_url(rec, unpaywall_email)
            if url and not rec.get("pdf_url"):
                oa_resolved += 1
            pdf_path = pdf_downloader.download_pdf(url, pdf_dir, rec["key"]) if url else None
            pairs.append((item_key, str(pdf_path) if pdf_path else None))

        attach_results = zotero_writer.attach_pdfs(zot, pairs)
        attached = sum(1 for r in attach_results if r["status"] == "attached")
        return {
            "mode": "cloud",
            "papers": len(raw),
            "registered": sum(1 for k in item_keys if k),
            "failed": len(create_result["failed"]),
            "collection_key": collection_key,
            "pdfs_attached": attached,
            "oa_resolved_via_unpaywall": oa_resolved,
            "attach_results": attach_results,
        }

    save_result = zotero_writer.connector_save_items(items, chunk=batch)
    return {
        "mode": "local",
        "papers": len(raw),
        "registered": save_result["successful_count"],
        "failed": len(save_result["failed"]),
        "collection_key": collection_key,
    }
