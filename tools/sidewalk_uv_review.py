"""Sample actual generated UVs against installed game textures; offline, no engine-render claim."""
import argparse
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import time
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import sidewalks as fixed


def fixtures(sw):
    sys.modules['sidewalks'] = sw  # vehicle_crossings imports its profile constants at call time
    result = []
    for width, kwargs in [(1.2, {}), (4., {}), (2.5, {'verge': True, 'driveways': [(7., 10.)]}),
                          (2.5, {'ramps': [(7., 9.)]})]:
        b = sw.Builder((0, 0, 0), collision=True)
        b.add_run(np.array([[0., 0., 0.], [20., 0., 0.]]), np.tile([0., 1.], (2, 1)), width, **kwargs)
        result.append(b)
    b = sw.Builder((0, 0, 0), collision=True)
    t = np.linspace(0, np.pi / 2, 20)
    arc = np.c_[6 * np.cos(t), 6 * np.sin(t), np.zeros(len(t))]
    b.add_corner(arc, -arc[:, :2] / 6, [[0, 2.5, 0], [0, 0, 0], [2.5, 0, 0]])
    result.append(b)
    return result


def raster(mesh, textures, bounds, size=(830, 245)):
    P, T, UV, M = mesh
    width, height = size
    x0, y0, x1, y1 = bounds
    scale = min((width - 30) / (x1 - x0), (height - 30) / (y1 - y0))
    points = np.c_[15 + (P[:, 0] - x0) * scale, height - 15 - (P[:, 1] - y0) * scale]
    pixels = np.full((height, width, 3), [45, 57, 61], np.uint8)
    for tri, mat in zip(T, M):
        q = points[tri]
        a, b, c = q
        det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(det) < 1e-8:
            continue
        lo = np.maximum(np.floor(q.min(0)).astype(int), 0)
        hi = np.minimum(np.ceil(q.max(0)).astype(int), [width - 1, height - 1])
        xx, yy = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        dx, dy = xx + .5 - a[0], yy + .5 - a[1]
        v = (dx * (c[1] - a[1]) - dy * (c[0] - a[0])) / det
        w = ((b[0] - a[0]) * dy - (b[1] - a[1]) * dx) / det
        inside = (v >= -1e-8) & (w >= -1e-8) & (v + w <= 1 + 1e-8)
        uv = UV[tri[0]] + v[..., None] * (UV[tri[1]] - UV[tri[0]]) + w[..., None] * (UV[tri[2]] - UV[tri[0]])
        texture = textures[int(mat)]
        tx = np.floor((uv[..., 0] % 1) * texture.shape[1]).astype(int) % texture.shape[1]
        ty = np.floor(((1 - uv[..., 1]) % 1) * texture.shape[0]).astype(int) % texture.shape[0]
        pixels[yy[inside], xx[inside]] = texture[ty[inside], tx[inside]]
    return Image.fromarray(pixels)


def benchmark(sw):
    sys.modules['sidewalks'] = sw
    results = {}
    for enhanced in (False, True):
        timings = []
        for _ in range(9):
            start = time.perf_counter()
            b = sw.Builder((0, 0, 0), collision=True)
            for i in range(200):
                b.add_run(np.array([[0., i * 5., 0.], [100., i * 5., 0.]]), np.tile([0., 1.], (2, 1)), 2.5,
                          driveways=[(45., 51.)] if enhanced and i % 5 == 0 else (), verge=enhanced and i % 2 == 0)
            mesh, col = b.arrays(), b.col.arrays()
            timings.append((time.perf_counter() - start) * 1000)
        results['mixed' if enhanced else 'plain'] = dict(median_ms=round(float(np.median(timings[2:])), 3),
            vertices=len(mesh[0]), triangles=len(mesh[1]), collision_triangles=len(col[1]))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True, help='Unmodified server/sidewalks.py')
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/sidewalk-uv')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('sidewalks_before', args.baseline)
    before = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(before)
    base_meshes = [(b.arrays(), b.col.arrays()) for b in fixtures(before)]
    new_meshes = [(b.arrays(), b.col.arrays()) for b in fixtures(fixed)]
    for (old, old_col), (new, new_col) in zip(base_meshes, new_meshes):
        base = new[3] != 5
        np.testing.assert_array_equal(old[0][old[1]], new[0][new[1][base]])
        np.testing.assert_array_equal(old[3], new[3][base])
        np.testing.assert_array_equal(old[2][old[1][old[3] == 0]], new[2][new[1][new[3] == 0]])
        for a, b in zip(old_col, new_col):
            np.testing.assert_array_equal(a, b)
    def texture(archive, tail):
        with ZipFile(args.game / 'content/assets/materials' / (archive + '.zip')) as z:
            return np.asarray(Image.open(BytesIO(z.read('assets/materials/' + archive + '/' + tail))).convert('RGB'))
    curb = texture('trim', 'concrete/curbs/t_curbs_b.color.dds')
    slab = texture('tileable', 'concrete/slabs_large/t_slabs_large_b.color.dds')
    atlas = texture('tileable', 'concrete/sidewalk1/t_sidewalk1_b.color.dds')
    tactile = texture('tileable', 'tile/tactile_indicator/t_tactile_indicator_b.color.dds')
    grass = np.full((16, 16, 3), [95, 126, 71], np.uint8)
    brick = np.full((16, 16, 3), [160, 106, 82], np.uint8)
    image = Image.new('RGB', (1740, 1570), '#17252d')
    draw = ImageDraw.Draw(image)
    font_path = 'C:/Windows/Fonts/segoeui.ttf'
    def font(n):
        return ImageFont.truetype(font_path, n) if Path(font_path).exists() else ImageFont.load_default(size=n)
    draw.text((25, 15), 'Sidewalk UV mapping: actual mesh + stock albedo textures', font=font(27), fill='white')
    draw.text((25, 53), 'Offline top-down texture sampling; grass shown as green. No lighting or normal maps. Not an in-game render.',
              font=font(17), fill='#a6bfcd')
    draw.text((25, 88), 'BEFORE', font=font(22), fill='#ebc9ae')
    draw.text((895, 88), 'FIXED: 2 m square paving panels', font=font(22), fill='#addec2')
    labels = ['Narrow sidewalk (1.2 m)', 'Wide sidewalk (4 m)', 'Verge + vehicle crossing',
              'Pedestrian ramp + tactile transition', 'Curved junction corner']
    for i, ((old, _), (new, _)) in enumerate(zip(base_meshes, new_meshes)):
        y = 125 + i * 285
        bounds = (-.5, -.5, 20.5, 5.) if i < 4 else (-.5, -.5, 6.5, 6.5)
        for x, mesh, top in [(25, old, atlas), (895, new, slab)]:
            draw.text((x, y), labels[i], font=font(18), fill='white')
            image.paste(raster(mesh, [curb, top, tactile, brick, grass, atlas], bounds), (x, y + 28))
    image.save(args.out / 'comparison.png')
    report = {'base_geometry_identical': True, 'collision_identical': True, 'curb_uvs_identical': True,
              'utility_patches': [int(np.count_nonzero(v[0][3] == 5) // 2) for v in new_meshes], 'fixtures': len(labels),
              'before': benchmark(before), 'fixed': benchmark(fixed),
              'scope': 'Offline UV/geometry/export verification; native game acceptance pending'}
    (args.out / 'review.json').write_text(json.dumps(report, indent=2))
    sys.modules['sidewalks'] = fixed
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
