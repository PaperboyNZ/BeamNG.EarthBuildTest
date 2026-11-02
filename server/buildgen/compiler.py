"""Adapt resolved v2 evidence to the existing mesh material/window kernels."""
import math
from dataclasses import replace
import numpy as np

from .inference import resolve
from . import materials, regional_architecture, city, house_styles
from . import roofs


def specialised(attrs, area):
    """Keep legacy eligibility while sharing auditable specialist dispatch rules."""
    from .specialized import legacy_route
    return legacy_route(attrs, area)


def plan(ring, attrs, look=None):
    import buildings as b
    fp = attrs["_footprint"]
    _, _, _, hw = b.oriented_box(ring)
    source_fp = attrs.get("_planning_footprint") or fp
    _, _, _, source_hw = b.oriented_box(np.asarray(source_fp.outer))
    result = resolve(attrs, source_fp, source_hw, attrs.get("_context"), can_pitch=roofs.supported(fp))
    from .regional_roofs import supported_form
    if not supported_form(fp) and result.roof_variant!='standard':
        result=replace(result,roof_variant='standard',diagnostics=result.diagnostics+('regional_roof_variant_complex_outline_fallback',))
    if result.roof.value == "hipped" and not fp.is_rectangle():
        strategy = roofs.envelope(fp, "hipped").strategy
        diagnostics = tuple(d for d in result.diagnostics if d != "clipped_pitched_roof_envelope")
        result = replace(result, diagnostics=diagnostics + ("roof_strategy:" + strategy,))
    sid = attrs.get("seed_id")
    # Production callers always carry source IDs; direct geometry tools can use
    # canonical footprint content explicitly, without a tile-centroid seed.
    seed = look if look is not None else b._hash01(sid if sid is not None else fp.outer, "v2_appearance")

    def tint(mat, table, channel, choices=None):
        choices = tuple(choices) if choices is not None else tuple(range(len(table[mat])))
        return f"{mat}|{choices[min(int(b._hash01(seed, channel) * len(choices)), len(choices) - 1)]}"

    material = result.facade.value
    style_region = house_styles.profile_region(result)
    mixed_house = result.house_style.variant != 'unmixed'
    city_candidate = city.candidate(result, str(attrs.get('class') or '').strip().lower())
    kind = {"brick": b.BRICK_WALL, "stone": b.STONE, "wood": b.SIDING, "concrete": b.CONCRETE,
            "render": b.STUCCO, "metal": b.METALWALL, "glass": b.OFFICE}[material]
    if material == "brick":
        facade = ("bne_brick_red", "bne_brick_dark", "bne_brick_tan")[min(int(seed * 3), 2)]
        if not city_candidate and result.use.value in ('residential','mixed','commercial','civic','unknown'):
            colour=regional_architecture.wall_colour(style_region,material,seed,None,broaden=mixed_house)
            if colour is not None:facade=b.custom_look(kind,colour)
    elif material in ("concrete", "wood", "render", "metal"):
        colour = materials.colour(seed, material)
        if not city_candidate and result.use.value in ('residential','mixed','commercial','civic','unknown'):
            colour = regional_architecture.wall_colour(style_region,material,seed,colour,broaden=mixed_house)
        facade = b.custom_look(kind, colour)
    else:
        facade = tint(kind, b.WALL_TINTS, "facade")
    color = b.parse_color(attrs.get("facade_color"))
    if color is None and result.facade.status == 'fallback':
        if 'half_timber' in result.modifiers and material == 'render':
            facade = b.custom_look(kind, (.93, .88, .76))
        elif 'white_stucco' in result.modifiers and material == 'render':
            facade = b.custom_look(kind, (.96, .95, .91))
        elif 'red_brick' in result.modifiers and material == 'brick':
            facade = 'bne_brick_red'
    if color is not None:
        facade = b.custom_look(kind, color)
    wall = None if material == "glass" else facade
    band = b.BAND_OFFICE if material == "glass" else b.BAND_SASH
    recipe = result.selection.preset
    windows = (recipe.windows or material == "glass") \
        and result.body_height / result.floors.value >= 2.2
    cls = str(attrs.get("class") or "").strip().lower()
    shop = recipe.shop
    kind = {"membrane": b.ROOF_FLAT, "metal": b.ROOF_METAL, "copper": b.ROOF_METAL,
            "tile": b.ROOF_SLATE, "slate": b.ROOF_SLATE, "shingle": b.ROOF_SHINGLE,
            "glass": b.OFFICE, "thatch": b.ROOF_THATCH}[result.roof_material.value]
    if result.roof_material.value == "copper":
        roof_mat = b.custom_look(kind, b.COLOR_NAMES["copper"])
    elif kind == b.OFFICE:
        roof_mat = tint(kind, b.WALL_TINTS, "roof")
    elif kind == b.ROOF_THATCH:
        roof_mat = b.custom_look(kind, (.85, .79, .65))
    else:
        choices = range(4, 7) if result.roof_material.value == "tile" else \
            range(4) if result.roof_material.value == "slate" else None
        roof_mat = tint(kind, b.ROOF_TINTS, "roof", choices)
    color = result.roof_colour.value
    if not color and not city_candidate and result.use.value in ('residential','mixed','commercial','civic','unknown'):
        color=regional_architecture.roof_colour(style_region,result.roof_material.value,seed,broaden=mixed_house)
    if color:
        roof_mat = b.custom_look(kind, color)
    return b.Spec(ring=np.asarray(fp.outer, np.float64), floors=result.floors.value,
                  floor_h=result.body_height / result.floors.value, height=result.body_height,
                  roof=result.roof.value, roof_mat=roof_mat, facade=facade, wall=wall, band=band,
                  shop=shop, plain=not windows, seed=seed,
                  min_h=1.05 if ('stilts' in result.modifiers and attrs.get('height') is None
                                and attrs.get('min_height') is None and not attrs.get('_part')
                                and result.floors.value <= 2) else 0., windows=windows, steeple=False,
                  porch=False, cls=cls or (result.use.value if result.use.value != "unknown" else ""),
                  deck=False, pitch=math.degrees(math.atan2(result.roof_rise, hw)) if result.roof_rise else 0.,
                  inference=result, diagnostics=result.diagnostics)
