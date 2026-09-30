#!/usr/bin/env python3
"""Locate and extract the real 7z archive embedded in an MPC Sample updater EXE.

The Akai updater is a 7-Zip SFX. There are multiple byte sequences that look
like a 7z signature inside the Windows stub, so this script validates the 7z
StartHeader CRC rather than taking the first match.

If 7z/7zz/7za is installed it will also extract the archive. Otherwise it
writes payload.7z, which can be opened manually with 7-Zip.
"""
from __future__ import annotations

import argparse
import binascii
import shutil
import struct
import subprocess
from pathlib import Path

SIG = b"7z\xbc\xaf\x27\x1c"


def valid_7z_offsets(data: bytes):
    pos = 0
    while True:
        off = data.find(SIG, pos)
        if off < 0:
            return
        pos = off + 1
        if off + 32 > len(data):
            continue
        hdr = data[off : off + 32]
        major, minor = hdr[6], hdr[7]
        start_crc = struct.unpack_from("<I", hdr, 8)[0]
        calc_crc = binascii.crc32(hdr[12:32]) & 0xFFFFFFFF
        next_off = struct.unpack_from("<Q", hdr, 12)[0]
        next_size = struct.unpack_from("<Q", hdr, 20)[0]
        end = off + 32 + next_off + next_size
        if major == 0 and start_crc == calc_crc and end <= len(data):
            yield off, major, minor, next_off, next_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("updater", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("work/updater"))
    args = ap.parse_args()

    data = args.updater.read_bytes()
    hits = list(valid_7z_offsets(data))
    if not hits:
        raise SystemExit("No valid embedded 7z archive found")
    if len(hits) > 1:
        print(f"Found {len(hits)} valid 7z headers; using the last one")
    off, major, minor, next_off, next_size = hits[-1]

    args.out.mkdir(parents=True, exist_ok=True)
    archive = args.out / "payload.7z"
    archive.write_bytes(data[off:])
    print(f"7z archive offset: 0x{off:X} ({off})")
    print(f"7z version: {major}.{minor}")
    print(f"archive bytes: {archive.stat().st_size}")
    print(f"wrote: {archive}")

    exe = next((shutil.which(x) for x in ("7zz", "7z", "7za") if shutil.which(x)), None)
    if exe:
        extracted = args.out / "files"
        extracted.mkdir(exist_ok=True)
        subprocess.run([exe, "x", "-y", f"-o{extracted}", str(archive)], check=True)
        print(f"extracted: {extracted}")
    else:
        print("No 7z/7zz/7za found. Open payload.7z manually with 7-Zip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
