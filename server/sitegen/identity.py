"""Immutable geographic identity and frame descriptors for site planning.

This module accepts geographic source coordinates, never tile-local geometry as
identity. Scalar conversion order is (longitude, latitude, ellipsoid height),
unlike ``geodesy.EnuFrame``'s (latitude, longitude, height). No file or pickle I/O.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import math


ANGLE_SCALE = 10_000_000
MAX_EXTENT_POINTS = 8192
MAX_EXTENT_DEGREES = 1.0
HORIZONTAL_DATUM = "WGS84"
VERTICAL_DATUM = "WGS84_ellipsoid"
UNITS = "metres"
_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)
_B = _A * (1 - _F)


def _text(value, field, limit=512):
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value.encode("utf-8")) > limit
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f"{field} requires bounded nonempty text without control characters")
    return value


def _number(value, field, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} requires a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} requires a finite number") from exc
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{field} outside {low}..{high}")
    return 0.0 if value == 0 else value


def _integer(value, field, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{field} requires an integer within {low}..{high}")
    return value


def _angle_e7(value):
    # Source JSON numbers are interpreted through Python's shortest decimal
    # representation. Decimal arithmetic keeps a binary product/modulo from
    # moving a decimal half-step across its round-to-even boundary.
    with localcontext() as context:
        context.prec = 40
        return int((Decimal(str(value)) * ANGLE_SCALE).to_integral_value(rounding=ROUND_HALF_EVEN))


def _object(data, fields):
    if not isinstance(data, dict) or set(data) != set(fields):
        raise ValueError("descriptor has missing or unsupported fields")


def canonical_json(value):
    """Deterministic JSON text; NaN/Infinity and arbitrary Python objects fail."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _digest(value):
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True, order=True)
class SourceIdentity:
    """Stable provider namespace and feature key; release is deliberately absent."""
    namespace: str
    feature_id: str

    def __post_init__(self):
        _text(self.namespace, "source namespace", 128)
        _text(self.feature_id, "source feature ID")

    def to_dict(self):
        return {"namespace": self.namespace, "feature_id": self.feature_id}

    @classmethod
    def from_dict(cls, data):
        _object(data, ("namespace", "feature_id"))
        return cls(data["namespace"], data["feature_id"])


@dataclass(frozen=True, slots=True, order=True)
class SourceRevision:
    """A pinned provider release/content revision attached to stable identity."""
    identity: SourceIdentity
    revision: str

    def __post_init__(self):
        if not isinstance(self.identity, SourceIdentity):
            raise ValueError("revision requires a SourceIdentity")
        _text(self.revision, "source revision")

    def to_dict(self):
        return {"identity": self.identity.to_dict(), "revision": self.revision}

    @classmethod
    def from_dict(cls, data):
        _object(data, ("identity", "revision"))
        return cls(SourceIdentity.from_dict(data["identity"]), data["revision"])

    @property
    def dependency_key(self):
        return "source-revision-v1:" + _digest(self.to_dict())


def semantic_id(kind, source, role=""):
    """Stable semantic name for a source role; revisions and frames do not enter."""
    _text(kind, "semantic kind", 64)
    if not isinstance(source, SourceIdentity):
        raise ValueError("semantic identity requires a SourceIdentity")
    if role != "":
        _text(role, "semantic role")
    return "sitegen-semantic-v1:" + _digest({"kind": kind, "source": source.to_dict(), "role": role})


def normalize_longitude(longitude):
    """Canonical [-180, 180) longitude; accept at most one extra complete wrap."""
    longitude = _number(longitude, "longitude", -540, 540)
    if -180 <= longitude < 180:
        return longitude
    result = (longitude + 180.0) % 360.0 - 180.0
    return 0.0 if result == 0 else result


def _geographic(longitude, latitude, height):
    lon = normalize_longitude(longitude)
    lat = _number(latitude, "latitude", -90, 90)
    height = _number(height, "ellipsoidal height", -12_000, 100_000)
    # All longitudes describe the same geographic point on the polar axis.
    return (0.0 if abs(lat) == 90 else lon), lat, height


def _ecef(lon, lat, height):
    la, lo = math.radians(lat), math.radians(lon)
    sl, cl = math.sin(la), math.cos(la)
    radius = _A / math.sqrt(1 - _E2 * sl * sl)
    return ((radius + height) * cl * math.cos(lo),
            (radius + height) * cl * math.sin(lo), (radius * (1 - _E2) + height) * sl)


