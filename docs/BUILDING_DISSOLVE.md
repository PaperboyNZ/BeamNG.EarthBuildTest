# Building revision dissolve — 2 November 2026

Generated building revisions previously waited for complete imports, then hid
and deleted the old objects in one frame. Selecting the static render path only
affected embedded LODs; it did not blend independently generated versions.

The client now dissolves complete visual sets over 0.4 seconds. An ordered 8×8
screen-space mask assigns each pixel to either the old or new version. Both
versions retain their exact transforms and normal materials. The same mask runs
in depth, color (including depth-equal), and shadow visibility passes. Applying
it in the color pass is necessary because two revisions can have identical depth.
Collision meshes do not participate.

Visibility requests are coalesced after coverage reconciliation. Incoming
objects register hidden, and subsequent revisions wait for the current dissolve
wave to finish. Retired objects stay resident, with their pooled shape slots
held, until their coverage reaches zero. Import limits remain unchanged. Rebase
and teardown settle transitions before detaching/moving objects.

The shader uses the documented TSStatic instance palette channel
`instanceColor2`, with a reserved byte marker (blue 173, alpha 91). Normal objects
do not match this marker. Building materials do not use this palette channel.
No translucent-material conversion or unsupported TSStatic opacity field is used.
See the [TSStatic instance data reference](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/).

At install/launch, `building_fade_shader.py` reads the installed game's two shader
visibility functions and inserts the small mod-owned include into **mod-local
copies**. Engine files are never edited and engine shader source is not included
in the distribution. The current function signatures and instance-data accessor
are checked first; unsupported layouts remove the generated hooks and print an
explicit diagnostic. Steam libraries are detected on Windows/Linux;
`BNGE_GAME_DIR` can specify another install. Restart BeamNG after installing this
build so it loads the shader overrides. The generated ready marker gates the
Lua transition path. This check establishes source compatibility, not GPU success.

Verification: deterministic Lua tests cover progressive and cached revisions,
far/near coverage, interrupted transitions, repeated visibility reconciliation,
rebase, deletion/pooled-slot lifetime, unchanged collision, and long-frame clamps.
Python checks cover every quantized mask threshold and idempotent shader
installation/failure cleanup. The HLSL include compiles with D3DCompile in opaque,
depth-equal, translucent, depth-only and instanced harness variants. The installed
game's shader sources were used to verify hook generation. These are offline
checks; native BeamNG appearance, Vulkan compilation, shadows and FPS still need
an in-game check and are not claimed as verified.
