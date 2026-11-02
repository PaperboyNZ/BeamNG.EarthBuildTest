# Construction details and frontage grading

The subsequent schema-9 update adds street-resolved garage drives, dropped kerb
crossings and optional landing links. Read [driveway geometry and limits](BUILDING_DRIVEWAYS.md)
alongside the earlier detail work below.

Local v2 checkpoint, 1 November 2026. These are engineering-informed rendering
rules for reconstructed buildings, not construction documents or a declaration
of building-code compliance. Missing parcel boundaries, underground drainage,
soil/permeability data and surveyed levels remain unknown.

## References and what they inform

- [MBIE: About E2/AS1](https://www.building.govt.nz/building-code-compliance/e-moisture/e2-external-moisture/an-introduction-to-acceptable-solution-e2as1)
  describes the coordinated envelope detailing of flashings, gutters, barges,
  fascia and soffits. The renderer follows that assembly logic: fascia closes
  the roof edge, corner boards close lightweight cladding junctions, and roof
  drainage has channels, outlets, offsets and downpipes. Geometry alone cannot
  establish weathertightness or correct fastening/lap details.
- [NZTA: Paths, April 2026](https://www.nzta.govt.nz/assets/Walking-Cycling-and-Public-Transport/docs/pedestrian-network-guidance/docs/3.3-paths-apr-2026.pdf)
  identifies 2% as the NZS 4121 maximum footpath crossfall. This implementation
  uses a 1.5% modeling target and develops it gradually beyond a landing. That
  one slope constraint does not establish an accessible route. The 1.2 m private
  frontage-path width is an authored default, not a public-footpath recommendation.
- [Worcestershire County Council: Access, layout and connectivity](https://www.worcestershire.gov.uk/council-services/travel-and-highways/highways-licences/streetscape-design-guide/4-access-layout-and-connectivity)
  gives 1:20 as a desirable maximum longitudinal gradient for adopted footpaths.
  We use 5% as a conservative automatic-generation cutoff. Steeper real paths
  exist; this cutoff means that their grading requires a more capable solver.
- [Christchurch City Council: Civil Engineering Construction Standard, Part 6](https://ccc.govt.nz/assets/Documents/Consents-and-Licences/construction-requirements/CSS/Download-the-CSS-2020/CSS-PART-6-ROADING-2019.pdf)
  includes chamfered concrete edges, jointing and checks against ponding. This
  informs the rendered paving edge restraints and deliberate joint layout.
  The older document supplies construction-detail principles here, not a claim
  about the city's current requirements or structural adequacy of these meshes.
- [Concrete NZ: Guide to Concrete Construction, Chapter 14](https://concretenz.org.nz/resource/resmgr/docs/ccanz/ccanz_tm35.pdf)
  explains contraction/control joints and notes that appropriate spacing varies
  with the application. Paths receive transverse seams approximately every
  1.2 m; wide aprons receive a longitudinal seam and an isolation seam next to
  the building. These are surface representations, not designed reinforcement,
  saw-cut depths or expansion-joint specifications.

The PDF search extracts were available, but direct retrieval of the NZTA PDF
returned 403 in this session. No inaccessible clause text or dimensions have
been guessed. The numerical defaults below are labeled as modeling choices.

## Implemented details

`buildgen/details.py` adds closed, mitered corner boards for timber/metal
cladding. It avoids applying white trim to every brick corner. Both legs share
the corner vertex; short, acute and concave corners retain their existing shell.
Window sill thickness and end caps from the preceding checkpoint remain.

Complex pitched outlines now receive flush fascia without expanding their
footprint into a courtyard. Rectangles retain their existing soffit/overhang
assembly. Ridge/hip caps and valley flashing derive from adjacent analytical
roof planes; coplanar triangulation edges do not become decorative seams.
Sheet ends are inset and tested against the occupied footprint. Caps never
raise a mapped roof top. Arbitrary cross-gable reconstruction remains unfinished.

Gutter generation merges collinear triangulation splits into physical eave runs.
Gable rakes do not receive gutters. Adjacent runs use mitered channel corners,
and shallow positive falls lead to selected outlets. Closed polygonal downpipes
have offsets beneath the eave, wall brackets and receiver collars at local ground.
The pipe attachment avoids facade openings. Where no suitable outer-wall
attachment is found, the gutter run is omitted. Courtyard drainage remains
incomplete. Approximate 112 mm channels and 80 mm pipes are visual recipe sizes;
catchment area, rainfall intensity, overflow capacity and buried connections
have not been designed or simulated.

Fine details render only nearby. They do not add collision for trim, gutters,
pipes or sheet-metal caps. Pitched primary roof/collision surfaces remain shared.

## Paths, paving and yard margins

`buildgen/sitework.py` proposes a straight path from the resolved entry to the
source-road frontage. The destination stops outside the road corridor. Routes
must be between 1.2 and 12 m and nearly normal to the entrance wall. This bounded
solver does not claim to recover an actual driveway, legal boundary or site plan.

Path and narrow gravel-margin samples join the existing access terrain batch.
The path starts at the threshold surface or the final stair riser. The following
checks apply before committing the whole route:

- At most 5% longitudinal grade on either edge and a 1.5% target crossfall,
  with a transition from the level entrance landing.
- No buried paving and at most 150 mm modeled fill above sampled terrain.
- No occupied-building or buffered road-corridor intersection.
- No overlap with the same building's garage apron.
- No route when samples are missing, the landing is absent, the stair connection
  is unsuitable, or the first path segment would drain back toward a threshold.

Thresholds have a small 2% outward fall while preserving the door datum. Flat
garage aprons now fall outward where terrain clearance permits. Existing adverse
garage grades are retained with an unresolved-drainage diagnostic; no fictional
stormwater connection is inserted. Stairs with at least three treads receive
simple visual handrails; these do not establish compliant guarding or accessibility.

Accepted path slabs join without height cracks. Broad walking surfaces appear in
near/lite/collision and occupancy bounds. Beveled edge restraints, fine joint
seams, handrails and 240 mm gravel margins are nearby visual details. Gravel
follows sampled ground and is omitted where it intersects known obstructions.
It is not an infiltration or soakaway claim. The system does not invent a lawn
parcel, retaining wall, property fence or underground drain from an empty space.
Dense terrain sampling is separate from mesh segmentation: intermediate stations
are removed only when both paved edges and every sampled ground track remain
collinear within a micrometre. Joint spacing is measured along the route and
does not depend on the retained mesh vertices.

## Limits and validation

Path checks currently know building footprints and supplied road corridors,
not every water feature, utility, tree root, parcel restriction or neighboring
generated path. Offset/curved routes, long setbacks, switchbacks, complete yard
grading, retaining structures and surveyed drainage destinations require further
site evidence and engineering rules. Existing stair dimensions also remain
simulation recipes; no automatic accessibility label is assigned.

Schema 7 retains the new immutable landscape surfaces with the access plan.
Tests check road/building/apron clearance, grading rejection, terrain batching,
anchor consistency, connected walking surfaces, collision/LOD agreement,
roof-cap footprint/top bounds and nondegenerate construction-detail meshes.
Synthetic previews use approximate colors; game texture, lighting and driving
acceptance remain outstanding.
