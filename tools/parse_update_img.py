#!/usr/bin/env python3
"""Parse and split the AZ0x update.img format used by MPC Sample 1.3.0.

This parser currently targets the v1 container observed in MPC Sample 1.3.0.
It validates every stored SHA-256 and can decompress XZ partition payloads.
It does not create signed firmware: the outer header is RSA-signed by Akai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import struct
from pathlib import Path

MAGIC = b"AZ0x"
STRING_BASE_V1 = 0x38
RECORD_SIZE = 0x40


def u16(d: bytes, off: int) -> int:
    return struct.unpack_from("<H", d, off)[0]


def u32(d: bytes, off: int) -> int:
    return struct.unpack_from("<I", d, off)[0]


def u64(d: bytes, off: int) -> int:
    return struct.unpack_from("<Q", d, off)[0]


def cstr(d: bytes, off: int) -> str:
    end = d.find(b"\0", off)
    if end < 0:
        raise ValueError(f"unterminated string at 0x{off:x}")
    return d[off:end].decode("utf-8", errors="replace")


def name_from_offset(d: bytes, string_off: int) -> str:
    if string_off == 0:
        return ""
    return cstr(d, STRING_BASE_V1 + string_off)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("work/update"))
    ap.add_argument("--no-decompress", action="store_true")
    args = ap.parse_args()

    d = args.image.read_bytes()
    if d[:4] != MAGIC:
        raise SystemExit(f"bad magic: {d[:4]!r}")

    version = u32(d, 4)
    if version != 1:
        raise SystemExit(f"unsupported AZ0x version {version}")

    model_table_off = u32(d, 0x14)
    record_table_off = u32(d, 0x18)
    signature_table_off = u32(d, 0x1C)
    string_table_size = u32(d, 0x20)
    model_count = u16(d, 0x24)
    record_count = u16(d, 0x26)
    signature_count = u32(d, 0x28)
    signed_region_size = u32(d, 0x2C)
    description_off = u32(d, 0x34)

    info = {
        "format": "AZ0x",
        "version": version,
        "file_size": len(d),
        "description": name_from_offset(d, description_off),
        "model_table_offset": model_table_off,
        "record_table_offset": record_table_off,
        "signature_table_offset": signature_table_off,
        "string_table_size": string_table_size,
        "model_count": model_count,
        "record_count": record_count,
        "signature_count": signature_count,
        "signed_region_size": signed_region_size,
        "records": [],
    }

    args.out.mkdir(parents=True, exist_ok=True)

    for i in range(record_count):
        roff = record_table_off + i * RECORD_SIZE
        magic = d[roff : roff + 4].decode("ascii", errors="replace")
        rec_version = u32(d, roff + 4)
        payload_off = u64(d, roff + 8)
        payload_size = u64(d, roff + 16)
        name_off = u64(d, roff + 24)
        stored_hash = d[roff + 32 : roff + 64]
        payload = d[payload_off : payload_off + payload_size]
        calc_hash = hashlib.sha256(payload).digest()
        name = name_from_offset(d, name_off)
        label = name or "bootloader"

        if payload_off + payload_size > len(d):
            raise SystemExit(f"record {i} extends past EOF")
        ok = stored_hash == calc_hash
        suffix = ".fit" if payload.startswith(b"\xd0\x0d\xfe\xed") else ".xz" if payload.startswith(b"\xfd7zXZ\x00") else ".bin"
        raw_path = args.out / f"{label}{suffix}"
        raw_path.write_bytes(payload)

        rec = {
            "index": i,
            "record_magic": magic,
            "record_version": rec_version,
            "name": name,
            "offset": payload_off,
            "size": payload_size,
            "sha256": stored_hash.hex(),
            "sha256_ok": ok,
            "raw_file": raw_path.name,
        }
        info["records"].append(rec)

        print(f"{i}: {magic} {label:10s} off=0x{payload_off:x} size={payload_size} sha256={'OK' if ok else 'FAIL'}")
        if not ok:
            raise SystemExit(f"SHA-256 mismatch for {label}")

        if suffix == ".xz" and not args.no_decompress:
            out_path = args.out / f"{label}.img"
            out_path.write_bytes(lzma.decompress(payload))
            print(f"   decompressed -> {out_path} ({out_path.stat().st_size} bytes)")

    if signature_count:
        key_name_off = u64(d, signature_table_off)
        key_name = name_from_offset(d, key_name_off)
        sig = d[signature_table_off + 8 : signature_table_off + 8 + 256]
        info["signature"] = {
            "key_name": key_name,
            "key_name_offset": key_name_off,
            "algorithm": "sha256,rsa2048 (PKCS#1 v1.5 verified for 1.3.0)",
            "signed_range": [0, signed_region_size],
            "signature_offset": signature_table_off + 8,
            "signature_size": len(sig),
            "signature_sha256": hashlib.sha256(sig).hexdigest(),
        }
        (args.out / "header.signed.bin").write_bytes(d[:signed_region_size])
        (args.out / "header.signature.bin").write_bytes(sig)
        print(f"signature key: {key_name}")
        print(f"signed range: [0x0, 0x{signed_region_size:x})")

    meta = args.out / "manifest.json"
    meta.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
