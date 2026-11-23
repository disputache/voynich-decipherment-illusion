#!/usr/bin/env python3
"""Download the three datasets this experiment uses from their original home, pinned and checksum-verified.

Source: Daniel E. Gaskell & Claire L. Bowern, https://github.com/danielgaskell/voynich (commit d076a7d).
The gibberish transcriptions are © 2022 Gaskell & Bowern under their modified MIT licence; the Voynichese and
meaningful-text datasets carry their own terms (see that repository's documentation). We do not redistribute any of
them here: this script fetches them from the source.
"""
import hashlib, sys, urllib.request, zipfile
from pathlib import Path

COMMIT = "d076a7d081f35098fa405928239595afd2e75927"
BASE = f"https://raw.githubusercontent.com/danielgaskell/voynich/{COMMIT}/data/"
FILES = {
    "voynichese.zip": "07992a9d51ab0b2d8c10554770e0b9405cdcfa952ca4e9542868c146c7a4c5bc",
    "gibberish_transcriptions.zip": "a4bfa58af956603ab6607227ad640e01cb695c7b492c6914488bd30f6d0aebbe",
    "meaningful.zip": "684edcf2a4e6abe08ce85b147c38d0e0dc5d48bd4d56cf81276c1251444342bd",
}
DATA = Path(__file__).resolve().parent / "data"


def main() -> int:
    DATA.mkdir(exist_ok=True)
    for name, sha in FILES.items():
        dst = DATA / name
        if not dst.exists():
            print(f"downloading {name} …")
            with urllib.request.urlopen(BASE + name, timeout=120) as r:
                dst.write_bytes(r.read())
        got = hashlib.sha256(dst.read_bytes()).hexdigest()
        if got != sha:
            print(f"checksum mismatch for {name}: {got}", file=sys.stderr)
            return 1
        print(f"ok  {name}")
    with zipfile.ZipFile(DATA / "voynichese.zip") as z:
        z.extractall(DATA / "voynichese")
    with zipfile.ZipFile(DATA / "gibberish_transcriptions.zip") as z:
        z.extractall(DATA / "gibberish")
    print("data ready (meaningful.zip is read in place)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
