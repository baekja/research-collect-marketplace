from datetime import date

import yaml

from research_collect.md_writer import build_markdown, write_paper


def _split_frontmatter(text: str) -> tuple[dict, str]:
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:end])
    body = text[end + 5:]
    return fm, body


def test_yaml_frontmatter_roundtrip(sample_record):
    md = build_markdown(sample_record, today=date(2026, 5, 19))
    fm, _ = _split_frontmatter(md)
    assert fm["title"] == sample_record["title"]
    assert fm["authors"] == sample_record["authors"]
    assert fm["year"] == sample_record["year"]
    assert fm["doi"] == sample_record["doi"]
    assert fm["bibkey"] == sample_record["key"]
    assert "paper/auto-import" in fm["tags"]
    assert f"year/{sample_record['year']}" in fm["tags"]
    assert fm["imported"] == "2026-05-19"


def test_body_has_abstract_and_notes_sections(sample_record):
    md = build_markdown(sample_record)
    _, body = _split_frontmatter(md)
    assert "## Abstract" in body
    assert "## Notes" in body
    assert sample_record["abstract"] in body


def test_write_paper_creates_file_at_bibkey_path(tmp_path, sample_record):
    path = write_paper(sample_record, tmp_path)
    assert path.exists()
    assert path.name == "wei2024coupling.md"
    assert path.read_text(encoding="utf-8").startswith("---\n")
