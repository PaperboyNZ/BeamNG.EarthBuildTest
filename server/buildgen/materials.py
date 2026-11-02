"""Bounded material priors and surface scales for the v2 facade compiler.

These are explicitly fallback construction choices, never mapped observations.
They use the existing game material library; no new proprietary assets are copied.
"""
import hashlib


def unit(identity, channel):
    return int.from_bytes(hashlib.blake2b(repr((identity, channel)).encode(), digest_size=8).digest(), "little") / 2**64


def choose(identity, channel, options):
    u = unit(identity, channel) * sum(w for _, w in options)
    for value, weight in options:
        u -= weight
        if u < 0:
            return value
    return options[-1][0]


def garage_colour(seed):
    """Existing seeded garage paint shared by Full and compact shutters."""
    return choose(seed, "garage-paint", (((.86, .87, .84), 4), ((.35, .38, .39), 3),
                                        ((.52, .44, .36), 2), ((.52, .21, .16), 1)))


def facade_prior(use, cls, floors, identity):
    if use == "industrial":
        options = (("metal", 7), ("concrete", 2), ("brick", 1))
    elif use in ("agricultural", "ancillary"):
        options = (("wood", 4), ("metal", 4), ("render", 2))
    elif cls == "office" and floors >= 5:
        options = (("glass", 5), ("concrete", 2), ("brick", 2), ("render", 1))
    elif floors >= 4:
        options = (("brick", 4), ("render", 3), ("concrete", 3))
    elif use in ("commercial", "civic", "mixed"):
        options = (("brick", 4), ("render", 4), ("concrete", 2))
    else:
        options = (("render", 4), ("brick", 3), ("wood", 3))
    return choose(identity, "facade-construction-v1", options)


def roof_prior(use, roof, identity):
    if roof == "flat":
        return "membrane"
    if use in ("industrial", "agricultural", "ancillary"):
        return "metal"
    return choose(identity, "roof-covering-v1", (("metal", 3), ("slate", 3), ("tile", 2), ("shingle", 2)))


# Neutral and restrained paint colours; trim/glass do not inherit the wall tint.
RENDER_COLOURS = ((.96, .96, .93), (.82, .83, .82), (.64, .67, .69), (.92, .86, .75),
                  (.74, .79, .80), (.76, .81, .72), (.83, .73, .68), (.92, .91, .84))
WOOD_COLOURS = ((.96, .95, .90), (.78, .81, .81), (.52, .60, .66), (.57, .64, .56),
                (.80, .74, .64), (.91, .87, .77), (.45, .48, .49), (.72, .80, .84))
CONCRETE_COLOURS = ((.88, .88, .86), (.72, .75, .76), (.88, .84, .76), (.64, .66, .67))
METAL_COLOURS = ((.82, .84, .85), (.52, .56, .59), (.69, .72, .67), (.80, .78, .71))


def colour(identity, family):
    colours = {"render": RENDER_COLOURS, "wood": WOOD_COLOURS,
               "concrete": CONCRETE_COLOURS, "metal": METAL_COLOURS}.get(family)
    return colours[min(int(unit(identity, "wall-paint-v1") * len(colours)), len(colours) - 1)] if colours else None


def wall_scale(family):
    """Metres per texture repeat, using the existing tileable material recipes."""
    return (2.4, 2.4) if family in ("brick", "stone") else (3., 3.)


def roof_scale(family):
    """Metres per repeat for the current stock assets; game calibration ongoing.

    One universal six-metre repeat made the zinc cladding read as giant panels.
    Keep these physical sizes independent of roof span, pitch and triangulation.
    """
    size = {"metal": 1.2, "copper": 1.2, "tile": 2.4, "slate": 2.4, "shingle": 3., "thatch": 1.8}.get(family, 6.)
    return size, size
