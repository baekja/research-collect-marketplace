"""CLI entry: `python -m research_collect` or `research-collect`."""
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .ingest import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="research-collect")
    parser.add_argument(
        "--raw", type=Path, default=Path("data/raw.json"),
        help="firecrawl-produced JSON (default: data/raw.json)",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("data/papers"),
        help="markdown output directory (default: data/papers)",
    )
    parser.add_argument(
        "--pdf-dir", type=Path, default=Path("data/pdfs"),
        help="PDF download directory (cloud mode only, default: data/pdfs)",
    )
    parser.add_argument(
        "--collection", default="AutoImport",
        help="Zotero collection name (default: AutoImport)",
    )
    parser.add_argument(
        "--batch", type=int, default=30,
        help="batch size for create_items (max 50)",
    )
    args = parser.parse_args()

    if args.batch > 50:
        parser.error("--batch must be <= 50 (Zotero API limit)")

    result = run(args.raw, args.out, args.collection, args.batch, pdf_dir=args.pdf_dir)

    print(f"[mode: {result['mode']}]")
    print(f"✅ markdown {result['papers']}편 → {args.out}")
    print(
        f"✅ Zotero '{args.collection}' 컬렉션: "
        f"등록 {result['registered']}건 · 실패 {result['failed']}건"
    )
    if result["mode"] == "cloud":
        print(f"✅ PDF 첨부: {result['pdfs_attached']}건")
        for r in result["attach_results"]:
            if r["status"] != "attached":
                print(f"   - {r.get('item_key', '?')}: {r['status']} ({r.get('reason', '')})")


if __name__ == "__main__":
    main()
