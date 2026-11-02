"""Offline baseline for the integrated overhaul; no map downloads or game claims.

Run in a fresh process for each baseline. First-pass timings include lazy work;
warm samples follow one full pass and exclude preview rendering and source hashing.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np
import shapely

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import buildings as b
import codefiles
from buildgen import freeze_items
from buildgen.diagnostics import DrivewayAudit
from buildgen.evidence import ATTRIBUTE_FIELDS
from buildgen.plan import SCHEMA_VERSION
from buildgen.topology import Footprint


ARCHITECTURE = (
    ('workshop', dict(cls='workshop', height=6., floors=1, material='metal')),
    ('retail', dict(cls='retail', height=6., floors=1, material='brick')),
    ('supermarket', dict(cls='supermarket', height=6., floors=1, material='concrete')),
    ('office_brick', dict(cls='office', height=12., floors=3, material='brick')),
    ('office_concrete', dict(cls='office', height=12., floors=3, material='concrete')),
    ('office_glass', dict(cls='office', height=12., floors=3, material='glass')),
    ('chapel', dict(cls='chapel', height=7., floors=1, material='wood')),
    ('church', dict(cls='church', height=11., floors=1, material='brick')),
    ('terminal', dict(cls='transportation', name='Passenger Terminal', height=13., floors=2)),
    ('garage', dict(cls='parking', height=12., floors=4, width=48., depth=30.)),
    ('terminal_hotel_false_positive', dict(cls='hotel', name='Terminal Hotel', height=12., floors=3)),
    ('freight_terminal', dict(cls='warehouse', name='Freight Terminal', height=9., floors=1)),
)


def building(cls='house', width=12., depth=10., height=None, floors=1,
             material=None, name=None, seed='house'):
    fp = Footprint(((0., 0.), (width, 0.), (width, depth), (0., depth)))
    attrs = dict(_footprint=fp, seed_id=seed, **{'class': cls, 'num_floors': floors})
    for key, value in (('height', height), ('facade_material', material), ('name', name)):
        if value is not None:
            attrs[key] = value
    spec = b.plan(np.asarray(fp.outer), attrs)
    spec.gring = np.zeros(len(spec.ring))
    return spec


def road(offset=(0., 0.)):
    return [(np.array([(-50., -12.), (100., -12.)]) + offset, 3., 'residential', False)]


def walk(width=2.5, offset=(0., 0.)):
    xy = np.array([(-50., -9. + width / 2), (50., -9. + width / 2)]) + offset
    return dict(pts=np.c_[xy, np.zeros(2)], side=1, w=width, caps=(True, True))


def fingerprint(mesh):
    if mesh is None:
        return None
    digest = hashlib.sha256()
    for value in mesh:
        if isinstance(value, np.ndarray):
            digest.update(str((value.dtype.str, value.shape)).encode())
            digest.update(value.tobytes())
        else:
            digest.update(json.dumps(value, sort_keys=True).encode())
    return digest.hexdigest()


def mesh_stats(mesh):
    if mesh is None:
        return dict(vertices=0, triangles=0, materials=0, array_bytes=0, sha256=None)
    return dict(vertices=len(mesh[0]), triangles=len(mesh[2]),
                materials=len(set(map(int, mesh[3]))),
                array_bytes=sum(v.nbytes for v in mesh if isinstance(v, np.ndarray)),
                sha256=fingerprint(mesh))


def compile_case(label, values):
    start = time.perf_counter()
    spec = building(width=30., depth=20., **values) if 'width' not in values else building(**values)
    props = b.doors([(spec, 0., 0.)], road(), 0., 0., ground=lambda p: np.zeros(len(p)))
    planned = time.perf_counter()
    items = freeze_items([(spec, 0., 0.)])
    frozen = time.perf_counter()
    near = b.build(items)
    near_done = time.perf_counter()
    lite = b.build(items, lite=True)
    lite_done = time.perf_counter()
    collision = b.collision_mesh(items)
    end = time.perf_counter()
    timing = dict(plan_access_ms=(planned-start)*1000, freeze_ms=(frozen-planned)*1000,
                  near_ms=(near_done-frozen)*1000, lite_ms=(lite_done-near_done)*1000,
                  collision_mesh_ms=(end-lite_done)*1000)
    result = dict(id=label, input=values,
                  dispatch='v2' if spec.inference is not None else 'legacy_specialist',
                  preset=spec.inference.selection.preset.id if spec.inference else None,
                  diagnostics=list(spec.diagnostics), floors=spec.floors, body_height=spec.height,
                  roof=spec.roof, steeple=bool(spec.steeple),
                  playable_deck_plan=b.deck_plan(spec, 0., 0.) is not None,
                  near=mesh_stats(near), lite=mesh_stats(lite), collision=mesh_stats(collision))
    return result, timing, near, props


def access_case(name, *, audit_enabled=True, offset=(0., 0.)):
    audit = DrivewayAudit() if audit_enabled else None
    spec = building(width=6. if name == 'no_garage' else 12.)
    items = [(spec, 0., 0.)]
    # Keep the rejected fixture below the supported 1.5 m crossing minimum.
    walks = [] if name == 'no_footpath' else [walk(1.4 if name == 'narrow' else 2.5, offset)]
    if name == 'pedestrian_ramp':
        walks[0]['ramps'] = [(48., 60.)]
    if name == 'obstructed':
        obstacle = building()
        fp = Footprint(((0., -5.), (14., -5.), (14., -3.), (0., -3.)))
        obstacle.ring = np.asarray(fp.outer)
        obstacle.footprint = fp
        items.append((obstacle, 0., 0.))
    calls = []

    def terrain(points):
        calls.append(len(points))
        local = points - offset
        if name == 'missing_terrain':
            return np.full(len(points), np.nan)
        if name == 'steep':
            return -local[:, 1] * .5
        return np.zeros(len(points))

    drives = []
    b.doors(items, [] if name == 'no_roads' else road(offset), *offset,
            drives, ground=terrain, walks=walks, driveway_audit=audit)
    meshes = freeze_items(items)
    return dict(id=name, audit=audit.snapshot() if audit else None,
                terrain_calls=len(calls), terrain_points=sum(calls),
                access_diagnostics=[list(s.access.diagnostics) if s.access else [] for s,_,_ in items],
                near_sha256=fingerprint(b.build(meshes)),
                collision_sha256=fingerprint(b.collision_mesh(meshes)),
                emitted_crossings=sum(len(w.get('driveways', ())) for w in walks),
                drive_records=len(drives))


def source_manifest():
    files = codefiles.source_files(ROOT / 'server')
    files = [('server/' + f) for f in files] + ['tools/generation_baseline.py', 'tools/building_preview.py']
    hashes = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}
    return dict(sha256=hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), files=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/overhaul-baseline/generation.json')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100:
        parser.error('--repeats must be between 1 and 100')
    # Make the synthetic baseline independent of user site/path switches, while
    # retaining other environment inputs explicitly in the report.
    os.environ['BNE_BUILDING_GENERATOR'] = 'v2'
    os.environ['BNE_BUILDING_PATHS'] = 'auto'
    os.environ.pop('BNE_BUILDING_SITES', None)
    rows, first, previews, samples = [], {}, [], {}
    for label, values in ARCHITECTURE:
        row, timing, mesh, props = compile_case(label, values)
        rows.append(row)
        first[label] = timing
        if args.preview:
            from building_preview import raster
            previews.append((label, raster(mesh, props, [], 460, 290, b)))
    for _ in range(args.repeats):
        for label, values in ARCHITECTURE:
            _, timing, _, _ = compile_case(label, values)
            samples.setdefault(label, []).append(timing)
    timing = {label: {stage: dict(p50_ms=float(np.percentile([v[stage] for v in runs], 50)),
                                 p95_ms=float(np.percentile([v[stage] for v in runs], 95)),
                                 p99_ms=float(np.percentile([v[stage] for v in runs], 99)),
                                 max_ms=max(v[stage] for v in runs))
                      for stage in runs[0]} for label, runs in samples.items()}
    access = [access_case(name) for name in ('connected', 'no_footpath', 'no_garage', 'narrow',
               'pedestrian_ramp', 'obstructed', 'missing_terrain', 'steep', 'no_roads')]
    report = dict(schema_version=1, status='synthetic_baseline_not_game_acceptance',
        building_schema=SCHEMA_VERSION, source=source_manifest(),
        runtime=dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                     processor=platform.processor(), numpy=np.__version__, shapely=shapely.__version__,
                     geos=shapely.geos_version_string,
                     environment={k:v for k,v in os.environ.items() if k.startswith('BNE_BUILDING_')}),
        methodology=dict(first_pass='fresh process, sequential fixtures share lazy module caches; not cold I/O',
                         warm_repeats=args.repeats, samples_per_fixture=args.repeats,
                         excluded=['map/terrain I/O', 'serialization/delivery', 'engine import/deferred cost',
                                   'collision activation', 'frame time', 'memory residency', 'refuel gameplay']),
        first_pass_ms=first, warm=timing, warm_samples_ms=samples, architecture=rows, access=access,
        selection_counts=dict(Counter(row['preset'] or row['dispatch'] for row in rows)),
        retained_evidence_fields=list(ATTRIBUTE_FIELDS),
        ownership=dict(model='one_owner_per_surveyed_site', shared_complexes=False,
                       mapped_parking='separate pipeline', fuel='separate station identity/props/triggers'),
        limitations=['Office compositions are authored style priors; observed construction era remains unknown.',
                     'Keyword controls exercise conservative routing, not measured worldwide classification accuracy.',
                     'Fuel layouts/refuelling and real-map coverage require separate tests and game captures.',
                     'Crossing-only feasibility is not evaluated by the current resolver.',
                     'Small repeated fixtures cannot establish performance percentiles for real routes.'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    if previews:
        from PIL import Image, ImageDraw, ImageFont
        canvas = Image.new('RGB', (1380, 1390), (232, 237, 240))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=16)
        draw.text((18, 15), 'Current generator baseline / synthetic meshes / approximate colours / no game acceptance',
                  fill=(30, 45, 55), font=font)
        for i, (label, preview) in enumerate(previews):
            x, y = (i % 3) * 460, 50 + (i // 3) * 330
            canvas.paste(preview, (x, y))
            draw.text((x+12, y+293), label.replace('_', ' '), fill=(30, 45, 55), font=font)
        canvas.save(args.out.with_suffix('.png'))
    print(json.dumps(dict(report=str(args.out), architecture=len(rows), access=len(access),
                          source_sha256=report['source']['sha256']), indent=2))


if __name__ == '__main__':
    main()
