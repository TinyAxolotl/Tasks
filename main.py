#!/usr/bin/env python3
"""
Download all available MPP exam tasks from the Azure blob bucket
https://mppexam.blob.core.windows.net/comission-2025/
"""
import argparse
import os
import re
from pathlib import Path
import requests

BASE_URL = "https://mppexam.blob.core.windows.net/comission-2025/"
DIFFICULTIES = ("A", "B", "C")
DEFAULT_MAX_NUM = 999
CONSECUTIVE_MISSES_LIMIT = 25

SESSION = requests.Session()
IMG_SRC_RE = re.compile(r"<img[^>]+src=[\'\"]?([^\'\" >]+)", re.I)


def resolve_url(src: str) -> str:
    if src.startswith("http://") or src.startswith("https://"):
        return src
    return BASE_URL + src.lstrip("/")


def detect_encoding(resp: requests.Response) -> str:
    """Return best-guess encoding for the response body."""
    if resp.apparent_encoding:
        return resp.apparent_encoding
    return "windows-1251"  # fallback that works for MPP pages

def download_image(img_url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = SESSION.get(img_url, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  !  failed image {img_url}: {e}")
        return
    dest.write_bytes(r.content)
    print(f"  ↳ saved img {dest.relative_to(dest.parents[2])}")


def process_html(letter: str, num: int, resp: requests.Response, out_dir: Path) -> None:
    variant = f"{letter}{num:03d}"
    html_path = out_dir / f"{variant}.html"
    html_path.write_bytes(resp.content)
    print(f"✔  saved {variant}.html")

    enc = detect_encoding(resp)
    try:
        html_text = resp.content.decode(enc, errors="replace")
    except LookupError:
        html_text = resp.text

    for src in IMG_SRC_RE.findall(html_text):
        img_url = resolve_url(src)
        filename = os.path.basename(img_url.split("?", 1)[0])
        dest = out_dir / "images" / variant / filename
        if not dest.exists():
            download_image(img_url, dest)


def download_series(letter: str, out_dir: Path, max_num: int) -> None:
    misses = 0
    found_any = False
    for num in range(1, max_num + 1):
        name = f"{letter}{num:03d}.html"
        url = BASE_URL + name
        try:
            resp = SESSION.get(url, timeout=10)
        except requests.RequestException as err:
            print(f"!  error fetching {url}: {err}")
            continue

        valid = resp.status_code == 200 and b"404" not in resp.content[:512]
        if valid:
            process_html(letter, num, resp, out_dir)
            found_any = True
            misses = 0
        else:
            if found_any:
                misses += 1
                if misses >= CONSECUTIVE_MISSES_LIMIT:
                    print(f"↪  stopping at {letter}{num:03d} after {CONSECUTIVE_MISSES_LIMIT} misses")
                    break


def main() -> None:
    argp = argparse.ArgumentParser(description="Download MPP exam tasks & images (encoding-safe, no deps)")
    argp.add_argument("-o", "--output", default="tasks", help="folder to save the files")
    argp.add_argument("-n", "--max-num", type=int, default=DEFAULT_MAX_NUM,
                      help="highest variant number to test (default: 999)")
    args = argp.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for letter in DIFFICULTIES:
        print(f"\n=== Fetching series {letter} ===")
        download_series(letter, out_dir, args.max_num)

    print("\nDone! Everything stored under", out_dir.resolve())


if __name__ == "__main__":
    main()
