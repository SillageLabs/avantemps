"""Ingestion HTTPS NOAA et validation locale sans écriture, séparées."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .roni import SOURCE_URL, parse_roni, validate_noaa_history
from .storage import store_snapshot

MAX_BYTES = 256_000


def fetch_roni() -> str:
    request = Request(SOURCE_URL, headers={
        "User-Agent": "avantemps-research/0.2 (+https://github.com/SillageLabs/avantemps)",
        "Accept": "text/plain",
    })
    with urlopen(request, timeout=25) as response:
        origin = urlparse(response.geturl())
        if origin.scheme != "https" or origin.hostname != "www.cpc.ncep.noaa.gov":
            raise ValueError("Redirection hors de la NOAA refusée")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Fichier NOAA trop volumineux")
    return payload.decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="AVANTEMPS : ingestion officielle NOAA")
    parser.add_argument("--data-dir", type=Path, default=Path("var/data"))
    parser.add_argument("--check-file", type=Path, metavar="RONI.txt",
                        help="Valide un fichier local SANS l'importer ni l'attribuer à la NOAA")
    args = parser.parse_args()
    try:
        if args.check_file is not None:
            text = args.check_file.read_text(encoding="ascii")
            records = parse_roni(text)
            validate_noaa_history(records)
            last = records[-1]
            print(f"Format RONI validé, sans import : {len(records)} saisons, "
                  f"dernière {last.season} {last.year}: {last.anomaly_c:+.2f} °C")
            return 0
        snapshot = store_snapshot(args.data_dir, fetch_roni())
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Échec de l'ingestion/validation (archive inchangée) : {exc}", file=sys.stderr)
        return 1
    last = snapshot["summary"]["latest"]
    print(f"Archive {snapshot['id'][:12]} | "
          f"{last['season']} {last['year']}: {last['anomaly_c']:+.2f} °C (RONI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
