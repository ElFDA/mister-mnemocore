#!/usr/bin/env python3
"""
generate_db.py

Regenerates db.json (MiSTer Downloader custom database format) with
fresh MD5 hashes/sizes for the current content of the tracked files.
Run this locally before every push that changes any of them; db.json
must always reflect exactly what's on disk, or the Downloader will
either skip a real update or flag a mismatch.

Not meant to run on the MiSTer itself -- this is a maintainer tool.
"""
import hashlib
import json
import time

RAW_BASE = "https://raw.githubusercontent.com/ElFDA/mnemocore/master"

# destination path on the SD card -> source file in this repo
FILES = {
    "Scripts/mnemocore.sh": "mnemocore.sh",
    "MnemoCore/mnemocore_helper.py": "mnemocore_helper.py",
    "MnemoCore/antipanic.sh": "antipanic.sh",
    "MnemoCore/uninstall.sh": "uninstall.sh",
}


def md5_and_size(path):
    h = hashlib.md5()
    size = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def main():
    files = {}
    for dest, src in FILES.items():
        digest, size = md5_and_size(src)
        files[dest] = {
            "hash": digest,
            "size": size,
            "url": f"{RAW_BASE}/{src}",
        }

    db = {
        "v": 1,
        "db_id": "mnemocore",
        "timestamp": int(time.time()),
        "files": files,
        "folders": {
            "MnemoCore/": {},
        },
    }

    with open("db.json", "w") as f:
        json.dump(db, f, indent=4)
        f.write("\n")

    print("wrote db.json")


if __name__ == "__main__":
    main()
