"""Reproducible CPU and exact-vertex-sharing study; no native-game FPS claims.

Run from the source checkout. Baseline encoder is the saved pre-change cdae.py.
The vertex sharing experiment is analysis only and does not change shape files.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'server'), str(ROOT/'server/tests')]
import buildings as b
import cdae
from buildgen import facades, freeze_items, regional_architecture, regional_blocks
from test_buildgen_wall_sweep import reference_cells
from test_buildgen_facades import building as house
from test_buildgen_regions import building as regional_house
from test_buildgen_regional_blocks import building as block, variants
from test_buildgen_city import make as city
from test_buildgen_churches import make as church


def encode(module, mesh):
    p, uv, t, tm, mats, colors = mesh[:6]
    return module.encode(p, t, uvs=uv, material=mats, tri_materials=tm,
                         colors=colors, object_name='buildings')


def sharing(data):
    """Byte-exact GPU attributes; do not weld across shading or texture seams."""
    m = cdae.decode(data)['meshes'][0]
    n = m['verts'][0]
    fields = [k for k in ('verts', 'tverts', 'tverts2', 'colors', 'norms', 'tangents') if m[k][0]]
    start = time.perf_counter()
    rows = np.concatenate([np.frombuffer(m[k][2], np.uint8).reshape(n, -1) for k in fields], axis=1)
    _, first, inverse = np.unique(rows.view('V'+str(rows.shape[1])).ravel(),
                                  return_index=True, return_inverse=True)
    # Keep first-use order; compare every original triangle corner, not just positions.
    order = np.argsort(first)
    first = first[order]
    remap = np.empty(len(order), np.int64)
    remap[order] = np.arange(len(order))
    indices = np.frombuffer(m['indices'][2], '<u4')
    compact_indices = remap[inverse[indices]]
    elapsed = (time.perf_counter()-start)*1000
    np.testing.assert_array_equal(rows[first][compact_indices], rows[indices])
    saved = (n-len(first))*rows.shape[1]
    return dict(vertices=n, unique_vertices=len(first), vertex_reduction_pct=100*(1-len(first)/n),
                attribute_bytes_saved=saved, shape_bytes=len(data),
                shape_payload_reduction_pct=100*saved/len(data), analysis_ms=elapsed,
                triangle_corner_attributes_identical=True)


def paired(functions, repeats):
    samples = [[], []]
    for i in range(repeats+1):
        for k in ((0, 1) if i % 2 else (1, 0)):
            start = time.perf_counter()
            functions[k]()
            elapsed = (time.perf_counter()-start)*1000
            if i:
                samples[k].append(elapsed)
    old, new = map(statistics.median, samples)
    return dict(baseline_ms=old, optimized_ms=new, improvement_pct=100*(1-new/old),
                baseline_samples_ms=samples[0], optimized_samples_ms=samples[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=9)
    parser.add_argument('--all-regions', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'build/geometry-costs/benchmark.json')
    args = parser.parse_args()
    baseline_path = ROOT/'build/geometry-costs/original/cdae.py'
    loader = importlib.util.spec_from_file_location('baseline_cdae', baseline_path)
    old_cdae = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(old_cdae)
    specimens = [('house', house()), ('regional_block_6', block()),
                 ('regional_block_48', block(floors=48)), ('fallback_apartment_49', block(floors=49)),
                 ('office_16', city()[0]), ('glass_tower_80', city(material='glass', floors=80)[0]),
                 ('church', church()[0])]
    current_cells = facades.wall_cells
    result = dict(notes='Synthetic single-building near+lite compilation and in-memory encoding. '
                       'Alternating baseline/optimized runs, one warmup, median of repeats. '
                       'Planning, downloads, disk writes, cache misses, game import and rendering excluded. '
                       'Vertex sharing is an offline experiment; it is not enabled in production.',
                  repeats=args.repeats, fixtures=[], sources={})
    for name in ('server/buildgen/facades.py', 'server/cdae.py', 'server/buildings.py', 'server/buildgen/plan.py'):
        result['sources'][name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for name, spec in specimens:
        items = freeze_items([(spec, 0., 0.)])
        def generate(fn):
            with patch.object(facades, 'wall_cells', fn):
                return [b.build(items, lite=lite) for lite in (False, True)]
        previous, current = generate(reference_cells), generate(current_cells)
        for old, new in zip(previous, current):
            for field in (0, 1, 2, 3, 5):
                np.testing.assert_array_equal(old[field], new[field])
            assert old[4] == new[4]
            assert encode(old_cdae, old) == encode(cdae, new)
        geometry = paired([lambda: generate(reference_cells), lambda: generate(current_cells)], args.repeats)
        encoding = paired([lambda: [encode(old_cdae, m) for m in current],
                           lambda: [encode(cdae, m) for m in current]], args.repeats)
        row = dict(name=name, generation=geometry, encoding=encoding,
                   meshes_and_encoded_bytes_identical=True,
                   exact_vertex_sharing=sharing(encode(cdae, current[0])))
        result['fixtures'].append(row)
        print(name, 'generation', round(geometry['improvement_pct'], 1), '%; encoding',
              round(encoding['improvement_pct'], 1), '%', flush=True)
    if args.all_regions:
        checked = 0
        for spec in [regional_house(k) for k in regional_architecture.catalogue()] + [
                s for k in regional_blocks.catalogue() for s in variants(k)]:
            items = freeze_items([(spec, 0., 0.)])
            for lite in (False, True):
                new = b.build(items, lite=lite)
                with patch.object(facades, 'wall_cells', reference_cells):
                    old = b.build(items, lite=lite)
                for field in (0, 1, 2, 3, 5):
                    np.testing.assert_array_equal(old[field], new[field])
                assert old[4] == new[4]
                assert encode(old_cdae, old) == encode(cdae, new)
                checked += 1
        result['regional_mesh_and_binary_equivalence_count'] = checked
        print('Regional mesh + encoded-byte equivalence:', checked, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()
