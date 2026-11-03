"""Separate broad use, settlement form and regional construction priors.

Zoning may weight compatible forms but cannot establish present occupancy or
override measured dimensions. Regional packs are authoring priors, not surveys.
Explicit local overlays take priority over bundled global geographic polygons.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from . import materials


@dataclass(frozen=True, slots=True)
class Environment:
    kind: str = 'unknown'
    region: str = ''
    reasons: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(Path(__file__).with_name('catalog').joinpath('environments.json').read_text())


def resolve(context, use):
    eligible = [z for z in context.zones if z.status == 'effective' and z.meaning != 'planned' and z.overlap >= .6]
    regions = {z.region for z in eligible if z.region}
    region = next(iter(regions)) if len(regions)==1 else ''
    regional_reasons = ()
    if len(regions)>1:
        regional_reasons = ('conflicting_regional_overlays',)
    elif region:
        regional_reasons = ('explicit_regional_overlay:'+region,)
    elif context.location is not None:
        from .regional_geography import locate
        location = locate(*context.location)
        region = location.theme
        regional_reasons = ('regional_geography:'+location.method+':'+location.source,) if region else ()
    candidates = [z for z in eligible if z.environment and (use in z.uses or use == 'unknown')]
    # Conflicting overlays remain unknown; repeating a provider never adds votes.
    kinds = {z.environment for z in candidates}
    if len(kinds)==1:
        return Environment(next(iter(kinds)),region,regional_reasons+tuple(sorted({
            f'zone_environment:{z.source_id}:{z.raw_code}:{z.meaning}' for z in candidates})))
    observed = {k for k,overlap in context.land_use if overlap>=.6}
    aliases = {'residential':'residential_unspecified','industrial':'industrial_unspecified',
               'commercial':'commercial_unspecified','retail':'commercial_frontage','farmland':'rural',
               'farmyard':'rural','education':'education','medical':'health'}
    kinds = {aliases[k] for k in observed if k in aliases}
    if len(kinds)==1:
        return Environment(next(iter(kinds)),region,regional_reasons+('observed_land_use_environment',))
    return Environment('unknown',region,regional_reasons+(('conflicting_zone_environments',) if len(candidates)>1 else ()))


def weight(preset_id, environment):
    data = catalogue()['environments'].get(environment.kind,{})
    return float(data.get('preset_weights',{}).get(preset_id,1.))


def material_prior(environment, use, family, identity, fallback):
    if use not in ('residential','mixed','commercial','civic','unknown'):
        return fallback
    pack = catalogue()['regions'].get(environment.region,{})
    if pack.get('status') not in ('pilot','adapter_ready','active'):
        return fallback
    if pack.get('status') == 'active':
        from .regional_architecture import profile
        authored = profile(environment.region)
        if authored:
            choices = authored.get(family)
            # A pitched roof cannot receive a flat membrane from a mixed palette.
            if family == 'roof':choices = [(v,w) for v,w in choices if v!='membrane']
            return materials.choose(identity,'regional-'+family+'-v2',choices) if choices else fallback
    choices = pack.get(family)
    return materials.choose(identity,'regional-'+family+'-v1',choices) if choices else fallback
