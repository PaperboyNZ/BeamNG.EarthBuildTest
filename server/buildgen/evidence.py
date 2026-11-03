"""Normalise mapped attributes without confusing missing data with observations.

This adapter records source values only. It does not claim a source quality score
or turn a footprint-based estimate into a measured height.
"""
from dataclasses import dataclass
import math
import numpy as np


ATTRIBUTE_FIELDS = (
    "class", "subtype", "height", "num_floors", "min_height", "roof_shape", "roof_height", "name",
    "facade_material", "facade_color", "roof_material", "roof_color", "roof_direction", "roof_orientation",
    "min_floor", "num_floors_underground", "level",
    "height_src", "src_dataset", "src_record",
    "is_underground", "has_parts",
)
BOOLEAN_FIELDS=frozenset(('is_underground','has_parts'))
_NUMBERS = {"height", "min_height", "num_floors", "roof_height", "roof_direction",
            "min_floor", "num_floors_underground", "level"}
_POSITIVE = {"height", "num_floors"}
_SIGNED_LABELS = {"min_floor", "level"}


@dataclass(frozen=True, slots=True)
class Observation:
    field: str
    value: str | float | bool | None
    status: str
    source: str | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class BuildingEvidence:
    source_id: str | None
    parent_id: str | None
    source_record: str | None
    observations: tuple[Observation, ...]

    def get(self, field):
        return next((o for o in self.observations if o.field == field), None)


def _text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        # NaN represents absent text in some decoded/test feature tables.
        try:
            if not math.isfinite(float(value)):
                return None
        except (TypeError, ValueError):
            pass
    return str(value).strip() or None


def feature_attributes(features,index):
    """Mapped field values without turning legacy NULL->False into evidence."""
    arrays=features.attrs;result={k:arrays[k][index] if k in arrays else None for k in ATTRIBUTE_FIELDS}
    lost=[]
    for field in BOOLEAN_FIELDS:
        value=result[field];known=arrays.get(field+'__known')
        if value is None:continue
        if known is not None and bool(known[index]):result[field]=bool(value)
        elif bool(value):result[field]=True # legacy True cannot have come from a NULL
        else:
            result[field]=None
            if known is None:lost.append(field)
    if lost:result['_legacy_boolean_unknown']=tuple(sorted(lost))
    return result


def normalise_attributes(attrs):
    """Preserve supplied values and mark invalid/absent fields explicitly.

    Zero minimum/roof height and roof direction are valid. A NaN means missing;
    an infinity, negative dimension or malformed number is invalid. Conflicting
    total/minimum heights remain recorded for the later resolver to diagnose.
    """
    dataset = _text(attrs.get("src_dataset"))
    observations = []
    for field in ATTRIBUTE_FIELDS:
        if field in ("src_dataset", "src_record", "height_src"):
            continue
        raw = attrs.get(field)
        source = (_text(attrs.get("height_src")) or dataset) if field == "height" else dataset
        if field in BOOLEAN_FIELDS:
            if isinstance(raw,(bool,np.bool_)):
                observations.append(Observation(field,bool(raw),'observed',source))
            elif raw is None or isinstance(raw,(float,np.floating)) and math.isnan(raw):
                reason='legacy cache discarded boolean nullability' if field in attrs.get('_legacy_boolean_unknown',()) else None
                observations.append(Observation(field,None,'unknown',source,reason))
            else:observations.append(Observation(field,_text(raw),'invalid',source,'not a boolean'))
            continue
        if field not in _NUMBERS:
            value = _text(raw)
            observations.append(Observation(field, value, "observed" if value is not None else "unknown", source))
            continue
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            observations.append(Observation(field, None, "unknown", source))
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            observations.append(Observation(field, _text(raw), "invalid", source, "not a number"))
            continue
        if math.isnan(value):
            observations.append(Observation(field, None, "unknown", source))
        elif not math.isfinite(value):
            observations.append(Observation(field, str(value), "invalid", source, "non-finite number"))
        elif isinstance(raw, bool) or (value < 0 and field not in _SIGNED_LABELS) \
                or (field in _POSITIVE and value == 0):
            observations.append(Observation(field, value, "invalid", source, "invalid dimension or direction"))
        elif field == "roof_direction" and value > 360:
            observations.append(Observation(field, value, "invalid", source, "direction outside 0..360 degrees"))
        else:
            observations.append(Observation(field, value, "observed", source))
    return BuildingEvidence(_text(attrs.get("seed_id")), _text(attrs.get("parent_id")),
                            _text(attrs.get("src_record")), tuple(observations))
