"""Diagnostic specialist selection; legacy routing is deliberately unchanged.

This is not a geometry planner or an ingestion adapter. Optional semantic keys
are caller-supplied observations, not evidence that the production feed retains
them. In particular, names and geography never confirm use, fabric or mode.
"""
from dataclasses import asdict, dataclass
import json
import math
from numbers import Real


CONTRACT_VERSION = 1
_CHURCH = frozenset(("church", "chapel", "cathedral"))
_RELIGIOUS = frozenset(("religious", "place_of_worship", "mosque", "temple", "synagogue"))
_FUEL = frozenset(("fuel", "fueling_station", "gas_station", "petrol_station"))
_PASSENGER = frozenset(("passenger_terminal", "airport_terminal", "bus_station", "ferry_terminal", "train_station"))
_FREIGHT = frozenset(("freight_terminal", "cargo_terminal"))
_CURRENT_USES = {**dict.fromkeys(_CHURCH, "church"), **dict.fromkeys(_RELIGIOUS, "religious"),
                 **dict.fromkeys(_FUEL, "fuel_station"), **dict.fromkeys(_PASSENGER, "passenger_terminal"),
                 **dict.fromkeys(_FREIGHT, "freight_terminal"), "residential": "residential", "house": "residential",
                 "apartments": "residential", "retail": "retail", "shop": "retail", "hotel": "hotel",
                 "commercial": "commercial", "industrial": "industrial", "office": "office",
                 "parking_garage": "parking_garage"}
_MODES = {"air": "air", "airport": "air", "aviation": "air", "bus": "bus", "ferry": "ferry", "rail": "rail"}
_OBSERVED_FIELDS = ("class", "subtype", "name", "building", "building_use", "use", "amenity", "religion",
                    "terminal_use", "transport_mode", "aeroway", "railway", "min_height", "roof_shape",
                    "parent_id", "src_dataset", "src_record", "seed_id")


@dataclass(frozen=True, slots=True)
class LegacyRules:
    """Detached dispatch constants; callers may pass these to avoid an import.

    No defaults duplicate buildings.py's dimensional thresholds. The default
    select() path reads those constants lazily after buildings has initialized.
    """
    bridge_classes: frozenset[str]
    church_classes: frozenset[str]
    garage_tag_classes: frozenset[str]
    garage_min_m2: float
    pyramid_min_m2: float

    def __post_init__(self):
        for name in ("bridge_classes", "church_classes", "garage_tag_classes"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))

    @classmethod
    def from_buildings(cls):
        import buildings as b
        return cls(frozenset(b.BRIDGE_CLASSES), frozenset(b.CHURCH_CLASSES),
                   frozenset(b.GARAGE_TAG_CLASSES), b.GARAGE_MIN_M2, b.PYRAMID_MIN_M2)


@dataclass(frozen=True, slots=True)
class SourceObservation:
    field: str
    value: str
    status: str = "observed"


@dataclass(frozen=True, slots=True)
class SpecializedCapability:
    adapter: str
    geometry_accepted: bool
    required_features: tuple[str, ...]
    unsupported_features: tuple[str, ...]
    fallback: str
    fallback_topology_verified: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecializedSelection:
    contract_version: int
    legacy_route: bool
    legacy_reasons: tuple[str, ...]
    facility_use: str
    architectural_fabric: str
    transport_mode: str
    family: str | None
    vocabulary: str | None
    owner: str
    confidence: str
    ambiguous: bool
    observations: tuple[SourceObservation, ...]
    reasons: tuple[str, ...]
    capability: SpecializedCapability

    def to_dict(self):
        """Return detached diagnostic data, never source objects or geometry."""
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _legacy_reason(attrs, area, rules=None):
    # Preserve original lower(), substring checks, truthiness, thresholds and
    # short-circuit order exactly, including misleading names and invalid area
    # values which the old selector never examines after an earlier match.
    if rules is None:
        import buildings as b
        bridge_classes, church_classes = b.BRIDGE_CLASSES, b.CHURCH_CLASSES
        garage_tag_classes = b.GARAGE_TAG_CLASSES
        garage_min_m2, pyramid_min_m2 = b.GARAGE_MIN_M2, b.PYRAMID_MIN_M2
    else:
        bridge_classes, church_classes = rules.bridge_classes, rules.church_classes
        garage_tag_classes = rules.garage_tag_classes
        garage_min_m2, pyramid_min_m2 = rules.garage_min_m2, rules.pyramid_min_m2
    cls = str(attrs.get("class") or "").lower()
    name = str(attrs.get("name") or "").lower()
    for field in ("ship", "pier", "bridge_part", "bridge_masonry"):
        if attrs.get(field):
            return "legacy_flag:" + field
    if cls in bridge_classes:
        return "legacy_class:bridge"
    if cls in church_classes:
        return "legacy_class:church"
    if any(w in name for w in ("church", "chapel", "cathedral", "terminal", "concourse")):
        return "legacy_name:church_or_terminal"
    if cls in ("parking", "parking_garage") and area >= garage_min_m2:
        return "legacy_class_area:parking_garage"
    if "parking garage" in name:
        return "legacy_name:parking_garage"
    if "garage" in name and area > 800:
        return "legacy_name_area:garage"
    if attrs.get("garage") and cls in garage_tag_classes:
        return "legacy_flag_class:garage"
    if attrs.get("roof_shape") == "pyramidal" and area >= pyramid_min_m2:
        return "legacy_roof_area:pyramidal"
    return None


