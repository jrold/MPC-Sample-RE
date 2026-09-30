#!/usr/bin/env python3
"""Build a harmless unsigned MPC Sample (AC50) V2 test-app probe package.

The generated archive targets the stock /usr/bin/test-app-launcher found in
MPC Sample 1.3.0. It does NOT modify firmware or flash partitions. The shell
payload records basic system information to /data/mpc-sample-re-probe.txt and
then requests the normal AC50 application service to start again.

Use only on hardware you own/control. Expect the normal MPC UI to stop while
the test application is running; a power cycle remains the fallback recovery.
"""
from __future__ import annotations

import argparse
import textwrap
import zipfile
from pathlib import Path

PRODUCT = "AC50"
OS_VERSION_ID = "scarthgap"
APP_DIR = "test-apps/ac50"
APP_NAME = "AC50TestApp"

MANIFEST = f"""\
testApps:
  - version: 0.1.0
    osVersionID: {OS_VERSION_ID}
    products:
      - {PRODUCT}
    signedImage: False
    basePath: {APP_DIR}
    relativeExePath: {APP_NAME}
    launcher-XXXXXX: MPCSampleRE
    name: MPC Sample RE Probe
"""

SCRIPT = textwrap.dedent(r'''#!/bin/sh
    # MPC-Sample-RE harmless discovery probe.
    # No flash writes, package installation, account changes, or SSH changes.

    OUT=/data/mpc-sample-re-probe.txt
    TMP="${OUT}.tmp"

    {
        echo "MPC-Sample-RE probe"
        echo "==================="
        date 2>&1 || true
        echo
        echo "--- uname ---"
        uname -a 2>&1 || true
        echo
        echo "--- os-release ---"
        cat /etc/os-release 2>&1 || cat /usr/lib/os-release 2>&1 || true
        echo
        echo "--- cpuinfo ---"
        cat /proc/cpuinfo 2>&1 || true
        echo
        echo "--- meminfo ---"
        cat /proc/meminfo 2>&1 || true
        echo
        echo "--- cmdline ---"
        cat /proc/cmdline 2>&1 || true
        echo
        echo "--- mounts ---"
        cat /proc/mounts 2>&1 || true
        echo
        echo "--- processes ---"
        ps 2>&1 || true
        echo
        echo "--- network ---"
        ip addr 2>&1 || ifconfig -a 2>&1 || true
        echo
        echo "--- listening sockets ---"
        ss -lntup 2>&1 || netstat -lntup 2>&1 || true
        echo
        echo "--- selected services ---"
        systemctl --no-pager --full status ac50.service az0x-webserver.service az01-script-runner.service 2>&1 || true
        echo
        echo "PROBE_COMPLETE=1"
    } > "$TMP" 2>&1

    mv "$TMP" "$OUT"
    sync 2>/dev/null || true

    # Stock az0x-webserver is configured to stop ac50 before launching a test app.
    # Delay the restart to avoid racing the test-app launcher's display/audio teardown.
    ( sleep 2; systemctl start ac50.service >/dev/null 2>&1 || true ) &
    exit 0
''')


def add_text(zf: zipfile.ZipFile, arcname: str, text: str, executable: bool = False) -> None:
    info = zipfile.ZipInfo(arcname)
    info.create_system = 3
    mode = 0o755 if executable else 0o644
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, text.encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", type=Path, default=Path("mpc-sample-re-probe.zip"))
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w") as zf:
        add_text(zf, "manifest.yaml", MANIFEST)
        add_text(zf, f"{APP_DIR}/{APP_NAME}", SCRIPT, executable=True)

    print(f"wrote: {args.output}")
    print(f"product: {PRODUCT}")
    print(f"osVersionID: {OS_VERSION_ID}")
    print("signedImage: False")
    print("payload: read-only discovery probe; report -> /data/mpc-sample-re-probe.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
