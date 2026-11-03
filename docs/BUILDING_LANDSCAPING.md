# Shared frontage landscaping — schema 12

The 1 November 2026 continuation adds more concrete, usable path shoulders,
grass, garden beds and restrained low planting to residential and commercial
frontages. It uses the existing building identity and resolved entrance geometry,
not a garden template. The commercial docks, parking and service-access work and
the residential roof-colour, zoning and driveway changes remain integrated.

## Treatment selection

`buildgen/landscaping.py` defines nine small construction/landscape treatments.
These are authored visual conventions, not claims about surveyed gardens or
country-specific horticulture. Proposed international style packs are not
silently activated. Current facade material, resolved use, settlement environment
and the existing climate response select a compatible treatment:

| Identity | Treatment |
| --- | --- |
| Temperate homes | Concrete paths with somewhat wider grass/garden margins |
| Masonry homes | Warm neutral paving, planted borders and lawn |
| Urban frontages | More concrete, compact planting, less soft margin |
| Rural homes | Grass/gravel margins and modest concrete access |
| Warm-climate forms | Light warm paving and low planted beds |
| Cold-climate forms | Neutral concrete, gravel and restrained planting |
| Restrained modern forms | Cool concrete, gravel and small planted borders |
| Retail | Wider public entry paths, neutral concrete and compact beds/lawn |
| Industrial / trade | Narrow practical concrete or gravel margins; no ornamental shrubs |

Independent semantic seeds vary the two side widths, surface choices, plant
positions and plant heights. Variation stays tied to identity and available
space rather than using independent noise on every paving panel. Geometry is
fitted to each entrance and section. Some sites legitimately receive paving
without planting, or no optional treatment if clearance/grade is inadequate.

## Geometry and integration

Frontage paths are 1.2–1.6 m wide where the entry landing can support them.
Concrete shoulders share the exact adjacent path edge levels and crossfall.
They become ordinary access solids, present in collision and visual LODs.
Natural margins follow sampled terrain and are decorative surfaces over the
existing terrain physics. Grass, soil and gravel use existing game terrain
texture assets; they are not green-tinted concrete. Low plants use small opaque
meshes with no wind simulation, alpha sorting, scene objects or collision.

Gardens and pavement avoid neighbouring buildings, roads, garage aprons and
other resolved access. Authoritative property boundaries/exclusions are obeyed
when supplied. Without parcel evidence, the scope is the narrow entrance
frontage corridor already supported by the previous path generator, up to
12 m long and at most 0.85 m of margin on each side. It does not infer full
gardens, lawns across entire parcels, perimeter walls or ownership of road verges.

When a driveway creates a replacement walking connection, old concrete
shoulders are removed. Retained natural beds are trimmed to the new entrance
link and checked against driveway/link geometry, preventing long decorative
strips from following a removed path. Missing or unsuitable terrain suppresses
optional treatment instead of creating earthworks.

For supplied commercial property data, up to four short residual groundcover
strips can fit alongside pedestrian/parking walks. Their positions derive from
the accepted walking geometry and remaining property area; they cannot occupy
loading courts, parking spaces, service routes or exclusions. Industrial sites
receive at most one short gravel strip. A strip is emitted only if its parent
walking/parking component succeeds. The property terrain budget remains shared
with docks and parking, with decoration taking the lowest priority.

The existing path switch, `--building-paths off`, disables inferred frontage
paths and their margins. Supplied property-site layouts remain a separate,
explicitly enabled feature under `--building-sites`; see
[commercial site inputs](COMMERCIAL_SITES_STAGE2.md).

## Cost and checks

Frontage margins reuse the existing five-across terrain sampling pattern; they
do not add a terrain request or a wider sampling search. Adding industrial
entrance paths can add up to 105 points to their existing access batch.
Subdivision follows terrain; flat patches merge before export.

Per building, the new detail budgets are:

* At most twelve decorative frontage patches and twelve concrete shoulders.
* At most four additional property-site groundcover patches, within the existing
  512-point / 24-patch property planner budget; one for industry.
* At most eight plants, eighteen triangles each (144 triangles total), near LOD
  only. Industrial treatment emits none. Groundcover remains visible in lite LOD.

The 90-case synthetic entrance/driveway/landscape benchmark measured about
3.9 ms median and 4.8 ms p95, with at most 181 terrain samples across the relevant
batches. This includes existing access and commercial-facade checks, excludes
building planning/mesh generation/DEM fetches, and is not an in-game FPS claim.
The separate 90-case property planner, including residual groundcover, measured
8.3 ms median / 11.7 ms p95 and at most 375 samples.

273 focused tests pass across 19 suites. The seven new landscaping tests cover
identity treatment, deterministic variety, clearances, bounded geometry and
terrain work, driveway integration, repeated site generation, disabled paths,
missing terrain and material registration. Existing access tests still compare
every physical surface between visual and collision meshes; additional
decorative surfaces are explicitly excluded from physics.

Reproduce the synthetic visual review with:

```powershell
python tools/landscape_preview.py --out build/landscaping.png
python tools/site_preview.py --out build/landscaped-sites.png
```

The previews approximate textures and lighting. Actual BeamNG texture loading,
appearance, driving and streaming still require playtesting. This change does
not assert measured species, engineered drainage or local regulatory compliance.

Current combined private package: `BeamNG.Earth-v2-landscaping-20261101.zip`.
Prepared residential runtime data is preserved byte-for-byte from the preceding
commercial-site package. The default launcher enables frontage landscaping;
property-wide site work still requires real property/access evidence.
