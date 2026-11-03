# Commercial property stage one

This implementation is based on playtest source `22ac393ffc1484c351a607480802f7a4ac6c12d7`. The staged source contains the server changes, matching Lua material lifecycle, open font assets and reproducible review tools. It is a source implementation, not a newly compiled application or an in-game visual acceptance run.

## Buildings and geometry

The first stage covers small grocery stores, supermarkets, shopping parades, trade units, clinics and hospitals. Building height, roof, footprint, holes and accepted entrances remain source-constrained. New facade work includes fitted sign bands, entrance surrounds/covers, shopfront framing, service-bay trim, clinic privacy bands and hospital floor/shading details. NZ/Australian, British/Irish, Japanese urban and tropical contemporary palettes supply regional authoring priors. These are procedural interpretations, not claims about a surveyed building's exact architecture.

Reusable assets include the two-post property directory, named facade panels, trolley shelter with nested carts, bench, bike stand, bollard, service cabinet and planter. Furniture is **visual-only in this first stage** and is batched into an existing building visual product, rather than creating a scene object per prop. Building and shared-court collision remains the established accepted product. Reusable furniture templates and closed facade prisms are cached; building prisms use the existing batched component transform.

Both freestanding and facade signs derive their background, frame and accent from the regional palette and the building's resolved facade tint/material. Text uses a contrasting light or dark colour. Directory panels vary within that coherent palette. Generic older shop-sign bands use the same palette policy. Tenant names do not determine invented brand colours or logos.

## Detail and cost ceilings

The existing Advanced Building detail setting governs generation work, not just visibility:

| Detail | Named facade panels/tile | Directory pages/tile | Furniture/tile | Fascia/directory width | Trolley shelter triangles |
|---|---:|---:|---:|---|---:|
| Minimum / Very Low | 0 | 0 | 0 | No text baking | 0 |
| Low | 0 | 0 | 0 | Two-triangle unlettered sign bands | 0 |
| Medium | 8 | 4 | 6 | 256 / 256 px | 180, shelter only |
| High | 16 | 6 | 12 | 512 / 512 px | 780, two carts |
| Very High | 24 | 8 | 18 | 512 / 512 px | 1,080, three carts |
| Ultra | 32 | 8 | 24 | 1,024 / 512 px | 1,680, five carts |

Whole directories are admitted atomically: a low budget never silently drops the last page of tenants. The compiler directly rasterizes at the requested texture width. There is no per-frame font selection, text layout, rasterization or network access. Font, text, mesh-template and identity caches are bounded. Named assets participate in initial output, progressive visibility groups, visual refinement, normal revisit caching, session relocation and material retirement. The client caps resident sign materials at 2,048. If a material fails to load or that limit is reached, it omits the optional named visual chunk while retaining base buildings and physics.

Local synthetic measurements, excluding network and engine import/rendering:

- Warm indexed identity resolution: approximately 20 ms for 500 buildings with real coordinate conversion in the identity microbenchmark.
- Identity + inference + programme: 139 ms median for 500 synthetic buildings, three batches.
- Incremental property facade geometry for 500 synthetic buildings: 74 ms Low, 187 ms Medium, 233 ms High and 282 ms Ultra. This excludes the existing full building compiler.
- Cached facade-panel preparation in the same 500-building microbenchmark: approximately 1–3 ms for the admitted 8–32 panels. Initial font inventory initialization and new text baking cost more; the first measured Medium batch took 143 ms. Later detail measurements can reuse earlier text/font cache entries and are not independent cold-start comparisons.
- A separate cold test preparing 500 distinct directories took approximately 5 seconds after font lookup optimization. Directory preparation is bounded to the tile ceilings above.

These numbers are local worker measurements, not game FPS or a cold download guarantee. Run `tools/benchmark_commercial_stage_one.py` and `tools/benchmark_property_detail.py` to reproduce the synthetic scopes.

## Identity and sizing

Optional Overture Places are read only from existing memory/disk cell caches and indexed once per cell. A batched spatial query and coordinate conversion resolve candidate occupants for hundreds of footprints. Missing optional Places do not trigger network downloads or block ordinary geometry. Watched cache inputs include missing files so later enrichment can invalidate an accepted plan during normal regeneration.

An independently mapped building class/subtype establishes the host use. Contained POIs preserve names/provenance and remain containment associations; they do not automatically become verified tenants, ownership evidence or the host building class. A hospital's gift shop does not replace the hospital identity. Direct mapped host names may label the facade; unknown names are not fabricated.

