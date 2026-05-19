"""Deterministic transformations for raw firecrawl records."""
import re
import unicodedata


def _fold_ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def bib_key(authors: list[str], year: int, title: str) -> str:
    """Build BibTeX citation key: <lastname><year><first-title-word>, ASCII-folded."""
    first_author = authors[0]
    last = first_author.split(",")[0] if "," in first_author else first_author.split()[-1]
    last = re.sub(r"[^a-z]", "", _fold_ascii(last).lower())

    tokens = title.split()
    first_word_raw = tokens[0] if tokens else ""
    first_word = re.sub(r"[^a-zA-Z]", "", first_word_raw).lower()

    return f"{last}{year}{first_word}"


def normalize_record(record: dict) -> dict:
    """Coerce a raw firecrawl record to canonical form; raise on missing required fields."""
    for field in ("title", "authors", "year"):
        if field not in record:
            raise ValueError(f"missing required field: {field!r}")

    out = dict(record)
    authors = out["authors"]
    if isinstance(authors, str):
        authors = [authors]
    out["authors"] = authors

    out.setdefault("doi", "")
    out.setdefault("abstract", "")
    out.setdefault("pdf_url", "")

    out["key"] = bib_key(out["authors"], out["year"], out["title"])
    return out
