"""Bounded facade authoring vocabulary for supported stage-one properties.

This describes visual opportunities, not evidence that site furniture or a
particular tenant frontage exists. The renderer must fit all elements to the
observed envelope and available access space.
"""
from dataclasses import dataclass
from . import materials


@dataclass(frozen=True, slots=True)
class Programme:
    kind: str
    variant: str
    regional_style: str
    decorations: tuple[str, ...]
    proportions: tuple[tuple[str, float], ...]
    size_modifier: str = ''


PRESETS = {
    'grocery_store': 'ci_grocery_store', 'supermarket': 'ci_supermarket',
    'strip_shops': 'ci_strip_shops', 'trade_units': 'ci_trade_units',
    'clinic': 'ci_clinic', 'hospital': 'ci_hospital',
}
USES = {'grocery_store': 'commercial', 'supermarket': 'commercial',
        'strip_shops': 'commercial', 'trade_units': 'industrial',
        'clinic': 'civic', 'hospital': 'civic'}

# Values are dimensionless proposed fractions of the available facade, not new
# dimensions for the source building. Geometry must enforce clearance and fit.
RECIPES = {
    'grocery_store': (('inline', 'corner'), ('fascia', 'shop_glazing', 'awning'),
                      (('glazing_fraction', .54), ('fascia_fraction', .11))),
    'supermarket': (('central_entry', 'offset_entry'), ('fascia', 'entry_canopy', 'shop_glazing', 'bollards'),
                    (('glazing_fraction', .38), ('fascia_fraction', .14))),
    'strip_shops': (('regular_bays', 'varied_bays'), ('fascia', 'shop_glazing', 'shared_canopy'),
                    (('glazing_fraction', .55), ('fascia_fraction', .12))),
    'trade_units': (('regular_portals', 'paired_portals'), ('service_portal', 'staff_entry', 'unit_panel'),
                    (('portal_fraction', .55), ('panel_fraction', .10))),
    'clinic': (('street_entry', 'recessed_entry'), ('entry_canopy', 'directory', 'screened_glazing'),
               (('glazing_fraction', .30), ('canopy_fraction', .18))),
    'hospital': (('entrance', 'ward_facade'), ('entry_canopy', 'directory', 'regular_windows', 'shading'),
                 (('glazing_fraction', .34), ('canopy_fraction', .22))),
}
REGIONS = {
    'nz_temperate': 'nz_australia', 'au_southeast': 'nz_australia',
    'au_tropical_arid': 'nz_australia', 'eu_atlantic': 'britain_ireland',
    'jp_temperate': 'japanese_urban', 'tropical_humid': 'tropical_contemporary',
    'mainland_southeast_asia': 'tropical_contemporary',
    'indonesian_archipelago': 'tropical_contemporary', 'philippines': 'tropical_contemporary',
}
REGIONAL_DECORATIONS = {
    'nz_australia': ('simple_veranda', 'metal_fascia'),
    'britain_ireland': ('framed_shopfront', 'masonry_piers'),
    'japanese_urban': ('compact_sign_band', 'vertical_screen'),
    'tropical_contemporary': ('deep_shading', 'ventilated_screen'),
    'generic': ('simple_trim',),
}


def preset_for_identity(identity, use):
    """Return a supported physical-building preset, never promote a POI alone."""
    if not hasattr(identity, 'get') or identity.get('status') not in ('supported', 'verified'):
        return None
    kind = identity.get('kind')
    return PRESETS.get(kind) if USES.get(kind) == use else None


def for_spec(spec):
    """Return an immutable programme for the already selected property facade."""
    inference = getattr(spec, 'inference', None)
    if inference is None:
        return None
    preset = inference.selection.preset.id
    kind = next ( (k for k, v in PRESETS.items() if v == preset), None)
    if kind is None:
        return None
    identity = getattr(spec, 'property_identity', None)
    modifier = identity.get('size_modifier') if hasattr(identity, 'get') else None
    if kind != 'supermarket' or modifier != 'large':
        modifier = ''
    region = getattr(inference.selection.environment, 'region', '')
    regional_style = REGIONS.get(region, 'generic')
    variants, decorations, proportions = RECIPES[kind]
    seed = getattr(spec, 'seed', None)
    variant = materials.choose(seed, 'property-programme-variant-v1:'+kind,
                               tuple((value, 1) for value in variants))
    return Programme(kind, variant, regional_style,
                     decorations + REGIONAL_DECORATIONS[regional_style], proportions, modifier)
