# MPC-Sample-RE

Reverse-engineering notes and tooling for the **Akai MPC Sample** firmware.

Initial target: official **MPC Sample 1.3.0 Updater**.

## Current status

- [x] Extract Windows updater SFX
- [x] Locate and parse `update.img`
- [x] Split bootloader / recovery / boot / rootfs payloads
- [x] Verify all payload SHA-256 values
- [x] Decompress Linux filesystems
- [x] Identify RK3566 / AZ07 / AC50 platform
- [x] Extract and verify the `akai-1` RSA-2048 update signature
- [x] Identify the main AArch64 MPC Sample application
- [x] Confirm substantial JUCE/VST/MPC Plugin Program code is compiled into it
- [ ] Map AC50 plugin feature gates / control flow
- [ ] Determine a safe development-key or verification-bypass path
- [ ] Map USB update protocol and raw partition-write protections
- [ ] Build a reproducible modified-image workflow

## Tools

### `tools/extract_updater.py`

Finds the **real** embedded 7z archive in the Windows SFX by validating the 7z StartHeader CRC. This matters because the EXE contains earlier false-positive 7z signature byte sequences.

```bash
python tools/extract_updater.py "MPC Sample 1.3.0 Updater.exe"
```

If 7-Zip is installed, it extracts automatically. Otherwise it writes `payload.7z`.

### `tools/parse_update_img.py`

Splits the AZ0x `update.img`, verifies each payload hash, and decompresses XZ partitions:

```bash
python tools/parse_update_img.py work/updater/files/update.img
```

The resulting ext filesystem images can be opened with 7-Zip on Windows or normal Linux ext filesystem tools.

### `tools/scan_mpc_binary.py`

Scans an extracted `/usr/bin/MPC Sample` for a conservative set of plugin/VST host indicators.

```bash
python tools/scan_mpc_binary.py "rootfs/usr/bin/MPC Sample"
```

## Important signing note

The firmware is not merely checksummed. The payload hashes live in an RSA-signed AZ0x header. In 1.3.0 the signature verifies over `update.img[0:0x190]` with the shipped `akai-1` public key.

So editing rootfs + updating its SHA is easy; **making stock verification accept that edited header is the current blocker**.

See [`docs/firmware-1.3.0.md`](docs/firmware-1.3.0.md) for the current map and [`docs/plugin-host.md`](docs/plugin-host.md) for the plugin investigation.

## Repository policy

This repo intentionally does **not** include Akai/inMusic firmware binaries, extracted proprietary executables, samples, or private signing keys. The tooling operates on firmware obtained by the device owner.
