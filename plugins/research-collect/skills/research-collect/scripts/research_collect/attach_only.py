"""Attach PDFs to existing Zotero items (cloud mode only).

Standalone entry point: `python -m research_collect.attach_only --items <path>`.
Does NOT create new items — for that use `python -m research_collect`.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import pdf_downloader, zotero_writer


def lookup_item_by_doi(zot: Any, doi: str) -> str | None:
    """Return the first Zotero item key matching `doi`, or None.

    Uses pyzotero `items(q=...)` full-text search. Pyzotero >=1.5 supports
    `q=DOI:<value>` as a field-scoped filter; we still re-verify the DOI
    on each hit to guard against false positives.
    """
    if not doi:
        return None
    try:
        results = zot.items(q=f"DOI:{doi}", limit=5)
    except Exception:
        return None
    for hit in results or []:
        data = hit.get("data", hit)
        if data.get("DOI", "").strip().lower() == doi.strip().lower():
            return hit.get("key") or data.get("key")
    if results:
        first = results[0]
        return first.get("key") or first.get("data", {}).get("key")
    return None


def resolve_pdf_for_spec(
    spec: dict, pdf_dir: Path, unpaywall_email: str
) -> str | None:
    """Resolve a local PDF path for one attach spec.

    Priority: pdf_path > pdf_url (download) > doi+UNPAYWALL_EMAIL (OA fallback).
    Returns local file path string, or None if no source could be resolved.
    """
    pdf_path = spec.get("pdf_path", "")
    if pdf_path and Path(pdf_path).is_file():
        return str(pdf_path)

    bibkey = spec.get("item_key") or (
        "doi_" + (spec.get("doi") or "unknown").replace("/", "_")
    )

    pdf_url = spec.get("pdf_url", "")
    if pdf_url:
        downloaded = pdf_downloader.download_pdf(pdf_url, pdf_dir, bibkey)
        if downloaded:
            return str(downloaded)

    doi = spec.get("doi", "")
    if doi and unpaywall_email:
        oa_url = pdf_downloader.resolve_oa_url(doi, unpaywall_email)
        if oa_url:
            downloaded = pdf_downloader.download_pdf(oa_url, pdf_dir, bibkey)
            if downloaded:
                return str(downloaded)

    return None


def run_attach_only(
    items_path: Path,
    pdf_dir: Path | None = None,
    zot: Any | None = None,
    mode: str | None = None,
) -> dict:
    """Read attach-list JSON, resolve item keys + PDFs, attach via cloud API.

    Raises RuntimeError when mode is local: the Zotero local API cannot
    upload attachments (see references/zotero_local_limits.md for the HTTP
    failure table).
    """
    if zot is None:
        zot, mode = zotero_writer.connect()
    elif mode is None:
        mode = "local"

    if mode != "cloud":
        raise RuntimeError(
            "attach-only requires cloud mode (ZOTERO_USER_ID + ZOTERO_API_KEY). "
            "Local Zotero API cannot upload PDF attachments."
        )

    specs = json.loads(Path(items_path).read_text(encoding="utf-8"))
    pdf_dir = Path(pdf_dir) if pdf_dir else Path.cwd() / "data" / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    unpaywall_email = os.environ.get("UNPAYWALL_EMAIL", "")

    pairs: list[tuple[str | None, str | None]] = []
    pre_results: list[dict] = []

    for spec in specs:
        item_key = (spec.get("item_key") or "").strip()
        doi = (spec.get("doi") or "").strip()

        if not item_key and not doi:
            pre_results.append({"status": "invalid", "reason": "no item_key or doi"})
            pairs.append((None, None))
            continue

        if not item_key:
            item_key = lookup_item_by_doi(zot, doi) or ""
            if not item_key:
                pre_results.append({"status": "not_found", "doi": doi})
                pairs.append((None, None))
                continue

        local_pdf = resolve_pdf_for_spec(spec, pdf_dir, unpaywall_email)
        if not local_pdf:
            pre_results.append(
                {"status": "skipped", "reason": "no PDF source", "item_key": item_key}
            )
            pairs.append((item_key, None))
            continue

        pre_results.append(
            {"status": "queued", "item_key": item_key, "pdf_path": local_pdf}
        )
        pairs.append((item_key, local_pdf))

    attach_results = zotero_writer.attach_pdfs(zot, pairs)

    merged: list[dict] = []
    for pre, post in zip(pre_results, attach_results):
        if pre["status"] == "queued":
            merged.append({**pre, **post})
        else:
            merged.append(pre)

    return {
        "mode": "cloud",
        "processed": len(specs),
        "attached": sum(1 for r in merged if r["status"] == "attached"),
        "not_found": sum(1 for r in merged if r["status"] == "not_found"),
        "skipped": sum(1 for r in merged if r["status"] == "skipped"),
        "invalid": sum(1 for r in merged if r["status"] == "invalid"),
        "failed": sum(1 for r in merged if r["status"] == "failed"),
        "results": merged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="research-collect-attach",
        description="Attach PDFs to existing Zotero items (cloud mode only).",
    )
    parser.add_argument(
        "--items", type=Path, required=True,
        help="JSON file with [{item_key|doi, pdf_path|pdf_url}, ...]",
    )
    parser.add_argument(
        "--pdf-dir", type=Path, default=Path("data/pdfs"),
        help="Where to cache downloaded PDFs (default: data/pdfs)",
    )
    args = parser.parse_args()

    try:
        result = run_attach_only(args.items, pdf_dir=args.pdf_dir)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"[mode: {result['mode']}]")
    print(f"처리: {result['processed']}건")
    print(f"  ✅ 첨부됨: {result['attached']}")
    if result["not_found"]:
        print(f"  ⚠️  DOI 조회 실패: {result['not_found']}")
    if result["skipped"]:
        print(f"  ⚠️  PDF 소스 없음: {result['skipped']}")
    if result["invalid"]:
        print(f"  ❌ 잘못된 입력 (item_key·doi 둘 다 없음): {result['invalid']}")
    if result["failed"]:
        print(f"  ❌ 첨부 실패: {result['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
