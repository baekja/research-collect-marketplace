import os
from unittest.mock import MagicMock, patch

from research_collect.zotero_writer import (
    _split_creator,
    attach_pdfs,
    build_item,
    cloud_create_items,
    connect,
    connector_save_items,
)


# ---- build_item / split_creator (mode-agnostic) ---------------------------


def test_build_item_payload_shape(sample_record):
    item = build_item(sample_record, "COLKEY")

    assert item["itemType"] == "journalArticle"
    assert item["title"] == sample_record["title"]
    assert item["date"] == "2024"
    assert item["DOI"] == sample_record["doi"]
    assert item["abstractNote"] == sample_record["abstract"]
    assert item["collections"] == ["COLKEY"]
    assert {"tag": "auto-import"} in item["tags"]
    assert {"tag": "year/2024"} in item["tags"]
    assert all(c["creatorType"] == "author" for c in item["creators"])
    assert item["creators"][0] == {
        "creatorType": "author", "firstName": "Zhang", "lastName": "Wei",
    }


def test_build_item_includes_pdf_url_when_present():
    rec = {
        "title": "T", "authors": ["A B"], "year": 2024, "key": "b2024t",
        "pdf_url": "https://example.com/x.pdf",
    }
    item = build_item(rec, "COL")
    assert item["url"] == "https://example.com/x.pdf"


def test_build_item_url_empty_when_no_pdf_url():
    rec = {"title": "T", "authors": ["A B"], "year": 2024, "key": "b2024t"}
    item = build_item(rec, "COL")
    assert item["url"] == ""


def test_split_creator_single_name():
    assert _split_creator("Zhang") == {
        "creatorType": "author", "firstName": "", "lastName": "Zhang",
    }


def test_split_creator_multi_token():
    assert _split_creator("Van Der Berg") == {
        "creatorType": "author", "firstName": "Van Der", "lastName": "Berg",
    }


# ---- connect() mode selection --------------------------------------------


def test_connect_uses_cloud_when_env_present():
    env = {"ZOTERO_USER_ID": "1234", "ZOTERO_API_KEY": "secretkey"}
    with patch.dict(os.environ, env, clear=False), \
         patch("research_collect.zotero_writer.zotero.Zotero") as MockZ:
        zot, mode = connect()
    assert mode == "cloud"
    MockZ.assert_called_once_with(library_id=1234, library_type="user", api_key="secretkey")


def test_connect_falls_back_to_local_when_env_missing():
    env_minus = {k: "" for k in ("ZOTERO_USER_ID", "ZOTERO_API_KEY")}
    with patch.dict(os.environ, env_minus, clear=False), \
         patch("research_collect.zotero_writer.zotero.Zotero") as MockZ:
        zot, mode = connect()
    assert mode == "local"
    MockZ.assert_called_once_with(library_id=0, library_type="user", local=True)


# ---- connector_save_items (local mode) -----------------------------------


def test_connector_chunks_respect_size():
    items = [{"i": i} for i in range(31)]
    response = MagicMock(status_code=201, text="")
    with patch("research_collect.zotero_writer.httpx.post", return_value=response) as mock_post:
        connector_save_items(items, chunk=30)

    assert mock_post.call_count == 2
    first_payload = mock_post.call_args_list[0].kwargs["json"]
    second_payload = mock_post.call_args_list[1].kwargs["json"]
    assert len(first_payload["items"]) == 30
    assert len(second_payload["items"]) == 1


def test_connector_counts_success_per_chunk():
    items = [{"i": i} for i in range(31)]
    response = MagicMock(status_code=201, text="")
    with patch("research_collect.zotero_writer.httpx.post", return_value=response):
        result = connector_save_items(items, chunk=30)

    assert result["successful_count"] == 31
    assert result["failed"] == []


def test_connector_records_chunk_failure():
    items = [{"i": i} for i in range(5)]
    bad_response = MagicMock(status_code=400, text="Endpoint does not support method")
    with patch("research_collect.zotero_writer.httpx.post", return_value=bad_response):
        result = connector_save_items(items, chunk=30)

    assert result["successful_count"] == 0
    assert len(result["failed"]) == 1
    assert result["failed"][0]["status"] == 400


# ---- cloud_create_items (cloud mode) -------------------------------------


def test_cloud_create_items_returns_keys_in_order():
    zot = MagicMock()
    zot.create_items.return_value = {
        "successful": {"0": {"key": "AAA"}, "1": {"key": "BBB"}, "2": {"key": "CCC"}},
        "failed": {},
        "unchanged": {},
    }
    items = [{"i": i} for i in range(3)]
    result = cloud_create_items(zot, items, chunk=30)
    assert result["item_keys"] == ["AAA", "BBB", "CCC"]
    assert result["failed"] == []


def test_cloud_create_items_records_failed_slot_as_none():
    zot = MagicMock()
    zot.create_items.return_value = {
        "successful": {"0": {"key": "AAA"}, "2": {"key": "CCC"}},
        "failed": {"1": {"message": "bad DOI"}},
        "unchanged": {},
    }
    items = [{"i": i} for i in range(3)]
    result = cloud_create_items(zot, items, chunk=30)
    assert result["item_keys"] == ["AAA", None, "CCC"]
    assert len(result["failed"]) == 1


# ---- attach_pdfs ---------------------------------------------------------


def test_attach_pdfs_skips_none_pdf():
    zot = MagicMock()
    results = attach_pdfs(zot, [("ITEM1", None)])
    assert results[0]["status"] == "skipped"
    zot.attachment_simple.assert_not_called()


def test_attach_pdfs_calls_attachment_simple():
    zot = MagicMock()
    results = attach_pdfs(zot, [("ITEM1", "/tmp/x.pdf")])
    zot.attachment_simple.assert_called_once_with(["/tmp/x.pdf"], "ITEM1")
    assert results[0]["status"] == "attached"


def test_attach_pdfs_records_exception():
    zot = MagicMock()
    zot.attachment_simple.side_effect = RuntimeError("403 forbidden")
    results = attach_pdfs(zot, [("ITEM1", "/tmp/x.pdf")])
    assert results[0]["status"] == "failed"
    assert "RuntimeError" in results[0]["reason"]
