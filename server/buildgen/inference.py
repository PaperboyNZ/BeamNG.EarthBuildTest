"""Conservative, auditable building-use and architectural inference.

Scores express rule support, not calibrated probabilities. Explicit mapped use
constrains the result; geometry alone cannot establish a building's use. Climate
only changes a weak roof prior and never supplies a country or cultural label.
"""
from collections import Counter
from dataclasses import dataclass, replace
import math
from statistics import median

from .context import Context, ContextManifest, LOCAL_M
from .evidence import normalise_attributes
from . import materials
from . import presets, zones
from . import environments
from . import house_styles


USE_CLASSES = {
    "residential": "house detached semidetached_house bungalow residential apartments terrace dormitory "
                   "static_caravan cabin town_house",
    "commercial": "commercial retail supermarket grocery_store convenience convenience_store strip_shops shopping_parade kiosk office hotel restaurant shop mall cafe motel hostel",
    "industrial": "industrial warehouse manufacture manufacturing factory hangar workshop trade_units freight_terminal cargo_terminal freight_station",
    "agricultural": "agricultural farm barn farm_auxiliary stable cowshed greenhouse",
    "civic": "civic public school university college kindergarten hospital clinic government fire_station "
             "ambulance_station community_centre townhall sports_hall",
    "religious": "religious church chapel cathedral mosque temple synagogue shrine",
    "transport": "transportation train_station transportation_station terminal parking_garage airport_terminal airport_concourse passenger_terminal concourse bus_station ferry_terminal",
    "ancillary": "shed garage garages carport roof hut service storage_tank toilets parking shelter silo grain_silo "
                 "transformer_tower substation",
    "mixed": "mixed_use mixed",
}
CLASS_USE = {cls: use for use, classes in USE_CLASSES.items() for cls in classes.split()}
LAND_USE = dict(CLASS_USE, farmland="agricultural", farmyard="agricultural", agriculture="agricultural",
                education="civic", medical="civic", institutional="civic")
MATERIALS = {
    "brick": "brick bricks", "stone": "stone sandstone limestone granite marble masonry tuff slate",
    "wood": "wood timber log wood_boards", "concrete": "concrete cement precast",
    "render": "plaster stucco render", "metal": "metal steel iron corrugated_iron aluminium aluminum",
    "glass": "glass",
}
ROOF_MATERIALS = {
    "thatch": "thatch thatched straw reed palm_leaves",
    "metal": "metal tin steel zinc corrugated_iron sheet aluminium aluminum",
    "copper": "copper", "tile": "tile tiles roof_tiles clay terracotta",
    "slate": "slate stone", "shingle": "shingle shingles wood",
    "membrane": "concrete cement tar_paper bitumen asphalt felt gravel", "glass": "glass",
}
FACADE_ALIASES = {v: k for k, values in MATERIALS.items() for v in values.split()}
ROOF_ALIASES = {v: k for k, values in ROOF_MATERIALS.items() for v in values.split()}
SUPPORTED_ROOFS = {"flat", "gabled", "hipped"}


@dataclass(frozen=True, slots=True)
class Decision:
    value: str | float | int | tuple
    status: str                 # observed, inferred, fallback, unknown, conflict
    source: str
    strength: str               # high, moderate, low, unknown; not a probability
    support: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Candidate:
    use: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Resolution:
    use: Decision
    architecture: Decision
    facade: Decision
    roof: Decision
    roof_material: Decision
    height: Decision            # total thickness including roof, excluding min_height
    floors: Decision
    body_height: float
    roof_rise: float
    pitch: float
    candidates: tuple[Candidate, ...]
    context: ContextManifest
    diagnostics: tuple[str, ...]
    morphology: Decision
    selection: presets.Selection
    roof_colour: Decision = Decision((), "fallback", "material_palette", "low")
    roof_variant: str = 'standard'
    house_style: house_styles.HouseStyle = house_styles.HouseStyle()
    dwelling_structure: str = ''
    modifiers: tuple[str, ...] = ()


def observed(ev, field):
    o = ev.get(field)
    return o.value if o is not None and o.status == "observed" else None


def _text(value):
    return str(value).strip().lower().replace("-", "_") if value is not None else ""


def mapped_uses(ev):
    return frozenset(CLASS_USE[v] for field in ("class", "subtype")
                     if (v := _text(observed(ev, field))) in CLASS_USE)


