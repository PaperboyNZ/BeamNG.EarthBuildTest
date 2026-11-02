# Site generation identity and geographic frame contract

Implemented in `server/sitegen/identity.py`. This is an additive M1 foundation;
it does not change legacy catalogue validation, dispatch, geometry, engine tile
ownership or the existing building plan schema. It establishes descriptor identity
and coordinates before persistent site caches or cross-tile resource scheduling.

## Identity and revisions

`SourceIdentity(namespace, feature_id)` is the immutable provider identity. The
namespace identifies the dataset/authority and identifier domain, for example
`overture:buildings`, `osm:way` or a locally registered survey namespace. Provider
IDs are opaque text: their case and Unicode code points remain significant. Do not
use a display name, row index, requested tile, tile-local XY, projected vertex array
or current release as a provider ID. Existing `seed_id`, `src_dataset`, `src_record`
and legacy `site_id` are adapter inputs, not interchangeable identity domains.
An adapter must declare its domain and the meaning of the chosen source key.

`SourceRevision(identity, revision)` pins one version of that source. Its
`dependency_key` includes both identity and revision. The revision must change when
the consumed source content changes; an immutable release identifier or content
checksum is suitable. A mutable URL, timestamp of retrieval or the literal word
`latest` is insufficient. Unknown release/content provenance cannot establish a
reusable persistent dependency. No geometry-only fallback identity is invented.

`semantic_id(kind, source, role="")` creates a versioned SHA-256 name from a
structured JSON tuple of semantic kind, source identity and stable role. Different
source namespaces and explicit roles remain distinct. A semantic ID deliberately
excludes source revision, frame origin, member order, tile ownership and residency.
For example, revision changes may invalidate a parking-deck resource's result while
preserving the semantic identity of that deck. Roles must themselves be stable
source-linked names; enumerating the order members happen to arrive is unsuitable.

Source changes, canonical frame descriptor, planner/profile/schema/code versions,
and all consumed evidence revisions are separate cache dependencies. A source
revision key alone is not a complete generated-result cache key. A frame key alone
is neither a source identity nor a source-content checksum. A change in an upstream
source ID requires an explicit lineage policy outside this module.

## Canonical frame selection

`CanonicalFrame.from_geographic_extent(points)` accepts the **complete** source
extent as `(longitude_degrees, latitude_degrees)` pairs. For a multi-member site,
collect all authoritative source members before selecting the frame. A partial
tile clip or a partially loaded member set cannot establish the canonical frame.
Association extent and occupied surface remain separate concepts in site records.

The version 1 selection policy is:

1. Validate finite numeric geographic inputs. Boolean values are invalid. Accept
   latitude from -90 through +90 degrees and longitude from -540 through +540
   degrees. Normalize longitude to `[-180, 180)`, so +180 and -180 are equivalent.
2. Quantize the extent samples to integer `1e-7` degrees with decimal round-to-even.
   Interpret validated numeric values through Python's shortest decimal string
   (`Decimal(str(value))`) at fixed local decimal precision 40. Use
   longitude zero for an exact/quantized polar sample. Duplicate samples have no
   influence. Quantize original longitude before integer wrap; do not multiply or
   wrap binary floats first. This makes `2.5e-7` and `360.00000025` select the same
   half-step anchor without a data-dependent epsilon. Values already rounded to
   different decimal source numbers remain different inputs.
   Geometry is **not** quantized by this operation.
3. Sort unique longitudes around the circle. Remove the largest circular gap to
   obtain the shortest containing arc. Equal largest gaps choose the lowest
   canonical starting longitude. Choose the round-to-even midpoint of that arc
   and of the latitude extrema. Normalize the anchor longitude again.
4. Reject quantized longitude or latitude spans above one degree and inputs over
   8,192 samples. Empty extents fail. Antipodal/global extents are unsupported.
   Split oversized associations into separately framed bounded source sectors;
   do not truncate source members to satisfy this limit.
5. Use a tangent ENU frame at the selected anchor and **zero WGS84 ellipsoidal
   height**. A canonical anchor at either pole uses longitude zero, fixing its
   east/north orientation deterministically.

The frozen descriptor stores `longitude_e7` and `latitude_e7` integers. Its JSON
also declares `source-extent-enu-v1`, horizontal datum `WGS84`, vertical datum
`WGS84_ellipsoid`, coordinate units `metres`, anchor precision `0.0000001` degrees,
and height zero. Unrecognized/missing fields or conventions are rejected. The
anchor quantization is about 11 mm in latitude; it does not reduce vertex or ENU
geometry precision. Geometry remains float64 through the scalar conversion path.

