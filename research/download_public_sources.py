"""Download public governance datasets when remote endpoints are reachable.

Note: some official endpoints may block automated requests in constrained environments.
Use this script locally/CI with full internet to fetch source files before panel building.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

SOURCES = {
    "wgi_bulk_xlsx": "https://info.worldbank.org/governance/wgi/Home/Reports",
    "vdem_dataset_page": "https://www.v-dem.net/data/the-v-dem-dataset/",
    "manifesto_dataset_page": "https://manifesto-project.wzb.eu/datasets",
}


def download(url: str, dest: Path, timeout: int = 60) -> None:
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 64):
            if chunk:
                f.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", action="append", default=[], help="Direct downloadable URL (can be repeated)")
    parser.add_argument("--out-dir", default="data/raw")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.url:
        print("No direct URLs provided. Official dataset pages:")
        for key, value in SOURCES.items():
            print(f"- {key}: {value}")
        print("\nTip: pass direct file URLs with --url to download artifacts into data/raw.")
        return

    for i, url in enumerate(args.url, start=1):
        filename = url.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
        dest = out_dir / filename
        print(f"Downloading {url} -> {dest}")
        download(url, dest)

    print(f"Downloaded {len(args.url)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
