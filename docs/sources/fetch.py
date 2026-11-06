"""Download the source files that are not committed (licence or size) into <source>/local/ and verify them.

    python docs/sources/fetch.py            # fetch missing files, verify every file's SHA-256
    python docs/sources/fetch.py --check    # verify only, download nothing
    python docs/sources/fetch.py --text     # also write .txt extracts next to local PDFs (needs pypdf)

Each docs/sources/<NN-slug>/SOURCE.md lists its files in the frontmatter:
    files:
      - <commit|local> <file name> <sha256> <url>
`commit` files live in git next to SOURCE.md; `local` files are git-ignored under local/.
HTML pages change over time, so a checksum mismatch on .html is reported but not fatal.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = "sdlc360-sources/1.0 (+https://github.com/dryabokon/SDLC360)"


def entries(source_md: Path) -> list[tuple[str, Path, str, str]]:
    text = source_md.read_text(encoding="utf-8")
    front = text.split("---", 2)[1] if text.startswith("---") else ""
    out = []
    for line in front.splitlines():
        parts = line.strip().split()
        if len(parts) == 5 and parts[0] == "-" and parts[1] in ("commit", "local"):
            _, mode, name, sha, url = parts
            path = source_md.parent / name if mode == "commit" else source_md.parent / "local" / name
            out.append((mode, path, sha, url))
    return out


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract_text(pdf: Path) -> None:
    try:
        from pypdf import PdfReader  # dev dependency, see requirements-dev.txt
    except ImportError:
        print("  (pypdf not installed: skipping text extract)")
        return
    reader = PdfReader(str(pdf))
    pages = [f"[page {i}]\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages, 1)]
    pdf.with_suffix(".txt").write_text("\n\n".join(pages), encoding="utf-8")


def main(argv: list[str]) -> int:
    check_only, text = "--check" in argv, "--text" in argv
    failed = 0
    for source_md in sorted(HERE.glob("*/SOURCE.md")):
        for mode, path, want, url in entries(source_md):
            rel = path.relative_to(HERE)
            if not path.exists():
                if check_only or mode == "commit":
                    print(f"MISSING  {rel}")
                    failed += mode == "commit"
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                print(f"fetch    {rel}")
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    path.write_bytes(r.read())
            got = sha256(path)
            if got == want:
                print(f"ok       {rel}")
            elif path.suffix == ".html":
                print(f"changed  {rel} (page updated since retrieval)")
            else:
                print(f"MISMATCH {rel}: expected {want[:12]}, got {got[:12]}")
                failed += 1
            if text and path.suffix == ".pdf" and mode == "local":
                extract_text(path)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
