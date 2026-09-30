# Development access / test-app path

## Short version

MPC Sample 1.3.0 appears to contain a **non-flashing development/factory execution path** that is much more useful for reverse engineering than fighting the RSA-signed update image.

The stock image contains:

- `/usr/bin/test-app-launcher`
- `/usr/bin/az0x-webserver`
- an enabled `az0x-webserver.service`
- AC50 webserver config with web auth explicitly disabled
- a `/testapp` multipart-upload endpoint in the webserver
- an unsigned V2 test-app package parser in `test-app-launcher`

This is still marked **experimental on MPC Sample hardware** until a package is actually launched on a physical unit.

## MPC Sample-specific facts

From 1.3.0:

- product code: `AC50`
- AZ0x OS: `5.0.14`
- `VERSION_CODENAME=scarthgap`
- USB gadget creates an NCM network interface
- MPC address: `192.168.155.1/28`
- DHCP server enabled
- web auth: `auth-disable: true`
- web document root: `/var/www/ac50`
- webserver test-app config stops service `ac50`
- default upload location in the binary: `/tmp`
- default launch command in the binary:
  `test-app-launcher --testapp-path="{testapp-path}"`

Akai's public update instructions document the normal web UI at
`http://mpc-sample.local/` or `http://192.168.155.1/`.

The webserver binary also contains an HTML test-app form whose POST target is:

`/testapp`

and a multipart input named `file`.

## Unsigned V2 test package format

The MPC Sample's `test-app-launcher` contains the same V2 schema used by
other current inMusic AZ0x devices:

- root archive entry exactly named `manifest.yaml`
- `testApps`
- `version`
- `osVersionID`
- `products`
- `signedImage`
- `basePath`
- `relativeExePath`
- `launcher-XXXXXX`
- `name`

The launcher binary contains both:

- `az01-signed-fs "{}"`
- `GetUnsignedRelExePath called for unsupported object`

so signed and unsigned package paths are both compiled into this build.

For AZ0x 5.x, the launcher reads `VERSION_CODENAME`; therefore the matching
MPC Sample value is `scarthgap`.

A matching experimental manifest is:

```yaml
testApps:
  - version: 0.1.0
    osVersionID: scarthgap
    products:
      - AC50
    signedImage: False
    basePath: test-apps/ac50
    relativeExePath: AC50TestApp
    launcher-XXXXXX: MPCSampleRE
    name: MPC Sample RE Probe
```

## Build the harmless probe

```bash
python tools/make_probe_testapp.py
```

This creates `mpc-sample-re-probe.zip`.

The included shell payload only gathers diagnostics into:

`/data/mpc-sample-re-probe.txt`

It does **not** write boot/rootfs/recovery partitions, install packages,
change SSH configuration, or replace Akai binaries. It schedules the normal
`ac50.service` to start again after the probe exits.

## First hardware test

1. Boot MPC Sample normally and connect its USB-C data port to the computer.
2. Confirm the normal Akai web updater loads at `http://192.168.155.1/`
   (or `http://mpc-sample.local/`).
3. Open `http://192.168.155.1/testapp`.
4. If the stock test-app upload form appears, select the generated
   `mpc-sample-re-probe.zip` and submit it.
5. Expect the normal MPC application to stop while the test package is
   launched because Akai's config explicitly lists `ac50` under
   `services-to-stop`.
6. The probe asks systemd to restore `ac50.service` after it exits.
   If the UI does not return, power-cycle the unit normally.

Do **not** use the firmware `/software-update` endpoint for this ZIP. That
endpoint expects a signed AZ0x firmware image and verifies the Akai signature.

## Why this matters for plugin work

If the unsigned test-app path works on physical AC50 hardware, we can iterate
without modifying flash:

1. inspect live `/data` settings and MPC state;
2. test whether `ExpansionManager.showVST` / `showVST3` can be changed
   through ordinary application settings;
3. enumerate dynamically loaded libraries and plugin search paths;
4. run small AArch64 probes alongside the stock system;
5. only after that decide whether a persistent firmware modification is even
   necessary.

That is a much safer development loop than trying to bypass the signed updater
first.

## Related external research

Dylan Corrales documented the same `test-app-launcher` V2 package structure
on inMusic Engine OS / AZ0x hardware in August 2026. On those tested devices,
`signedImage: False` accepts a shell-script executable without the signed
`az01-signed-fs` path. MPC Sample independently contains the same launcher
schema and code paths, but physical AC50 execution still needs to be confirmed.
