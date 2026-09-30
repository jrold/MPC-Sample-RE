# MPC Sample firmware 1.3.0 notes

Source analyzed: `MPC Sample 1.3.0 Updater.exe`.

## Updater wrapper

- Updater SHA-256: `417dc79c1baa9e35ed173757c15dc8e7249224775ee9389739814f657fea8b73`
- Windows updater is a 7-Zip SFX.
- The actual valid 7z archive begins at file offset `0x34445` (`214085`).
- Archive contents:

| File | Size |
|---|---:|
| `Background.png` | 8,243 |
| `Config.json` | 845 |
| `update.img` | 169,207,872 |
| `FirmwareUpdater.exe` | 3,341,392 |
| `libusb-1.0.dll` | 756,224 |

`Config.json` identifies the package as **MPC Sample 1.3.0 Update** and says update mode is entered by powering on while holding **CHOP + MUTE + SAMPLE SELECT**.

## `update.img`

- SHA-256: `5c49811b80b75c246b203896a581aecdcd6dd813db6f28f9d1f2183ba85d8c99`
- Format magic: `AZ0x`
- Format version: `1`
- Description: `MPC Sample image`
- Product/model string: `AC50`
- Snapshot string: `SNAPSHOT-20260402131256`

### Payload table

All hashes below were independently recalculated and match the image header.

| Record | Name | Offset | Compressed size | SHA-256 |
|---|---|---:|---:|---|
| `BOOT` | bootloader | `0x00000298` | 1,754,600 | `d3b42e33ad0c1b5fdce12374448dcaf275ca1e4550f59045827a7b18377ed0ca` |
| `PARR` | recovery | `0x001ac880` | 12,431,000 | `588690178c8eb990d53e2263c1ac28c60bc3aa7e2be914cc64a3b6cf09b8efbd` |
| `PART` | boot | `0x00d87718` | 12,644,540 | `d2409e515acf9bc1f21fd9594b4d44eb9a954b6eea73476654e2588bfc478532` |
| `PART` | rootfs | `0x019967d8` | 142,377,060 | `3455f58e10d2e69665954f6cda9d7eab6dc18a4ed18d4ce4b6ca3aac1aa21731` |

The recovery, boot, and rootfs payloads are XZ-compressed. Decompressed sizes/filesystems:

- recovery: ~27 MiB ext filesystem, contains `kernel.fit`
- boot: ~28 MiB ext filesystem, contains `kernel.fit`
- rootfs: ~408 MiB ext4 filesystem

The bootloader payload is a FIT/DTB container and identifies:

- `rockchip,rk3566`
- `inmusic,az07`
- `inmusic,ac50`
- U-Boot `2025.10-inmusic-20251120`

The partition map embedded in the bootloader includes redundant SPL/U-Boot slots plus `factory`, `boot`, `recovery`, `rootfs`, `content` and `data`.

## Image signing

This is the main obstacle to a simple "modify rootfs, repack, flash" workflow.

The outer AZ0x header contains the SHA-256 of every payload and is itself signed.

For 1.3.0:

- signed bytes: `update.img[0x000:0x190]`
- key-name descriptor: `0x190:0x198`, string offset points to `akai-1`
- RSA signature: `0x198:0x298` (256 bytes)
- algorithm: SHA-256 + RSA-2048, PKCS#1 v1.5
- public key in the shipped rootfs: `/usr/lib/az0x/pubkeys/akai-1.pub`

The signature was verified successfully with OpenSSL against exactly the first `0x190` bytes. Any change to a payload requires changing its stored SHA-256 in that signed header, which invalidates the Akai signature.

The rootfs ships inMusic's `libaz01-prog.so.1.3`, which exports functions including `az01_verify_image`, `az01_verify_signature`, `az01_load_public_key_file`, `az01_load_private_key`, `az01_sign_*`, and image/partition write APIs. Its strings identify `/usr/lib/az0x/pubkeys` and `/usr/lib/az01/pubkeys` as key directories.

The Windows `FirmwareUpdater.exe` also imports Windows cryptographic verification APIs (`BCryptVerifySignature`) and contains the same `no valid signature found` / `sha256,rsa2048` strings, so signature handling is present on the host side as well.

## Root filesystem / application

The rootfs reports the inMusic **AZ0x** base distribution `5.0.14` and contains AArch64 kernel modules for `6.12.60-imb-2025-12-03-rt13`.

Main application:

- path: `/usr/bin/MPC Sample`
- size: `119,243,440` bytes
- ELF64, AArch64, PIE, stripped
- build ID: `1dac7f481a0fe8d128e435ace88d7e6aece0c9c9`
- JUCE string: `JUCE v5.4.4`

Startup path:

`ac50.service` -> `/usr/bin/launch-ac50` -> `/usr/bin/az0x-firmware-tool` for the AC50 peripheral firmware -> `/usr/bin/MPC Sample`.

## Plugin-host code present in the MPC Sample executable

The application binary contains concrete VST/plugin-host strings, not just generic audio framework names. Verified examples include:

- `VST_PATH`
- `/usr/lib/vst;/usr/local/lib/vst;~/.vst`
- `VSTPluginMain`
- `Attempting to load VST:`
- `Initialising VST:`
- `Creating VST instance:`
- `Plugin Scanning`
- `Plugin Scan`
- `Plugin scan result`
- `Plugin scan failed`
- `VST Folders`
- `Plugin Program`
- `EngineVst::loadDefaultProgram`
- `EngineVst::loadProgram`
- `EngineVst::editorOpen`
- `VstPlugin::beforeDelete`
- `ExpansionManager.showVST`
- `ExpansionManager.showVST3`
- `MPC:Bassline`
- `MPC:TubeSynth`
- `VintageBassline`
- `FMSynth`
- `GranularSynth`

This establishes that substantial MPC plugin-host machinery was compiled into the MPC Sample application. It does **not yet prove** that the stock AC50 UI exposes a reachable path to instantiate those plugins; that requires control-flow/gating analysis next.

## Current practical conclusion

Unpacking is solved. Repacking the binary layout and recalculating payload hashes is also straightforward. **Flashing a modified image is not yet solved** because the stock trust chain requires an Akai-signed header.

The next useful RE targets are:

1. Find exactly where plugin/program availability is gated for product `AC50`.
2. Trace `az01_verify_image` callers and key-provider logic to identify the least invasive way to introduce a development key or bypass verification on user-owned hardware.
3. Inspect the USB update protocol to determine whether raw partition-writing commands are independently authenticated or only protected by the signed image workflow.
4. Determine whether a supported service/debug path can provide shell access before modifying any flash contents.