def _rotation(lon, lat):
    la, lo = math.radians(lat), math.radians(lon)
    sl, cl, so, co = math.sin(la), math.cos(la), math.sin(lo), math.cos(lo)
    return ((-so, co, 0.), (-sl * co, -sl * so, cl), (cl * co, cl * so, sl))


def _from_ecef(x, y, z):
    p = math.hypot(x, y)
    if p < 1e-8:
        return 0., math.copysign(90., z), abs(z) - _B
    lon = math.degrees(math.atan2(y, x))
    lat = math.atan2(z, p * (1 - _E2))
    for _ in range(12):
        s = math.sin(lat)
        radius = _A / math.sqrt(1 - _E2 * s * s)
        new_lat = math.atan2(z + _E2 * radius * s, p)
        if abs(new_lat - lat) < 1e-15:
            lat = new_lat
            break
        lat = new_lat
    s, c = math.sin(lat), math.cos(lat)
    # Dot against the surface normal avoids division by cos(latitude) at poles.
    height = p * c + z * s - _A * math.sqrt(1 - _E2 * s * s)
    return normalize_longitude(lon), math.degrees(lat), height


@dataclass(frozen=True, slots=True)
class GeographicFrame:
    """Exact source ENU origin, including legacy nonzero ellipsoidal altitude.

    Coordinates retain float64 precision; this descriptor does not assert that
    its origin was selected by the canonical source-extent policy.
    """
    longitude: float
    latitude: float
    height: float = 0.0

    def __post_init__(self):
        # Preserve declared polar ENU orientation in original source frames.
        lon = normalize_longitude(self.longitude)
        lat = _number(self.latitude, "latitude", -90, 90)
        height = _number(self.height, "ellipsoidal height", -12_000, 100_000)
        object.__setattr__(self, "longitude", lon)
        object.__setattr__(self, "latitude", lat)
        object.__setattr__(self, "height", height)

    def to_dict(self):
        return {"type": "wgs84-enu-v1", "longitude": self.longitude,
                "latitude": self.latitude, "height": self.height,
                "horizontal_datum": HORIZONTAL_DATUM, "vertical_datum": VERTICAL_DATUM, "units": UNITS}

    @classmethod
    def from_dict(cls, data):
        _object(data, ("type", "longitude", "latitude", "height", "horizontal_datum", "vertical_datum", "units"))
        if (data["type"], data["horizontal_datum"], data["vertical_datum"], data["units"]) != (
                "wgs84-enu-v1", HORIZONTAL_DATUM, VERTICAL_DATUM, UNITS):
            raise ValueError("unsupported ENU frame convention")
        return cls(data["longitude"], data["latitude"], data["height"])

    def geodetic_to_enu(self, longitude, latitude, height=0.):
        lon, lat, h = _geographic(longitude, latitude, height)
        point = _ecef(lon, lat, h)
        origin = _ecef(self.longitude, self.latitude, self.height)
        delta = tuple(p - o for p, o in zip(point, origin))
        return tuple(sum(a * b for a, b in zip(row, delta))
                     for row in _rotation(self.longitude, self.latitude))

    def enu_to_geodetic(self, east, north, up=0.):
        point = tuple(_number(v, "ENU coordinate", -1_000_000, 1_000_000) for v in (east, north, up))
        origin = _ecef(self.longitude, self.latitude, self.height)
        rotation = _rotation(self.longitude, self.latitude)
        xyz = tuple(origin[i] + sum(rotation[j][i] * point[j] for j in range(3)) for i in range(3))
        lon, lat, height = _from_ecef(*xyz)
        return _geographic(lon, lat, height)


