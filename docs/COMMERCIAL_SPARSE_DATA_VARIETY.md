# Commercial and industrial variety without detailed tags

Schema 24 adds eight executable compositions for broad commercial/industrial use:
glazed pavilion, concentrated display hall, pier frontage, ribbon block, service
hall, clerestory hall, glazed workhall and industrial window grid. Factory and
manufacturing labels also use the industrial compositions. Detailed warehouse,
workshop, supermarket, retail, office and hotel tags retain their dedicated paths.

Selection uses occupied footprint area, a rotation-independent aspect ratio,
shape compactness, courtyard presence, resolved storeys and wall height. Observed
neighbours within 75 metres provide size and density weights. Specific effective
zone environments can adjust those weights, but no zone is required. Stable
source identity chooses among compatible alternatives. Appearance is recorded as
an inferred visual prior, while source class, resolved occupancy, dimensions,
materials, roof and outline remain authoritative. Shape alone never turns an
unclassified building into an industrial or commercial one: existing observed
land use or a supported neighbour consensus can supply that broad use.

The actual road-facing elevation is fitted after entrance resolution. Service
halls have multiple service bays and a staff-window zone; clerestory halls have
high glazing and fewer shutters; workhalls have lower grouped windows; industrial
grids can have no shutters. Commercial forms differ in glazing extent, pier and
bay spacing, opaque ends, and horizontal or vertical grouping. Courtyards retain
their voids; unsupported courtyard apertures stay blank. Source party walls,
terrain, obstructions and primary access reservations constrain optional openings.
The forms do not invent businesses, traversable interiors, truck yards or extra
access routes.

Near and middle representations consume the same accepted layout. Optional work
is capped at 64 openings per elevation and 256 per building, excluding the one
primary entry. Giant outlines keep plausible module sizes and residual blank
wall instead of stretched doors. Source fingerprints include the new solver and
catalogue, and the schema bump invalidates previously generated building plans.

Validation: `test_buildgen_commercial_forms.py` covers no-zone population diversity,
untagged buildings with land-use/neighbour evidence, contextual population changes,
specific-tag preservation, narrow/collinear/L-shaped/courtyard fit, steep or missing
terrain, hidden service openings, translation, serialization, near/middle geometry,
collision and work caps. `tools/commercial_variety_preview.py` renders naturally
selected examples and reports 128 seeds per broad use. These are offline synthetic
checks; native game appearance and performance acceptance remain pending.