def _text(value):
    if value is None:
        return ""
    if _nonfinite(value):
        return ""
    return str(value).strip().lower() if isinstance(value, (str, Real)) else ""


def _nonfinite(value):
    if not isinstance(value, Real):
        return False
    try:
        return not math.isfinite(value)
    except OverflowError:
        return True


def _observations(attrs):
    out = []
    for field in _OBSERVED_FIELDS:
        value = attrs.get(field)
        if value is None:
            continue
        if isinstance(value, (str, Real)):
            invalid = _nonfinite(value)
            out.append(SourceObservation(field, str(value), "invalid" if invalid else "observed"))
        else:
            out.append(SourceObservation(field, type(value).__name__, "unsupported_value"))
    return tuple(out)


def _unique(values, conflict_value="unknown"):
    values = set(values)
    return (next(iter(values)) if len(values) == 1 else conflict_value if values else "unknown"), len(values) > 1


def legacy_route(attrs, area, *, rules=None):
    """Lightweight boolean compatibility path, without diagnostic allocations."""
    return _legacy_reason(attrs, area, rules) is not None


def select(attrs, area, *, rules=None):
    """Classify conservatively and report capability without changing routing.

    .legacy_route is the replacement for compiler.specialised(), not truthiness
    of this record. Optional building/use/transport tags are direct observations;
    their complete production feed/cache/worker lineage is not yet established.
    No new geometry, family, denomination, operator or transport interface is
    selected here. All fallback topology remains explicitly unverified.
    """
    legacy_reason = _legacy_reason(attrs, area, rules)
    text = {field: _text(attrs.get(field)) for field in _OBSERVED_FIELDS}
    cls, subtype, building = text["class"], text["subtype"], text["building"]
    tags = {cls, subtype}
    name = text["name"]
    reasons = []
    conflicts = []

    # building=church describes fabric, whereas a converted building's current
    # use can be residential/retail/etc. A generic religious tag confirms neither
    # a church envelope nor Christian symbols.
    fabric_signals = []
    if (tags | {building}) & _CHURCH:
        fabric_signals.append("church")
    terminal = bool((tags | {building}) & (_PASSENGER | _FREIGHT | {"terminal", "concourse"})
                    or text["terminal_use"] in ("passenger", "freight", "cargo")
                    or text["aeroway"] == "terminal" or text["amenity"] in ("bus_station", "ferry_terminal")
                    or text["railway"] == "station")
    if terminal:
        fabric_signals.append("terminal")
    if "parking_garage" in tags or building == "parking_garage":
        fabric_signals.append("parking_garage")
    fabric, conflict = _unique(fabric_signals)
    if conflict:
        conflicts.append("conflicting_fabric")

    explicit_use = [text[k] for k in ("building_use", "use") if text[k]]
    uses = [_CURRENT_USES.get(v, v) for v in explicit_use]
    if not explicit_use:
        uses = [_CURRENT_USES[v] for v in tags if v in _CURRENT_USES]
        if text["amenity"] == "place_of_worship":
            uses.append("religious" if "church" not in uses else "church")
        if text["amenity"] == "fuel":
            uses.append("fuel_station")
        if text["amenity"] in ("bus_station", "ferry_terminal") or text["railway"] == "station":
            uses.append("passenger_terminal")
        if text["terminal_use"] in ("passenger", "freight", "cargo"):
            uses.append("passenger_terminal" if text["terminal_use"] == "passenger" else "freight_terminal")
    if "church" in uses and "religious" in uses:
        uses = [v for v in uses if v != "religious"]
    use, conflict = _unique(uses, "terminal_unknown" if terminal else "unknown")
    if conflict:
        conflicts.append("conflicting_current_use")
    elif use == "unknown" and terminal:
        use = "terminal_unknown"
        reasons.append("passenger_or_freight_unknown")
    if explicit_use and fabric == "church" and use not in ("church", "religious"):
        reasons.append("church_fabric_with_different_current_use")
    if use == "religious":
        reasons.append("generic_religious_is_not_confirmed_church")
    if text["religion"]:
        reasons.append("religion_does_not_establish_fabric_or_denomination")

    modes = []
    if text["transport_mode"] in _MODES:
        modes.append(_MODES[text["transport_mode"]])
    elif text["transport_mode"]:
        reasons.append("unsupported_transport_mode")
    if terminal:
        if text["aeroway"] == "terminal" or "airport_terminal" in tags:
            modes.append("air")
        for value, mode in (("bus_station", "bus"), ("ferry_terminal", "ferry"), ("train_station", "rail")):
            if value in tags or text["amenity"] == value:
                modes.append(mode)
        if text["railway"] == "station":
            modes.append("rail")
    mode, conflict = _unique(modes)
    if conflict:
        conflicts.append("conflicting_transport_mode")
    if terminal and mode == "unknown":
        reasons.append("transport_mode_unknown")

    keyword_church = any(w in name for w in ("church", "chapel", "cathedral"))
    keyword_terminal = any(w in name for w in ("terminal", "concourse"))
    keyword_ambiguous = (keyword_church and fabric != "church") or (keyword_terminal and not terminal)
    if keyword_ambiguous:
        reasons.append("name_keyword_does_not_confirm_specialist")
    if legacy_reason and (legacy_reason.startswith("legacy_name") or legacy_reason.startswith("legacy_roof_area")):
        reasons.append("legacy_heuristic_is_not_geometry_evidence")
    reasons.extend(conflicts)
    owner = ("gasstations" if use == "fuel_station" else "commercial_industrial" if use == "freight_terminal"
             else "infrastructure" if legacy_reason and (legacy_reason.startswith("legacy_flag:")
                                                         or legacy_reason == "legacy_class:bridge") else "buildgen")
    if owner == "gasstations":
        reasons.append("fuel_resources_remain_owned_by_gasstations")
    if owner == "commercial_industrial":
        reasons.append("freight_remains_commercial_industrial")

    required = []
    fp = attrs.get("_planning_footprint")
    if fp is None:
        fp = attrs.get("_footprint")
    holes = getattr(fp, "holes", ()) if fp is not None else ()
    if holes is not None and len(holes) > 0:
        required.append("source_voids")
    try:
        minimum = float(attrs.get("min_height", 0.) or 0.)
        if math.isfinite(minimum) and minimum > 0:
            required.append("elevated_volume")
    except (TypeError, ValueError, OverflowError):
        pass
    if text["parent_id"]:
        required.append("mapped_part_relationship")
    if text["roof_shape"] in ("dome", "onion", "round", "curved"):
        required.append("special_roof")
    capability = SpecializedCapability("diagnostics_only", False, tuple(required), tuple(required),
                                       "legacy_compatibility" if legacy_reason else "existing_route", False,
                                       ("specialist_geometry_adapter_not_implemented", "fallback_topology_unverified"))
    ambiguous = bool(conflicts or keyword_ambiguous or use == "terminal_unknown")
    confidence = "conflict" if conflicts else "ambiguous" if ambiguous else "observed" if uses or fabric_signals else "unknown"
    return SpecializedSelection(CONTRACT_VERSION, legacy_reason is not None, (legacy_reason,) if legacy_reason else (),
                                use, fabric, mode, None, None, owner, confidence, ambiguous, _observations(attrs),
                                tuple(reasons), capability)


# The spelling reads naturally at call sites which expose an eligibility query.
selectable = select