@dataclass(frozen=True, slots=True)
class CanonicalFrame:
    """Source-extent ENU anchor quantized to 1e-7 degree, at ellipsoid height 0."""
    longitude_e7: int
    latitude_e7: int

    def __post_init__(self):
        _integer(self.longitude_e7, "longitude_e7", -180 * ANGLE_SCALE, 180 * ANGLE_SCALE - 1)
        _integer(self.latitude_e7, "latitude_e7", -90 * ANGLE_SCALE, 90 * ANGLE_SCALE)
        if abs(self.latitude_e7) == 90 * ANGLE_SCALE and self.longitude_e7:
            raise ValueError("polar canonical anchor requires longitude zero")

    @classmethod
    def from_geographic_extent(cls, points):
        """Select from complete geographic extent, independent of vertex order.

        This selects an anchor only, not polygon validity, occupancy or topology.
        A source must be complete; clipped tile fragments are not eligible.
        """
        longitudes, latitudes = set(), []
        for i, point in enumerate(points):
            if i >= MAX_EXTENT_POINTS:
                raise ValueError("source extent exceeds point budget")
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("extent requires longitude/latitude pairs")
            lon, lat, _ = _geographic(*point, 0.)
            # Quantize before extent selection: wrap-equivalent float inputs
            # produce identical integer extrema and tie breaking.
            lat_i = _angle_e7(lat)
            # Quantize decimal source longitude before integer wrapping.
            lon_i = _angle_e7(float(point[0]))
            lon_i = (lon_i + 180 * ANGLE_SCALE) % (360 * ANGLE_SCALE) - 180 * ANGLE_SCALE
            if abs(lat_i) == 90 * ANGLE_SCALE:
                lon_i = 0
            longitudes.add(lon_i)
            latitudes.append(lat_i)
        if not latitudes:
            raise ValueError("source extent is empty")
        ordered = sorted(longitudes)
        turn = 360 * ANGLE_SCALE
        # Remove largest circular gap; tie choose lowest canonical starting lon.
        gaps = [((ordered[(i + 1) % len(ordered)] - value) % turn,
                 ordered[(i + 1) % len(ordered)]) for i, value in enumerate(ordered)]
        if len(ordered) == 1:
            span, start = 0, ordered[0]
        else:
            gap, start = min(gaps, key=lambda item: (-item[0], item[1]))
            span = turn - gap
        lat_low, lat_high = min(latitudes), max(latitudes)
        if span > MAX_EXTENT_DEGREES * ANGLE_SCALE or lat_high - lat_low > MAX_EXTENT_DEGREES * ANGLE_SCALE:
            raise ValueError("split source extents wider than one degree before canonical framing")
        # Integer midpoint uses round-to-even; no geometry coordinates are snapped.
        lon = round((start * 2 + span) / 2)
        lon = (lon + 180 * ANGLE_SCALE) % turn - 180 * ANGLE_SCALE
        lat = round((lat_low + lat_high) / 2)
        return cls(0 if abs(lat) == 90 * ANGLE_SCALE else lon, lat)

    def as_geographic_frame(self):
        return GeographicFrame(self.longitude_e7 / ANGLE_SCALE, self.latitude_e7 / ANGLE_SCALE)

    def geodetic_to_enu(self, longitude, latitude, height=0.):
        return self.as_geographic_frame().geodetic_to_enu(longitude, latitude, height)

    def enu_to_geodetic(self, east, north, up=0.):
        return self.as_geographic_frame().enu_to_geodetic(east, north, up)

    def to_dict(self):
        return {"type": "source-extent-enu-v1", "longitude_e7": self.longitude_e7,
                "latitude_e7": self.latitude_e7, "height": 0,
                "horizontal_datum": HORIZONTAL_DATUM, "vertical_datum": VERTICAL_DATUM,
                "units": UNITS, "anchor_precision_degrees": "0.0000001"}

    @classmethod
    def from_dict(cls, data):
        fields = ("type", "longitude_e7", "latitude_e7", "height", "horizontal_datum",
                  "vertical_datum", "units", "anchor_precision_degrees")
        _object(data, fields)
        frame = cls(data["longitude_e7"], data["latitude_e7"])
        if data != frame.to_dict() or type(data["height"]) is not int:
            raise ValueError("unsupported canonical frame convention")
        return frame

    @property
    def key(self):
        return "canonical-frame-v1:" + _digest(self.to_dict())

    def owner_cell(self, cell_size_e7=100_000):
        """Stable geographic descriptor owner; half-open 0.01 degree by default.

        This does not confer resource producer ownership or alter engine tiles.
        The north pole belongs to the last latitude row; +180 normalizes to -180.
        """
        size = _integer(cell_size_e7, "cell size", 1, 180 * ANGLE_SCALE)
        if 180 * ANGLE_SCALE % size:
            raise ValueError("cell size must divide 180 degrees exactly")
        x = (self.longitude_e7 + 180 * ANGLE_SCALE) // size
        y = min((self.latitude_e7 + 90 * ANGLE_SCALE) // size, 180 * ANGLE_SCALE // size - 1)
        return f"geographic-owner-v1:{size}:{x}:{y}"


def rebase_enu(point, source_frame, target_frame):
    """Reproject a scalar ENU point through WGS84, preserving all three axes."""
    if not isinstance(source_frame, (GeographicFrame, CanonicalFrame)) or not isinstance(
            target_frame, (GeographicFrame, CanonicalFrame)):
        raise ValueError("rebase requires declared geographic frames")
    if not isinstance(point, (tuple, list)) or len(point) != 3:
        raise ValueError("rebase requires an east/north/up triple")
    return target_frame.geodetic_to_enu(*source_frame.enu_to_geodetic(*point))