def use_decision(ev, context, area):
    mapped = mapped_uses(ev)
    scores = {use: 0. for use in USE_CLASSES}
    reasons = {use: [] for use in USE_CLASSES}

    def add(use, score, reason):
        scores[use] += score
        reasons[use].append(reason)

    # Multiple mapped land-use classes can overlap; retain their disagreement.
    for cls, overlap in context.land_use:
        use = LAND_USE.get(cls)
        if use and overlap >= .6:
            add(use, 3. * overlap, f"land_use:{cls}:{overlap:.3f}")
    for use, score, why in zones.support(context.zones):
        # Existing land-use data may share the overlay's lineage. Never count
        # the same broad zone support twice, even across different providers.
        scores[use] = max(scores[use], score)
        reasons[use].extend(why)
    counts, weight = Counter(), Counter()
    for n in context.neighbours:
        uses = mapped_uses(n.evidence)
        if len(uses) == 1:
            use = next(iter(uses))
            counts[use] += 1
            weight[use] += 1. if n.distance_m <= LOCAL_M else .35
    total = sum(weight.values())
    for use in sorted(weight):
        if counts[use] >= 3 and weight[use] >= .6 * total:
            add(use, 1.8 * weight[use] / total, f"observed_neighbours:{counts[use]}")
    # Weak shape evidence can support an existing candidate, never create a type.
    if 40 <= area <= 300:
        add("residential", .25, "small_footprint")
    if area > 1200:
        add("industrial", .25, "large_footprint")
        add("commercial", .25, "large_footprint")
    candidates = tuple(Candidate(use, round(score, 6), tuple(reasons[use]))
                       for use, score in sorted(scores.items(), key=lambda x: (-x[1], x[0])))
    if len(mapped) == 1:
        return Decision(next(iter(mapped)), "observed", "mapped_use", "high"), candidates
    if len(mapped) > 1:
        return Decision("unknown", "conflict", "mapped_use", "unknown", tuple(sorted(mapped))), candidates
    top, runner = candidates[:2]
    if top.score >= 1.5 and top.score - runner.score >= .75:
        return Decision(top.use, "inferred", "neighbourhood", "moderate", top.reasons), candidates
    return Decision("unknown", "unknown", "insufficient_or_conflicting_evidence", "unknown"), candidates


def _comparable(context, area, use):
    return tuple(n for n in context.neighbours if .4 * area <= n.area_m2 <= 2.5 * area
                 and (use == "unknown" or mapped_uses(n.evidence) == {use}))


def _choice(ev, field, neighbours, aliases, default):
    value = observed(ev, field)
    if value is not None and _text(value) in aliases:
        return Decision(aliases[_text(value)], "observed", f"mapped:{field}", "high")
    groups = {}
    for n in neighbours:
        v = aliases.get(_text(observed(n.evidence, field)))
        if v is not None:
            groups.setdefault(v, []).append(n.source_id)
    ranked = sorted(groups, key=lambda v: (-len(groups[v]), v))
    if ranked and len(groups[ranked[0]]) >= 3 and len(groups[ranked[0]]) >= .65 * sum(map(len, groups.values())):
        v = ranked[0]
        return Decision(v, "inferred", f"observed_neighbours:{field}", "moderate", tuple(sorted(groups[v])))
    return Decision(default, "fallback", "conservative_prior", "low")


def _morphology(ev, context, area, half_width, use):
    h, nf = observed(ev, "height"), observed(ev, "num_floors")
    if (h is not None and h > 12.) or (nf is not None and nf > 3):
        return Decision("multi_storey_block", "inferred", "mapped_dimensions", "moderate")
    cls = _text(observed(ev, "class"))
    nearby = tuple(n for n in context.neighbours if n.distance_m <= LOCAL_M)
    coverage = sum(n.area_m2 for n in nearby) / (math.pi * LOCAL_M**2)
    sparse = len(nearby) >= 3 and coverage < .24
    detached = cls in ("house", "detached", "bungalow", "semidetached_house") or \
        (sparse and use in ("residential", "unknown"))
    if detached and 65. <= area <= 450. and half_width >= 3.5:
        return Decision("detached_lowrise", "inferred", "mapped_class_or_observed_spacing", "moderate" if sparse else "low")
    return Decision("generic_lowrise", "fallback", "footprint_envelope", "low")


