#!/usr/bin/env python3
"""Extract selected plugin-host evidence from the MPC Sample application binary."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = [
    r"JUCE v[0-9.]+",
    r"VST_PATH",
    r"/usr/lib/vst[^\x00]*",
    r"Attempting to load VST:[^\x00]*",
    r"VSTPluginMain",
    r"Initialising VST:[^\x00]*",
    r"Plugin Scanning",
    r"Error Scanning VST",
    r"Creating VST instance:[^\x00]*",
    r"Plugin Program",
    r"Plugin Scan",
    r"Plugin scan result",
    r"Plugin scan failed",
    r"VST Folders",
    r"ExpansionManager\.showVST3?",
    r"EngineVst::[A-Za-z0-9_~]+",
    r"VstPlugin::[A-Za-z0-9_~]+",
    r"MPC:Bassline",
    r"MPC:TubeSynth",
    r"VintageBassline",
    r"FMSynth",
    r"GranularSynth",
    r"TubeSynth",
    r"Bassline",
]


def ascii_strings(data: bytes, min_len: int = 4):
    pat = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    for m in pat.finditer(data):
        yield m.start(), m.group().decode("ascii", errors="ignore")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("binary", type=Path)
    args = ap.parse_args()
    regs = [re.compile(p, re.I) for p in PATTERNS]
    seen = set()
    for off, s in ascii_strings(args.binary.read_bytes(), 4):
        if any(r.search(s) for r in regs):
            if s not in seen:
                print(f"0x{off:08x}\t{s}")
                seen.add(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
