"""Zotero writes — two modes:

- **local**: pyzotero (`local=True`) for collection read/create; new items are POSTed
  to the desktop connector endpoint `/connector/saveItems`. PDF attachments are NOT
  possible in this mode (the connector's `attachments` field is metadata-only and the
  Web-API write endpoints are 400/501 in local mode).
- **cloud**: pyzotero with `library_id=USER_ID, api_key=KEY`. Full Web API access —
  `create_items` and `attachment_simple` both work. Required for PDF attachment.

`connect()` auto-selects mode from env (`ZOTERO_USER_ID` + `ZOTERO_API_KEY` → cloud).
"""
import os
from typing import Any

import httpx
from pyzotero import zotero


CONNECTOR_SAVE_URL = "http://localhost:23119/connector/saveItems"


def connect() -> tuple[Any, str]:
    """Return `(zot, mode)`. `mode` is `'cloud'` if both env vars are set, else `'local'`."""
    user_id = os.environ.get("ZOTERO_USER_ID")
    api_key = os.environ.get("ZOTERO_API_KEY")
    if user_id and api_key:
        return zotero.Zotero(library_id=int(user_id), library_type="user", api_key=api_key), "cloud"
    return zotero.Zotero(library_id=0, library_type="user", local=True), "local"


def ensure_collection(zot: Any, name: str) -> str:
    """Return key for collection `name`, creating it if absent. Works in both modes."""
    existing = {c["data"]["name"]: c["key"] for c in zot.collections()}
    if name in existing:
        return existing[name]
    resp = zot.create_collections([{"name": name}])
    return resp["successful"]["0"]["key"]


def _split_creator(name: str) -> dict:
    parts = name.split()
    if not parts:
        return {"creatorType": "author", "firstName": "", "lastName": ""}
    if len(parts) == 1:
        return {"creatorType": "author", "firstName": "", "lastName": parts[0]}
    return {
        "creatorType": "author",
        "firstName": " ".join(parts[:-1]),
        "lastName": parts[-1],
    }


def build_item(record: dict, collection_key: str) -> dict:
    """Build a Zotero journalArticle payload from a normalized record.

    Works for both modes — local connector accepts the same shape, cloud `create_items`
    also.
    """
    return {
        "itemType": "journalArticle",
        "title": record["title"],
        "creators": [_split_creator(n) for n in record["authors"]],
        "date": str(record["year"]),
        "DOI": record.get("doi", ""),
        "abstractNote": record.get("abstract", ""),
        "url": record.get("pdf_url", ""),
        "tags": [
            {"tag": "auto-import"},
            {"tag": f"year/{record['year']}"},
        ],
        "collections": [collection_key],
    }


def connector_save_items(items: list[dict], chunk: int = 30) -> dict:
    """Local-mode write — POST items in chunks to the desktop connector.

    The endpoint returns an empty body on 2xx, so we count successes by chunk size.
    """
    successful_count = 0
    failed: list[dict] = []
    for i in range(0, len(items), chunk):
        batch = items[i:i + chunk]
        resp = httpx.post(CONNECTOR_SAVE_URL, json={"items": batch}, timeout=60.0)
        if 200 <= resp.status_code < 300:
            successful_count += len(batch)
        else:
            failed.append({
                "status": resp.status_code,
                "size": len(batch),
                "body": resp.text[:200],
            })
    return {"successful_count": successful_count, "failed": failed}


def cloud_create_items(zot: Any, items: list[dict], chunk: int = 30) -> dict:
    """Cloud-mode write — pyzotero `create_items` in chunks.

    Returns `item_keys` aligned with input order (failures inserted as None).
    """
    item_keys: list[str | None] = []
    failed: list[dict] = []
    for i in range(0, len(items), chunk):
        batch = items[i:i + chunk]
        resp = zot.create_items(batch)
        successes = resp.get("successful", {})
        failures = resp.get("failed", {})
        for j in range(len(batch)):
            key = str(j)
            if key in successes:
                item_keys.append(successes[key]["key"])
            elif key in failures:
                item_keys.append(None)
                failed.append(failures[key])
            else:
                item_keys.append(None)
                failed.append({"index": i + j, "reason": "no response slot"})
    return {"item_keys": item_keys, "failed": failed}


def attach_pdfs(
    zot: Any,
    pairs: list[tuple[str | None, str | None]],
) -> list[dict]:
    """Attach local PDF files to existing items (cloud mode only).

    `pairs` is a list of `(item_key, pdf_path)` tuples. Either being None or
    falsy means skip. Returns one status dict per pair.
    """
    results: list[dict] = []
    for item_key, pdf_path in pairs:
        if not item_key:
            results.append({"status": "skipped", "reason": "no item_key"})
            continue
        if not pdf_path:
            results.append({"item_key": item_key, "status": "skipped", "reason": "no pdf"})
            continue
        try:
            zot.attachment_simple([str(pdf_path)], item_key)
            results.append({"item_key": item_key, "status": "attached", "path": str(pdf_path)})
        except Exception as e:
            results.append({
                "item_key": item_key,
                "status": "failed",
                "reason": f"{type(e).__name__}: {e}",
            })
    return results
