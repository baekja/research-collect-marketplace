import json

from research_collect.normalize import normalize_record


def test_firecrawl_arxiv_fixture_normalizes_cleanly(fixtures_dir):
    raw = json.loads(
        (fixtures_dir / "firecrawl_arxiv_sample.json").read_text(encoding="utf-8")
    )
    for rec in raw:
        out = normalize_record(rec)
        assert out["key"]
        assert isinstance(out["authors"], list) and out["authors"]
        assert isinstance(out["year"], int)


def test_firecrawl_arxiv_fixture_has_required_fields(fixtures_dir):
    raw = json.loads(
        (fixtures_dir / "firecrawl_arxiv_sample.json").read_text(encoding="utf-8")
    )
    required = {"title", "authors", "year"}
    for rec in raw:
        missing = required - rec.keys()
        assert not missing, f"firecrawl sample missing required fields: {missing}"
