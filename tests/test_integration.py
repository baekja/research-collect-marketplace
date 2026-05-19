"""Live Zotero integration tests. Run with: pytest -m integration

Preconditions:
- Zotero desktop is running
- Edit → Settings → Advanced → "Allow other applications..." is checked
"""
import json

import pytest

pytestmark = pytest.mark.integration


def test_ensure_collection_idempotent(temp_zotero_collection):
    from research_collect.zotero_writer import ensure_collection

    zot, key, name = temp_zotero_collection
    assert ensure_collection(zot, name) == key


def test_ingest_two_records_roundtrip(tmp_path, sample_raw_records, temp_zotero_collection):
    from research_collect.ingest import run

    zot, key, name = temp_zotero_collection
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(sample_raw_records), encoding="utf-8")

    result = run(
        raw_path=raw_path,
        out_dir=tmp_path / "papers",
        collection=name,
        zot=zot,
    )

    assert result["papers"] == 2
    assert result["registered"] == 2
    assert result["failed"] == 0
    assert result["collection_key"] == key

    md_files = sorted((tmp_path / "papers").glob("*.md"))
    assert len(md_files) == 2

    items = zot.collection_items(key)
    titles = {it["data"]["title"] for it in items}
    assert titles == {r["title"] for r in sample_raw_records}
