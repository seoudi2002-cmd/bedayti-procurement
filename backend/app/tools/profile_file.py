"""Command line: python -m app.tools.profile_file <file> [--values] [--ocr N]  → JSON structure profile."""
import argparse
import json
import sys
from pathlib import Path

from app.core.profiling import profile_file


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Profile the structure of an Excel/CSV/Word/PDF file (values hidden by default)")
    ap.add_argument("file")
    ap.add_argument("--values", action="store_true", help="include example/category values (may expose personal data)")
    ap.add_argument("--ocr", type=int, default=0, help="PDF: OCR and classify the first N pages")
    args = ap.parse_args(argv)
    path = Path(args.file)
    print(json.dumps(profile_file(path.name, path.read_bytes(), args.values, args.ocr), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