Ring start rotation, winding, repeated closing vertices, hole/member iteration
order, equivalent longitude wrapping and requested tile/rebase do not enter frame
selection. A genuine change in the complete geographic extent may change its frame
and must invalidate frame-dependent results while preserving semantic IDs.

This procedure selects an anchor only. It does not validate polygons, holes,
antimeridian edge interpretations, source completeness, membership, occupancy or
free space. Mixed polar extents can fail the angular-span limit despite a short
ground distance; this conservative case needs an explicit future framing policy.
The frame contract does not assert a horizontal epoch or perform tectonic datum
transformations. Input heights must already be WGS84 ellipsoidal heights; unknown,
orthometric/MSL or local heights require an explicit conversion outside this API.

## Original projections, units and rebasing

`GeographicFrame(longitude, latitude, height=0)` describes an original ENU origin,
including exact unquantized legacy origin coordinates and nonzero ellipsoidal
height. It is frozen and declares the same datums and units with type
`wgs84-enu-v1`. It preserves an explicitly supplied polar longitude because that
longitude defines the original frame's east/north orientation. It makes no claim
that the origin follows the source-extent canonical selection policy.

Both descriptors expose scalar `geodetic_to_enu(longitude, latitude, height)` and
`enu_to_geodetic(east, north, up)` returning triples. **This longitude-first API
differs from existing `geodesy.EnuFrame`'s latitude-first API.** Legacy adapters
must swap geographic axis order when calling the existing implementation. WGS84
ellipsoid constants agree with `server/geodesy.py`; no Rust/native import is needed
to construct or serialize descriptors. `CanonicalFrame.as_geographic_frame()`
returns the corresponding explicit origin descriptor.

`rebase_enu(point, source_frame, target_frame)` transforms a three-axis point via
WGS84 ECEF/geodetic coordinates. Retain all three axes: dropping the source up
component and treating height as an ENU offset loses the ellipsoid curvature and
altitude information needed for a correct rebase. Source projection context must
also preserve any separate tile XY subtraction (`x0`, `y0`); add those offsets back
before this conversion. A legacy footprint that discarded vertical components
needs an explicit planar-height assumption and cannot recover its original 3D
source geometry from XY alone.

Inputs and origins accept ellipsoidal height from -12,000 to 100,000 metres; inverse
ENU inputs accept each axis within ±1,000,000 metres. Results outside the supported
geographic-height range fail. These are finite local-site conversion bounds, not
a general orbit/planetary geodesy API. Tests compare scalar forward conversions
against existing geodesy and exercise altitude-preserving rebase round trips.

## Geographic boundary ownership

`CanonicalFrame.owner_cell(cell_size_e7=100_000)` gives a deterministic geographic
**descriptor admission key**, based on the canonical source anchor. The default
grid is 0.01 degrees, anchored at (-180, -90). Cells include west/south edges and
exclude east/north edges. +180 normalizes to -180; +90 belongs to the last latitude
row. A custom integer cell size must divide 180 degrees exactly and is included in
the versioned owner key. This remains independent of projected/rebased engine
tiles. It does not assign producer rights or imply that occupancy is limited to
one cell; resource producer/consumer ownership belongs to the site plan contract.

## Serialization and validation

Every identity/frame offers fresh `to_dict()` output and strict `from_dict()`
construction. `canonical_json()` uses sorted keys, compact separators, ASCII JSON
escapes and rejects NaN/Infinity. Content keys hash those bytes with SHA-256. Text
is nonempty, unpadded and free of ASCII control characters, with UTF-8 bounds of
128 bytes for source namespace, 512 for feature ID/revision/role and 64 for kind.
Serialized nested dictionaries never alias frozen descriptor state.

This module does no file I/O and does not deserialize pickle. Future persistent
cache storage must use bounded JSON envelopes with schema/dependency checks,
checksums, atomic replacement and quota/lifetime controls; those M2 mechanisms are
not implemented here. Trusted detached worker transport and persistent cache
loading are separate boundaries. Do not treat an arbitrary Python object or a
legacy pickle as a disk descriptor.

## Reproduction and limits

```powershell
New-Item -ItemType Directory -Force build/sitegen-identity/tmp | Out-Null
$env:TEMP = (Resolve-Path build/sitegen-identity/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_sitegen_identity --par 1 --timeout 120 --logs build/sitegen-identity/tests
```

The focused suite covers source revision versus semantic identity; namespace/role
separation; immutable detached JSON; ring/winding/member order; dateline/wrap
equivalence; unchanged geometry precision; altitude-preserving frame rebases;
existing geodesy parity; poles and half-open geographic boundaries; malformed,
nonfinite, oversized and unsupported geographic inputs. It does not establish
game geometry, cache integration, source completeness or scheduler correctness.
