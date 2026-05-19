"""Markdown note generation with YAML frontmatter."""
from datetime import date
from pathlib import Path

import yaml


def build_markdown(record: dict, today: date | None = None) -> str:
    """Render a normalized record into markdown with YAML frontmatter + body sections."""
    today = today or date.today()
    frontmatter = {
        "title": record["title"],
        "authors": record["authors"],
        "year": record["year"],
        "doi": record.get("doi", ""),
        "pdf_url": record.get("pdf_url", ""),
        "bibkey": record["key"],
        "tags": ["paper/auto-import", f"year/{record['year']}"],
        "imported": today.isoformat(),
    }
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    abstract = record.get("abstract", "")
    return (
        f"---\n{fm_text}\n---\n\n"
        f"## Abstract\n{abstract}\n\n"
        f"## Notes\n"
        f"- [ ] 본문 읽기\n"
        f"- [ ] 인용 가능 구문 추출\n"
        f"- [ ] 본 연구와의 관계 메모\n"
    )


def write_paper(record: dict, out_dir: Path, today: date | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{record['key']}.md"
    path.write_text(build_markdown(record, today=today), encoding="utf-8")
    return path
