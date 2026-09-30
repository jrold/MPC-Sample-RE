# Plugin-host investigation

The 1.3.0 `/usr/bin/MPC Sample` executable contains a surprisingly complete set of MPC/JUCE VST-host artifacts.

The strongest indicators are the normal JUCE/Linux VST discovery path, `VSTPluginMain`, plugin scanning/error strings, `EngineVst` methods, `VstPlugin` methods, Plugin Program UI strings, and named MPC synth engines.

See `../evidence/plugin-host-strings.txt` for a conservative list extracted directly from the binary.

## What is proven

- The executable is AArch64 and dynamically linked.
- JUCE 5.4.4 is compiled into the application.
- VST2 hosting/scanning code is compiled into the application.
- MPC Plugin Program concepts and several named synth engines are compiled into the application.

## What is not proven yet

- That AC50 can instantiate these paths without patching feature/product gates.
- That the actual standalone MPC plugin binaries are present in the rootfs (they are not obvious as separate `.so`/VST files in the stock image).
- That binaries from ARMv7 MPC One/Live firmware can be reused directly. MPC Sample is AArch64; architecture compatibility must be checked per plugin build.

The next RE step is to find cross-references to the Plugin Program / VST UI strings and identify product-code checks (`AC50`, AZ07 feature tables, expansion/plugin entitlement gates) around those call sites.