def resolve(attrs, footprint, half_width, context=None, can_pitch=True):
    """Resolve renderable dimensions/recipes, retaining source facts separately.

    The caller supplies the *thickness* of elevated parts in attrs.height;
    attrs._evidence still contains their original absolute top/minimum heights.
    """
    context = context or Context()
    half_width = float(half_width)
    ev = normalise_attributes(attrs)
    area = footprint.area
    use, candidates = use_decision(ev, context, area)
    environment = environments.resolve(context, use.value)
    if attrs.get("_part") and use.status == "observed":
        use = Decision(use.value, use.status, "parent:mapped_use", use.strength)
    neighbours = _comparable(context, area, use.value)
    diagnostics = list(context.diagnostics)
    if context.manifest.profile == "footprint-only-v1":
        diagnostics.append("context_unavailable_footprint_only")
    if use.status == "conflict":
        diagnostics.append("conflicting_mapped_use")
    if use.status == "observed" and candidates[0].score >= 1.5 and candidates[0].use != use.value:
        diagnostics.append("mapped_use_overrides_neighbourhood")
    diagnostics.extend(f"invalid_{o.field}" for o in ev.observations if o.status == "invalid")

    floor_m = {"industrial": 5., "agricultural": 4.5, "commercial": 3.6, "civic": 3.6,
               "ancillary": 2.8}.get(use.value, 3.)
    cls = _text(observed(ev, "class"))
    form = _morphology(ev, context, area, half_width, use.value)
    identity = attrs.get("seed_id") or footprint.outer
    default_floors = 4 if cls in ("apartments", "dormitory") else \
        1 if use.value in ("ancillary", "agricultural", "industrial") else 2
    if cls == "bungalow" or (form.value == "detached_lowrise" and materials.unit(identity, "lowrise-storeys") < .75):
        default_floors = 1
    nf = observed(ev, "num_floors")
    h = observed(ev, "height")
    if nf is not None:
        floors = max(1, min(120, int(round(nf))))
        if floors != nf:
            diagnostics.append("floor_count_rounded_or_limited")
        fd = Decision(floors, "observed", "mapped:num_floors", "high")
    else:
        fd = Decision(default_floors, "fallback", "use_floor_prior", "low")

    if h is not None:
        status = attrs.get("_height_status", "observed")
        hd = Decision(float(h), status, attrs.get("_height_source", "mapped:height"),
                      "high" if status == "observed" else "moderate")
    elif nf is not None:
        hd = Decision(fd.value * floor_m, "inferred", "mapped_floors_and_storey_prior", "moderate")
    else:
        measured = []
        for n in neighbours:
            top = observed(n.evidence, "height")
            low = observed(n.evidence, "min_height") or 0.
            if top is not None and 2. <= top - low <= 500.:
                measured.append((top - low, n.source_id))
        if len(measured) >= 3:
            hd = Decision(float(median(h for h, _ in measured)), "inferred", "observed_neighbour_heights",
                          "moderate", tuple(sorted(sid for _, sid in measured)))
        else:
            hd = Decision(fd.value * floor_m, "fallback", "use_height_prior", "low")

    low = hd.value <= 15. and area <= 500. and half_width <= 14.
    house_style = house_styles.select(environment.region, attrs.get('seed_id'), use.value,
                                      cls, fd.value, hd.value, area, bool(attrs.get('_part')))
    style_region = house_style.profile if house_style.variant != 'unmixed' else environment.region
    appearance_environment = replace(environment, region=style_region)
    from . import architectural_modifiers as modifiers
    selected = modifiers.select(style_region, context, identity, use.value, fd.value, area, bool(attrs.get('_part')))
    if house_style.variant != 'unmixed':
        diagnostics.extend(('house_style:'+house_style.variant,
                            'house_style_profile:'+(style_region or 'contemporary_generic')))
        if house_style.alternate:
            diagnostics.append('house_contemporary_family:'+house_style.alternate)
    # Geographic climate evidence is deliberately weak. It cannot override a
    # mapped roof or a supported local pattern, and applies only to low dwellings.
    roof_prior = "gabled" if low and use.value in ("residential", "agricultural", "unknown") \
        and context.climate not in (4, 5, 6, 7) else "flat"
    if roof_prior == "gabled" and form.value == "detached_lowrise" and area / max(4 * half_width**2, 1.) < 2.4:
        roof_prior = materials.choose(identity, "lowrise-roof", (("hipped", 3), ("gabled", 1)))
    from . import regional_architecture
    if low:
        roof_prior = regional_architecture.roof_default(style_region,use.value,low,identity,roof_prior)
    roof = _choice(ev, "roof_shape", neighbours, {r: r for r in SUPPORTED_ROOFS}, roof_prior)
    roof_variant='standard'
    if roof.status == "fallback":
        if style_region and low and regional_architecture.profile(style_region):
            roof = Decision(roof_prior, "fallback", "regional_roof_prior:"+style_region, "low")
        elif roof_prior != "flat":
            roof = Decision(roof_prior, "fallback", "low_building_climate_prior", "low")
    from .regional_roofs import supported_form
    if roof.status=='fallback' and roof.value!='flat' and low and supported_form(footprint) and style_region:
        regional_profile=regional_architecture.profile(style_region)
        if regional_profile and use.value in ('residential','mixed','commercial','civic','unknown'):
            from . import residential
            options=(residential.roof_options(environment.region,identity,fd.value)
                     if use.value in ('residential','unknown') and not attrs.get('_part') else None)
            roof_variant=materials.choose(identity,'regional-roof-variant-v1',options or regional_profile.get('roof_variants',[['standard',1]]))
            if roof_variant=='mansard':roof=Decision('hipped',roof.status,roof.source,roof.strength)
            elif roof_variant in ('gambrel','saltbox','shed','broad_eave','cross_gable'):
                roof=Decision('gabled',roof.status,roof.source,roof.strength)
            elif roof_variant=='flared_hip':
                roof=Decision('hipped',roof.status,roof.source,roof.strength)
    mapped_roof = observed(ev, "roof_shape")
    from . import commercial_roofs
    commercial_options = commercial_roofs.options(
        use.value, (cls, _text(observed(ev, 'subtype'))), footprint, fd.value, hd.value)
    commercial_prior = bool(commercial_options and roof.status == 'fallback' and
                            mapped_roof is None and not attrs.get('_part'))
    if attrs.get('_part') and use.value in ('commercial', 'industrial'):
        diagnostics.append('commercial_roof_part_omitted')
    if commercial_prior:
        choice = materials.choose(identity, 'ci-roof-form-v1', commercial_options)
        roof_variant = 'standard' if choice == 'flat' else choice
        roof = Decision('flat' if choice == 'flat' else 'gabled', 'fallback',
                        'sparse_use_roof_prior_v1', 'low')
    from . import stepped_gables
    if 'stepped_gable' in selected and not stepped_gables.suitable_footprint(footprint):
        selected=tuple(key for key in selected if key!='stepped_gable')
        diagnostics.append('stepped_gable_unsuitable_span')
    if roof.status == 'fallback' and supported_form(footprint):
        if 'mansard' in selected:
            roof = Decision('hipped', 'fallback', 'regional_modifier:mansard', 'low')
            roof_variant = 'mansard'
        elif 'stepped_gable' in selected:
            roof = Decision('gabled', 'fallback', 'regional_modifier:stepped_gable', 'low')
            roof_variant = 'standard'
        elif 'thatch' in selected:
            roof = Decision('gabled', 'fallback', 'regional_modifier:thatch', 'low')
            roof_variant = 'standard'
        elif 'roof_terrace' in selected:
            roof = Decision('flat', 'fallback', 'regional_modifier:roof_terrace', 'low')
            roof_variant = 'standard'
    if attrs.get("_part") and mapped_roof is None:
        roof = Decision("flat", "fallback", "unmapped_part_roof", "low")
    if mapped_roof is not None and _text(mapped_roof) not in SUPPORTED_ROOFS:
        diagnostics.append("unsupported_mapped_roof_flat_fallback")
        roof = Decision("flat", "fallback", "unsupported_mapped_roof", "low")
    if roof.value != "flat" and not can_pitch:
        diagnostics.append("pitched_roof_complexity_limit_flat_fallback")
        roof = Decision("flat", "fallback", "roof_complexity_limit", "low")
    elif roof.value != "flat" and not footprint.is_rectangle():
        diagnostics.append("clipped_pitched_roof_envelope")
    if roof.value != "flat" and half_width < .5:
        diagnostics.append("narrow_pitched_roof_flat_fallback")
        roof = Decision("flat", "fallback", "narrow_outline", "low")

    pitch = 32. if 17 <= context.climate <= 30 else 22. if 1 <= context.climate <= 3 else 26.
    if form.value == "detached_lowrise" and not 17 <= context.climate <= 30:
        pitch = 20. + 6. * materials.unit(identity, "lowrise-pitch")
    if low and use.value in ('residential','mixed','commercial','civic','unknown'):
        pitch = regional_architecture.pitch_default(style_region,identity,pitch)
    rh = observed(ev, "roof_height")
    if commercial_prior:
        pitch = 7. + 5. * materials.unit(identity, 'ci-roof-pitch-v1')
    if 'stepped_gable' in selected and roof.value=='gabled' and roof_variant=='standard' and rh is None:
        # This specific narrow-gable recipe needs a steeper profile. Shared
        # wall-height, absolute-rise and mapped-total caps still apply below.
        pitch=38.+3.*materials.unit(identity,'stepped-gable-pitch-v1')
    rise = 0.
    if roof.value != "flat":
        from .roof_proportions import inferred_rise
        fixed_top = h is not None or hd.source == "observed_neighbour_heights"
        domestic = use.value in ('residential', 'unknown', 'mixed') and hd.value <= 15.
        rise = float(rh) if rh is not None else inferred_rise(
            footprint, roof.value, roof_variant, half_width, pitch, hd.value, fixed_top, domestic)
        if commercial_prior and rh is None:
            # Warehouse spans must not create house-like towering gables.
            rise = min(rise, 2.8, hd.value * (.23 if fixed_top else .30))
        if rh is None and rise < half_width * math.tan(math.radians(pitch)) - 1e-8:
            diagnostics.append("inferred_roof_proportion_limited")
        if rh is not None and (rise <= 0. or (rise >= hd.value and
                                            (h is not None or hd.source == "observed_neighbour_heights"))):
            diagnostics.append("roof_height_conflicts_with_envelope")
            roof = Decision("flat", "fallback", "conflicting_roof_height", "low")
            rise = 0.
        elif rh is None and (h is not None or hd.source == "observed_neighbour_heights"):
            # Keep the measured top exactly; a guessed roof cannot consume the
            # mapped storeys or make the eaves taller than the source envelope.
            rise = min(rise, .4 * hd.value, max(0., hd.value - (fd.value if nf else 1) * 2.2))
            if rise < .1:
                roof = Decision("flat", "fallback", "insufficient_roof_clearance", "low")
                rise = 0.
        if h is None:
            hd = Decision(hd.value + rise, hd.status, hd.source, hd.strength, hd.support) \
                if hd.source != "observed_neighbour_heights" else hd
        pitch = math.degrees(math.atan2(rise, half_width)) if rise else 0.
    elif rh is not None and rh > 0.:
        diagnostics.append("roof_height_unrepresented_by_flat_roof")
    if roof.value != "flat" and (observed(ev, "roof_direction") is not None or
                                observed(ev, "roof_orientation") is not None):
        diagnostics.append("mapped_roof_alignment_not_yet_supported")
    body = float(hd.value - rise)
    if 'stepped_gable' in selected and not stepped_gables.fits(footprint,roof.value,roof_variant,rise):
        selected=tuple(key for key in selected if key!='stepped_gable')
        diagnostics.append('stepped_gable_insufficient_proportions')
    if nf is None:
        fd = Decision(max(1, min(120, int(round(body / floor_m)))), "inferred",
                      "resolved_height_and_storey_prior", hd.strength)
    if not 2.2 <= body / fd.value <= (10. if use.value in ("industrial", "agricultural") else 6.):
        diagnostics.append("height_storey_conflict")
        # Retain mapped heights and raw floor evidence, but resolve usable floor
        # spacing instead of rendering four storeys squeezed into five metres.
        if nf is not None:
            fd = Decision(max(1, min(120, int(round(body / floor_m)))), "inferred",
                          "height_over_conflicting_mapped_floors", "low")

    facade_default = (environments.material_prior(appearance_environment,use.value,'facade',identity,
                         materials.facade_prior(use.value, cls, fd.value, identity)) if fd.value <= 3 else
                     materials.facade_prior(use.value, cls, fd.value, identity))
    if 'half_timber' in selected:
        facade_default='render'
    facade = _choice(ev, "facade_material", neighbours, FACADE_ALIASES,
                     modifiers.material(selected, 'facade', house_styles.facade_prior(house_style, facade_default)))
    roof_mat = _choice(ev, "roof_material", neighbours, ROOF_ALIASES,
                      environments.material_prior(appearance_environment,use.value,'roof',identity,
                          materials.roof_prior(use.value, roof.value, identity)) if roof.value != 'flat' else
                      materials.roof_prior(use.value, roof.value, identity))
    if commercial_prior and roof.value != 'flat' and roof_mat.status == 'fallback':
        roof_mat = Decision('metal', 'fallback', 'sparse_use_roof_covering_v1', 'low')
    if roof_mat.status == 'fallback' and roof.value != 'flat':
        roof_mat = replace(roof_mat, value=modifiers.material(selected, 'roof', roof_mat.value))
    city_flat = (roof.value == 'flat' and body > 15. and
                 ((cls == 'office' and 13 <= fd.value <= 120) or
                  (cls == 'hotel' and 5 <= fd.value <= 120)))
    if style_region and not city_flat and regional_architecture.profile(style_region):
        if facade.status == 'fallback' and fd.value<=3 and use.value in ('residential','mixed','commercial','civic','unknown'):
            facade = Decision(facade.value,'fallback','regional_construction_prior:'+style_region,'low')
        if roof_mat.status == 'fallback' and roof.value != 'flat' and use.value in ('residential','mixed','commercial','civic','unknown'):
            roof_mat = Decision(roof_mat.value,'fallback','regional_construction_prior:'+style_region,'low')
    if attrs.get("_part"):
        if facade.status == "observed" and "facade_material" in attrs.get("_inherited_fields", ()):
            facade = Decision(facade.value, facade.status, "parent:" + facade.source, facade.strength)
        if roof_mat.status == "observed" and "roof_material" in attrs.get("_inherited_fields", ()):
            roof_mat = Decision(roof_mat.value, roof_mat.status, "parent:" + roof_mat.source, roof_mat.strength)
    for field, aliases in (("facade_material", FACADE_ALIASES), ("roof_material", ROOF_ALIASES)):
        value = observed(ev, field)
        if value is not None and _text(value) not in aliases:
            diagnostics.append(f"unsupported_{field}")
    family = {"brick": "masonry_punched", "stone": "masonry_punched", "wood": "timber_punched",
              "concrete": "concrete_punched", "metal": "metal_utilitarian", "glass": "glazed_frame",
              "render": "rendered_punched"}[facade.value]
    architecture = Decision(family, "inferred" if facade.status != "fallback" else "fallback",
                            "resolved_facade_system", facade.strength)
    selection = presets.select(use.value, (cls, _text(observed(ev, "subtype"))), footprint,
                               fd.value, context.climate, identity, context.zones, context.land_use, environment,
                               context=context, body_height=body, property_identity=attrs.get("_property_identity"))
    if selection.preset.id == "unresolved_shell":
        diagnostics.append("preset_unresolved_shell")
    for zone in context.zones:
        if zone.meaning == "statutory" and zone.status == "effective" and zone.overlap >= .6 \
                and use.status == "observed" and use.value not in zone.uses:
            diagnostics.append(f"mapped_use_differs_from_zone:{zone.source_id}:{zone.raw_code}")
    import buildings as b
    sampled = context.roof_colour if not attrs.get('_part') else None
    mapped_colour = b.parse_color(attrs.get('roof_color'))
    colour = Decision((), 'fallback', 'material_palette', 'low')
    if sampled is not None:
        colour = Decision(sampled.rgb, 'inferred', 'imagery:' + sampled.source, 'moderate',
                          (sampled.imagery_digest, sampled.geometry_digest))
        if mapped_colour is not None:
            diagnostics.append('imagery_roof_colour_overrides_mapped_fallback')
    elif mapped_colour is not None:
        colour = Decision(mapped_colour, 'fallback', 'mapped:roof_color', 'moderate')
    if roof.value=='flat' or attrs.get('_part'):roof_variant='standard'
    if roof_variant!='standard':diagnostics.append('regional_roof_variant:'+roof_variant)
    from . import residential
    dwelling=residential.resolve_id(environment.region,identity,fd.value,use.value,cls,hd.value,area,bool(attrs.get('_part')))
    if dwelling:diagnostics.append('dwelling_structure:'+dwelling)
    return Resolution(use, architecture, facade, roof, roof_mat, hd, fd, body, rise, pitch,
                      candidates, context.manifest, tuple(diagnostics), form, selection, colour,roof_variant,house_style,dwelling,selected)
