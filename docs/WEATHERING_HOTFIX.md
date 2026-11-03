# Weathering texture compatibility hotfix — 2 November 2026

Build: `BeamNG.Earth-v2-consolidated-r2-20261102`.

The first consolidated playtest started and connected successfully, but its
weathering detail map used a DX10 RGBA8 DDS header that BeamNG 0.40.4's ordinary
shape-material texture reader rejects. The game log repeatedly reports
`fourcc['DX10'] unsuported format`, followed by failures to load
`bne_weathering.dds`. Offline startup and geometry tests did not exercise that
native texture-loading path.

This hotfix changes that texture to the legacy RGB DDS header and RGBA masks
already used by the mod's ground-detail texture. All nine mip levels and every
pixel are unchanged. Palettes, weathering strength, building geometry, lamps,
curbs, driveways, collision and streaming logic are retained exactly.

The regression test now checks the shipped texture against the generator,
compares its pixel-format descriptor with the existing ground-detail asset,
decodes its top level independently, and verifies every mip and file length.
Six focused weathering tests pass. The parent build's broader tests are inherited,
not reported as rerun; the package manifest verifies the single runtime-asset
change. See `validation/weathering-hotfix.json` and `validation/tests.json`.

The supplied session also showed road/building import queues growing to 729,
1% lows of 6–8 FPS and several road-update stalls over one second. Repeated
texture failures are a confirmed regression and likely contribute, but this
patch does not establish how much of the frame-time problem they explain.
Shadow/reflection spikes and queued native imports still need profiling after
the texture loads successfully. The invalid-footprint warnings are source-data
rejections, separate from this texture failure; they are not a Python crash.

Close the existing Earth server and restart BeamNG, then run the parent
`Play latest buildings.bat`. It selects this corrected package and installs its
matching mod through the normal launcher. A full restart avoids retaining a
failed texture/material resource in the current game session.

Native texture reload, visual acceptance and post-fix FPS measurements remain
pending. The running game was not hot-patched or moved during this investigation.
