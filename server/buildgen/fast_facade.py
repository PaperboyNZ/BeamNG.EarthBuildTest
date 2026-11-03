"""Numeric facade inputs shared by inexpensive presentation compilers.

Coordinates in reservations are metres along an elevation and absolute Z in
the accepted plan's frame.  No detailed opening objects or facade planner are
constructed here.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Reservation:
    left: float
    right: float
    bottom: float
    top: float


def reservations(spec, boundary, edge, base, gmax):
    """Return conservative clearances for accepted door and garage anchors."""
    result = []
    if boundary == 0 and spec.door and edge == spec.door[0]:
        z = spec.access.door_z if spec.access else gmax
        result.append(Reservation(spec.door[1] - .85, spec.door[1] + .85, z, z + 2.4))
    if boundary == 0 and spec.garage_opening and edge == spec.garage_opening[0]:
        _, centre, width, height = spec.garage_opening
        z = spec.access.garage_z if spec.access and spec.access.garage_z is not None else base
        result.append(Reservation(centre - width / 2 - .2, centre + width / 2 + .2, z, z + height + .2))
    return tuple(result)


def window_mask(left, right, bottom, height, top, reserved):
    """Select windows under the roof and outside every reserved rectangle."""
    keep = np.asarray(bottom + height <= top - .15, dtype=bool)
    for r in reserved:
        keep &= ~((left < r.right) & (right > r.left) &
                  (bottom < r.top) & (bottom + height > r.bottom))
    return keep
