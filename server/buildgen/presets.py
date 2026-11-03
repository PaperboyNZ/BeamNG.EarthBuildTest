"""Executable form recipes, selected from observations and measured dimensions.

Named historic styles remain research proposals. A preset changes facade grammar,
not the observed footprint, occupancy label or total height.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

from . import materials
from . import environments


VERSION = 3


@dataclass(frozen=True, slots=True)
class Preset:
    id: str
    use: str
    classes: tuple[str, ...]
    min_area: float
    max_area: float
    min_floors: int
    max_floors: int
    window_width: float
    bay: float
    windows: bool
    shop: bool
    service: bool
    garage: bool
    shading: bool
    courtyard: bool = False
    environments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Selection:
    preset: Preset
    reasons: tuple[str, ...]
    alternatives: tuple[str, ...]
    climate_response: str
    version: int = VERSION
    environment: environments.Environment = environments.Environment()


@lru_cache(maxsize=1)
def catalogue():
    rows = json.loads(Path(__file__).with_name("catalog").joinpath("presets.json").read_text())["presets"]
    rows += json.loads(Path(__file__).with_name("catalog").joinpath("commercial.json").read_text())["presets"]
    rows += json.loads(Path(__file__).with_name("catalog").joinpath("commercial_forms.json").read_text())["presets"]
    result = tuple(Preset(**dict(r, classes=tuple(r["classes"]), environments=tuple(r.get('environments',())))) for r in rows)
    if len({p.id for p in result}) != len(result):
        raise ValueError("duplicate building preset")
    for p in result:
        if not 0 < p.window_width < p.bay or not 0 < p.min_area <= p.max_area or not 1 <= p.min_floors <= p.max_floors:
            raise ValueError(f"invalid preset dimensions: {p.id}")
    return result


def select(use, classes, footprint, floors, climate, identity, zones=(), land_use=(), environment=None,
           context=None, body_height=None, property_identity=None):
    environment = environment or environments.Environment()
    rows = catalogue()
    available = [p for p in rows if p.use == use and p.min_area <= footprint.area <= p.max_area
                 and p.min_floors <= floors <= p.max_floors and (not p.courtyard or footprint.holes)
                 and (not p.environments or environment.kind in p.environments)]
    mapped = [p for p in available if set(p.classes) & set(classes)]
    # Specific templates require mapped class evidence. Generic use is insufficient
    # to invent a hospital, factory process line, greenhouse or retail tenancy.
    pool = mapped or [p for p in available if not p.classes]
    # Dedicated commercial grammars supersede their broad shell only when the
    # class and measured dimensions fit. Residential weighting is unchanged.
    dedicated = [p for p in mapped if p.id.startswith('ci_')]
    if dedicated:
        pool = dedicated
    # A supported association may select a facade grammar only when compatible
    # with the independently resolved physical building use.
    from . import property_programme
    property_id = property_programme.preset_for_identity(property_identity, use)
    property_rows = [p for p in rows if p.id == property_id]
    if property_rows:
        pool = property_rows
    elif (hasattr(property_identity, 'get') and
          property_identity.get('kind') == 'food_retail_size_unresolved'):
        # The use is known but neither visual size band is established. Avoid
        # falling back to a mapped supermarket or small-grocery facade.
        pool = [p for p in available if not p.classes]
    from . import commercial_forms
    form_weights, form_reasons = commercial_forms.weights(use, classes, footprint, floors, body_height, context)
    forms = [p for p in available if p.id in form_weights]
    # Broad use needs architectural variety even without a detailed class/zone.
    # These forms describe appearance; the resolved occupancy remains untouched.
    if forms and not property_rows:
        pool = forms
    else:
        pool = [p for p in pool if p.id not in commercial_forms.IDS]
    reasons = ["mapped_class" if mapped else f"resolved_use:{use}", "measured_footprint_fit", f"storeys:{floors}"]
    reasons.extend(f"observed_land_use:{kind}:{overlap:.3f}" for kind,overlap in land_use if overlap >= .6)
    if forms and not property_rows:
        reasons.extend(form_reasons)
    if property_rows:
        reasons.append("supported_property_identity")
    if footprint.holes:
        courts = [p for p in pool if p.courtyard]
        if courts:
            pool = courts
            reasons.append("observed_courtyard")
    if not pool:
        pool = [p for p in rows if p.id == "unresolved_shell"]
        reasons.append("no_compatible_preset_simplified_shell")
    pool.sort(key=lambda p: p.id)
    chosen_id = materials.choose(identity, 'preset-v2',tuple(
        (p.id,form_weights.get(p.id,1.)*environments.weight(p.id,environment)) for p in pool))
    chosen = next(p for p in pool if p.id == chosen_id)
    reasons.extend(environment.reasons)
    if environment.region:
        reasons.append('regional_prior:' + environment.region)
    reasons.extend(f"zone_context:{z.source_id}:{z.raw_code}" for z in zones
                   if z.status == "effective" and z.meaning != "planned" and use in z.uses and z.overlap >= .6)
    response = "solar_shading" if climate in range(1, 8) and chosen.shading else \
        "cold_climate" if 17 <= climate <= 30 else "temperate_or_unknown"
    return Selection(chosen, tuple(sorted(set(reasons))), tuple(p.id for p in pool if p != chosen), response,
                     VERSION, environment)
