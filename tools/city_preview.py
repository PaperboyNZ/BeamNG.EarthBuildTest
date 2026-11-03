"""Reproducible city geometry review; approximate colours, not game lighting."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen.context import Context
from buildgen.topology import Footprint
from building_preview import raster
from commercial_preview import mesh_hash

CASES = (
    ('Curtain office / New York', 'office', 'glass', 24, (40.73, -73.99)),
    ('Panel office / Helsinki', 'office', 'concrete', 16, (60.17, 24.94)),
    ('Masonry office / London', 'office', 'brick', 13, (51.51, -.12)),
    ('Contemporary hotel / Singapore', 'hotel', 'concrete', 12, (1.30, 103.84)),
    ('Masonry hotel / Paris', 'hotel', 'stone', 8, (48.86, 2.35)),
    ('Hotel / Christchurch', 'hotel', 'render', 6, (-43.53, 172.63)),
    ('Courtyard hotel / Mexico City', 'hotel', 'brick', 8, (19.43, -99.13)),
    ('Office / Dubai', 'office', 'glass', 30, (25.20, 55.27)),
    ('Existing low office control', 'office', 'brick', 3, (None, None)),
)


def fixture(index):
    label, cls, material, floors, location = CASES[index]
    fp = Footprint(((0, 0), (30, 0), (30, 24), (0, 24)),
                   (((10, 8), (20, 8), (20, 16), (10, 16)),) if index == 6 else ())
    attrs = dict(_footprint=fp, seed_id='city-review-'+str(index),
                 height=floors*3.4, num_floors=floors, roof_shape='flat', facade_material=material)
    attrs['class'] = cls
    if location[0] is not None:
        attrs['_context'] = Context(location=location)
    spec = b.plan(np.asarray(fp.outer), attrs)
    spec.gring = np.zeros(len(spec.ring))
    roads = [(np.array([(-40., -12.), (70., -12.)]), 3., 'residential', False)]
    props = b.doors([(spec, 0., 0.)], roads, 0., 0., ground=lambda xy: np.zeros(len(xy)))
    return spec, props


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=2)
    args = parser.parse_args()
    canvas = Image.new('RGB', (1500, 1350), '#e8edf0')
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('Arial.ttf', 17)
    except OSError:
        font = ImageFont.load_default(size=17)
    draw.text((18, 12), 'City building geometry / approximate materials / no native-game acceptance', font=font, fill='#203040')
    rows = []
    for index, case in enumerate(CASES):
        timings = []
        for _ in range(max(1, args.repeats)):
            start = time.perf_counter()
            spec, props = fixture(index)
            frozen = freeze_items([(spec, 0., 0.)])
            planned = time.perf_counter()
            near, lite, collision = b.build(frozen), b.build(frozen, lite=True), b.collision_mesh(frozen)
            timings.append(dict(plan_access_ms=(planned-start)*1000,
                                compile_ms=(time.perf_counter()-planned)*1000))
        x, y = (index % 3)*500, 50+(index//3)*430
        canvas.paste(raster(near, props, [], 500, 370, b), (x, y))
        draw.text((x+16, y+372), case[0], font=font, fill='#203040')
        draw.text((x+16, y+397), f'near {len(near[0]):,} / lite {len(lite[0]):,} vertices', font=font, fill='#405060')
        architecture = getattr(frozen[0][0], 'city', None)
        rows.append(dict(label=case[0], region=spec.inference.selection.environment.region,
                         city=asdict(architecture) if architecture else None,
                         meshes={name: dict(vertices=len(mesh[0]), triangles=len(mesh[2]), sha256=mesh_hash(mesh))
                                 for name, mesh in (('near',near), ('lite',lite), ('collision',collision))},
                         timing_samples=timings))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    sources = ['server/buildings.py', 'server/buildgen/facades.py', 'server/buildgen/compiler.py',
               'server/buildgen/plan.py', 'server/buildgen/city.py', 'server/buildgen/catalog/city_regions.json']
    report = dict(status='synthetic_geometry_not_game_acceptance', fixtures=rows,
                  source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                 for name in sources if (ROOT/name).exists()})
    args.out.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(args.out)


if __name__ == '__main__':
    main()
