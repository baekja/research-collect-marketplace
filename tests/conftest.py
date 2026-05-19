import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def sample_record():
    return {
        "title": "Coupling Beam Seismic Behavior",
        "authors": ["Zhang Wei", "Park Junho"],
        "year": 2024,
        "doi": "10.1000/xyz",
        "abstract": "We study coupling beams under cyclic loading.",
        "key": "wei2024coupling",
    }


@pytest.fixture
def sample_raw_records():
    return [
        {
            "title": "Coupling Beam Seismic Behavior",
            "authors": ["Zhang Wei", "Park Junho"],
            "year": 2024,
            "doi": "10.1000/xyz",
            "abstract": "Abs 1",
        },
        {
            "title": "Reinforced Concrete Shear Wall under Cyclic Loading",
            "authors": ["Kim Minsu"],
            "year": 2023,
            "doi": "10.1000/abc",
            "abstract": "Abs 2",
        },
    ]


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_zotero_collection():
    """Yield (zot, key, name) for a throwaway test collection; clean up after test."""
    pytest.importorskip("pyzotero")
    from research_collect.zotero_writer import connect

    name = f"AutoImport_test_{uuid.uuid4().hex[:8]}"
    with patch.dict(os.environ, {"ZOTERO_USER_ID": "", "ZOTERO_API_KEY": ""}):
        zot, _ = connect()
    resp = zot.create_collections([{"name": name}])
    key = resp["successful"]["0"]["key"]

    try:
        yield zot, key, name
    finally:
        try:
            for item in zot.collection_items(key):
                try:
                    zot.delete_item(item)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            collection = zot.collection(key)
            zot.delete_collection(collection)
        except Exception:
            pass
