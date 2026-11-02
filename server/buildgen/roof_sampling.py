"""Offline roof-colour experiment; no runtime changes or network requests.

Sampling is in source XYZ pixel coordinates, with pixel-centre containment,
polygon holes, an inward margin, bounded sample count, and conservative quality
flags. RGB is observed appearance, not an estimate of intrinsic material albedo.
The thresholds are experiment settings, not validated classification guarantees.
"""
from collections import OrderedDict
from pathlib import Path
import math
import hashlib
import io
import time
import numpy as np
from PIL import Image
from shapely import contains_xy, prepare


def mercator_pixels(lonlat, zoom):
    ll = np.asarray(lonlat, dtype=float)
    lat = np.radians(np.clip(ll[:, 1], -85.05112878, 85.05112878))
    scale = 256 * 2 ** zoom
    return np.column_stack(((ll[:, 0] + 180) / 360 * scale,
                            (1 - np.arcsinh(np.tan(lat)) / np.pi) / 2 * scale))


def lab(rgb):
    """sRGB D65 to CIELAB; Euclidean distance is Delta E 1976, not CIEDE2000."""
    c = np.asarray(rgb, dtype=float) / 255
    c = np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    xyz = c @ np.array([[.4124564, .2126729, .0193339],
                        [.3575761, .7151522, .1191920],
                        [.1804375, .0721750, .9503041]])
    xyz /= np.array([.95047, 1., 1.08883])
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d ** 2) + 4 / 29)
    return np.stack((116*f[..., 1]-16, 500*(f[..., 0]-f[..., 1]),
                     200*(f[..., 1]-f[..., 2])), axis=-1)


class CachedTiles:
    """Read existing raw image tiles only. Bounded decoded LRU, no fetching."""
    def __init__(self, root, capacity=512):
        self.root = Path(root)
        self.capacity = capacity
        self.decoded = OrderedDict()
        self.decode_ms = []
        self.digests = {}
        self.used = set()

    def path(self, source, zoom, x, y):
        return self.root/source/str(zoom)/str(x)/f'{y}.jpg'

    def get(self, source, zoom, x, y):
        key = (source, zoom, x, y)
        self.used.add(key)
        if key in self.decoded:
            self.decoded.move_to_end(key)
            return self.decoded[key]
        t = time.perf_counter()
        raw = self.path(*key).read_bytes()
        with Image.open(io.BytesIO(raw)) as im:
            a = np.array(im.convert('RGB'))
        if a.shape != (256, 256, 3):
            raise ValueError('not a 256px XYZ tile')
        if np.max(np.ptp(a.astype(np.int16), axis=(0, 1))) <= 2:
            raise ValueError('uniform source tile')
        self.digests[key] = hashlib.sha256(raw).hexdigest()
        self.decode_ms.append((time.perf_counter()-t)*1000)
        self.decoded[key] = a
        if len(self.decoded) > self.capacity:
            self.decoded.popitem(last=False)
        return a

    def pixels(self, source, zoom, x, y):
        tx, ty = x//256, y//256
        keys = np.column_stack((tx, ty))
        out = np.empty((len(x), 3), np.uint8)
        for a, b in np.unique(keys, axis=0):
            m = (tx == a) & (ty == b)
            out[m] = self.get(source, zoom, int(a), int(b))[y[m] % 256, x[m] % 256]
        return out


def sample(polygon, metres_per_pixel, tiles, source, zoom):
    """Return diagnostic evidence even on rejection; never use rejected RGB."""
    if metres_per_pixel > 2:
        return {'status': 'coarse_imagery'}
    if not polygon.is_valid or polygon.is_empty:
        return {'status': 'invalid_footprint'}
    inner = polygon.buffer(-max(1/metres_per_pixel, 1.25))
    if inner.is_empty:
        return {'status': 'no_interior'}
    x0, y0, x1, y1 = inner.bounds
    width, height = max(1, math.ceil(x1)-math.floor(x0)), max(1, math.ceil(y1)-math.floor(y0))
    sx, sy = max(1, math.ceil(width/64)), max(1, math.ceil(height/64))
    x, y = np.meshgrid(np.arange(math.floor(x0), math.ceil(x1), sx, dtype=np.int64),
                       np.arange(math.floor(y0), math.ceil(y1), sy, dtype=np.int64))
    prepare(inner)
    mask = contains_xy(inner, x+.5, y+.5)
    x, y = x[mask], y[mask]
    if len(x) < 24:
        return {'status': 'too_few_pixels', 'pixels': len(x)}
    try:
        rgb = tiles.pixels(source, zoom, x, y).astype(float)
    except (OSError, ValueError):
        return {'status': 'missing_tile'}
    luma = rgb @ np.array([.2126, .7152, .0722])
    green = (rgb[:, 1] > rgb[:, 0]*1.15+8) & (rgb[:, 1] > rgb[:, 2]*1.10+8)
    valid = (luma >= 25) & (rgb.min(axis=1) < 250) & ~green
    if valid.sum() < 24 or valid.mean() < .6:
        return {'status': 'shadow_vegetation_or_nodata', 'pixels': len(x),
                'usable_share': float(valid.mean())}
    # Trim darkest/brightest tails, retaining the middle of the observed roof.
    lo, hi = np.percentile(luma[valid], [20, 90])
    keep = valid & (luma >= lo) & (luma <= hi)
    colour = np.median(rgb[keep], axis=0)
    spread = float(np.percentile(np.linalg.norm(lab(rgb[valid])-lab(colour), axis=1), 80))
    return {'status': 'accepted' if spread <= 25 else 'mixed_colour',
            'rgb': colour.tolist(), 'pixels': len(x), 'usable_share': float(valid.mean()),
            'spread_de76_p80': spread}
