"""Une ingestion manuelle, source HTTPS fixe, sans écraser l'archive précédente."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from .roni import SOURCE_URL
from .storage import store_snapshot

MAX_BYTES = 256_000


def fetch_roni() -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": "avantemps-research/0.1 (+https://github.com/SillageLabs/avantemps)", "Accept": "text/plain"})
    with urlopen(request, timeout=25) as response:
        origin = urlparse(response.geturl())
        if origin.scheme != "https" or origin.hostname != "www.cpc.ncep.noaa.gov":
            raise ValueError("Redirection NOAA inattendue")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Fichier NOAA trop volumineux")
    return payload.decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Importer le RONI officiel NOAA")
    parser.add_argument("--data-dir", type=Path, default=Path("var/data"))
    args = parser.parse_args()
    try:
        snapshot = store_snapshot(args.data_dir, fetch_roni())
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(f"Échec de l'ingestion (archive conservée) : {exc}", file=sys.stderr)
        return 1
    last = snapshot["summary"]["latest"]
    print(f"Archive {snapshot['id'][:12]} | {last['season']} {last['year']}: {last['anomaly_c']:+.2f} °C (RONI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