Food retail uses a project authoring threshold of **400 m²** between a small grocery and a supermarket, with a large modifier from **2,500 m²**. This is not a universal legal/retail definition. The current runtime accepts a single-storey exclusive grocery building footprint as a labelled area proxy. Unknown floor count, mixed occupants or building parts leave retail size unresolved and retain generic commercial architecture. A whole mixed-use host footprint is not assigned to one grocer.

Source research and broader family plans are in the workspace's `building_generation_research/property_identity_20261103/PLAN.md`. Primary sources include [Overture Places schema](https://docs.overturemaps.org/schema/reference/places/place/), [Overture Places guide](https://docs.overturemaps.org/guides/places/), [Geofabrik OSM extracts](https://download.geofabrik.de/) and [AllThePlaces data format](https://github.com/alltheplaces/alltheplaces/blob/master/DATA_FORMAT.md). This stage does not add a live public geocoder, commercial Places API or per-building query.

## Shared properties and directories

The runtime uses the existing `BNE_SHARED_SITE_RECORDS` SiteGraph and adds an optional `BNE_PROPERTY_IDENTITIES` version-1 JSON catalogue. Enable the normal Advanced (`v2`) building generator. The site catalogue and identity catalogue are pinned inputs; restart after changing them.

Example identity record (fictional values; `site_id` and `member` must match real declared SiteGraph identities):

```json
{
  "version": 1,
  "sites": [{
    "site_id": "survey:example-lot",
    "address": {"number": "6", "street": "Main Road"},
    "property_name": "Example Court",
    "style": "metal",
    "display": {"position": [8.0, 8.0], "heading_degrees": 0},
    "tenants": [{
      "identity": "provider:business-1",
      "member": "overture:building-1",
      "name": "Example Bakery",
      "unit": "UNIT 1",
      "association": "supported",
      "typography_role": "artisan"
    }],
    "furniture": [{
      "kind": "trolley_shelter",
      "position": [8.0, 14.0],
      "heading_degrees": 0
    }]
  }]
}
```

Positions are metres in the site's declared canonical ENU frame; zero heading presents the front toward local -Y. The placement fitter rejects source holes, member-building conflicts, exclusions, pedestrian/vehicle/service routes, parking stalls, overlap, steep ground and placements that span sector ownership. A directory without an explicit position can use a validated shared-layout landscape bed. Furniture positions are explicit site authoring data in this stage; no unverified yard or trolley bay is inferred from a nearby shop POI. Generated landscape planting can still require an in-game visual review alongside optional furniture.

Only declared building/lot members with supported/verified occupant associations enter a directory. Natural unit ordering, deduplication, permanent-closure filtering and bounded text inputs apply. Real address number and street are required. Up to 32 occupants are split into boards of eight, with page numbering and explicit omission diagnostics. A mapped address or tenancy feed still needs an adapter to populate this explicit catalogue; point containment alone does not populate it as verified ownership.

## Typography and reproducibility

The offline bundle contains **214 open-source font files**, including regular families from all 176 Noto Sans script directories in the pinned source, Tibetan, four regional CJK variants, Noto styles, Amiri and four display families. All 214 source URLs were downloaded and matched against the bundled SHA-256 manifest. Redistribution notices accompany the fonts.

Default business roles are Libre Franklin 600 for grocers, Oswald 600 for supermarkets, Barlow Condensed for trade units, Lora 500 for artisan/parade signage and Noto Sans for clinical/address text. Script coverage takes precedence over the Latin display style. Explicit tenant roles allow controlled variation. Japanese, Korean, Simplified Chinese and Traditional Chinese fonts can be selected by locale; Japanese building context selects Japanese facade lettering. Unspecified Han text defaults to Simplified Chinese forms.

Pillow/HarfBuzz and the included, replaceable LGPL FriBidi DLL provide offline shaping and bidirectional text on Windows. The app packager explicitly includes that DLL. Other platforms require a shaping-enabled Pillow build. The bundle is broad rather than a claim of literally every language/character: the current whole-line fallback cannot cover every mixed-script combination or emoji, and vertical Mongolian is diagnosed and omitted. Font updates require process restart and a regenerated font manifest. See `server/buildgen/fonts/README.md`, `manifest.json` and the notices for exact sources and licensing.

Review tools: `tools/preview_commercial_stage_one.py` renders the actual generated meshes and sign bitmaps; `tools/preview_property_fonts.py` renders representative international samples. The previews use approximate material lighting and fictional fixture names. Native BeamNG material/texture acceptance, on-road readability and collision behaviour of future physical furniture remain follow-up playtest work.
