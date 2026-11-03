"""Reproducible regional/clearance audit and stock-texture sidewalk gallery."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
import time
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'server'), str(ROOT / 'server/tests'), str(ROOT / 'tools')]
import geodesy
import islands
import roads
import sidewalks as sw
import streetscape as sc
from sidewalk_uv_review import raster


def regional_audit():
    profiles = json.loads((ROOT / 'server/buildgen/catalog/regional_profiles.json').read_text())['profiles']
    result = []
    for theme, profile in profiles.items():
        e = profile['example']
        walk = dict(pts=np.array([[0., 0., 0.], [20., 0., 0.]]), fid=theme, w=2.5, side=1)
        sc.annotate([walk], geodesy.EnuFrame(e['lat'], e['lon']),
                    source_locations={theme: (e['lat'], e['lon'])}, road_classes={theme: 'residential'})
        assert walk['curb_style'] == sc.THEMES[theme], theme
        result.append(dict(theme=theme, style=walk['curb_style'], pavement=walk['pavement'], verge=walk['verge']))
    return result


def island_audit():
    results = []
    for radius, width, entry_width in ((12., 5.5, 9.), (16., 5.5, 9.), (22., 9.8, 14.)):
        t = np.linspace(0, 2 * np.pi, 65)
        poly = np.c_[radius * np.cos(t), radius * np.sin(t)]
        loop = (poly, width / 2)
        entry = (np.array([[radius, 0.], [radius + 40, 0.]]), entry_width / 2)
        ring = islands._island_ring(poly[:-1], [loop], 0., carriageways=[loop, entry])
        assert ring is not None
        band = roads.offset_polyline(np.vstack([ring[-1:], ring, ring[:2]]), islands.ISLAND_BAND_M / 2)[1:-1]
        curb, out = sw.run_geometry(band, 1, islands.ISLAND_BAND_M)
        lanes = unary_union([LineString(p).buffer(hw - .02, cap_style=2, join_style=2) for p, hw in (loop, entry)])
        # Check the actual swept slab footprint after both offsets, not just
        # the proposed ray hits that precede island smoothing.
        footprint = Polygon(np.vstack((curb[:, :2], (curb[:, :2] + out * islands.ISLAND_BAND_M)[::-1]))).buffer(0)
        overlap = footprint.intersection(lanes).area
        assert overlap < 1e-8, overlap
        results.append(dict(radius=radius, circulating_width=width, entry_width=entry_width, lane_overlap_m2=overlap))
    return results


def tile_benchmark():
    from test_roads import FRAME, features, flat
    f = features([[(x, y) for x in (-50, 50, 128, 206, 310)] for y in (50, 128, 206)] +
                 [[(x, y) for y in (-50, 50, 128, 206, 310)] for x in (50, 128, 206)], ['residential'] * 6)
    elapsed = []
    for _ in range(5):
        walks = []
        start = time.perf_counter()
        roads.build_tile(FRAME, 0, 0, [f], flat, lambda la, lo: np.ones(np.shape(la), bool), walks=walks)
        elapsed.append((time.perf_counter() - start) * 1000)
    ends = np.concatenate([sw.run_geometry(w['pts'], w['side'], w['w'])[0][[0, -1]]
                           for w in walks if 'pts' in w])
    gaps = [np.linalg.norm(ends[:, :2] - point[:2], axis=1).min()
            for w in walks if 'corner' in w for point in w['corner']['arc'][[0, -1]]]
    assert len(gaps) == 72 and max(gaps) < 1e-6
    return dict(median_ms=round(float(np.median(elapsed[1:])), 2), source_roads=6,
                walk_pieces=len(walks), corners=sum('corner' in w for w in walks),
                checked_corner_joins=len(gaps), max_corner_join_gap_m=max(gaps),
                scope='Offline flat six-road / nine-junction tile, no game FPS inference')


def gallery(game, out):
    def texture(archive, tail):
        with ZipFile(game / 'content/assets/materials' / (archive + '.zip')) as z:
            return np.asarray(Image.open(BytesIO(z.read('assets/materials/' + archive + '/' + tail))).convert('RGB'))
    textures = [texture('trim', 'concrete/curbs/t_curbs_b.color.dds'),
                texture('tileable', 'concrete/slabs_large/t_slabs_large_b.color.dds'),
                texture('tileable', 'tile/tactile_indicator/t_tactile_indicator_b.color.dds'),
                texture('tileable', 'brick/brick_herringbone/t_brick_herringbone_b.color.dds'),
                np.full((8, 8, 3), [95, 126, 71], np.uint8),
                texture('tileable', 'concrete/sidewalk1/t_sidewalk1_b.color.dds'),
                texture('tileable', 'tile/t_italy_sidewalk_tiles/t_italy_sidewalk_tiles_b.color.dds')]
    cases = [('New York', 40.7, -74.), ('Auckland', -36.85, 174.76), ('London', 51.5, -.12),
             ('Amsterdam', 52.37, 4.9), ('Rome', 41.9, 12.5), ('Oslo', 59.91, 10.75),
             ('Singapore', 1.29, 103.85), ('Tokyo', 35.68, 139.69)]
    image = Image.new('RGB', (1600, 1080), '#17252d')
    draw = ImageDraw.Draw(image)
    font_path = Path('C:/Windows/Fonts/segoeui.ttf')
    def font(n):
        return ImageFont.truetype(str(font_path), n) if font_path.exists() else ImageFont.load_default(size=n)
    draw.text((25, 15), 'Regional sidewalks: retained materials, consistent scale', font=font(29), fill='white')
    draw.text((25, 59), 'Actual mesh/stock albedo sampling. Grass is schematic. No lighting or normal maps; not an engine screenshot.',
              font=font(17), fill='#a6bfcd')
    for index, (city, lat, lon) in enumerate(cases):
        walk = dict(pts=np.array([[0., 0., 0.], [14., 0., 0.]]), fid='source', w=2.5, side=1)
        sc.annotate([walk], geodesy.EnuFrame(lat, lon), source_locations={'source': (lat, lon)},
                    road_classes={'source': 'residential'})
        b = sw.Builder((0, 0, 0))
        b.add_run(walk['pts'], np.tile([0., 1.], (2, 1)), 2.5, walk['curb_h'],
                  slab=sw.slab_material(walk), verge=walk['verge'])
        x, y = 25 + (index % 2) * 790, 108 + (index // 2) * 240
        draw.text((x, y), city + ' / ' + walk['pavement'], font=font(22), fill='white')
        label = walk['curb_style'].replace('_', ' ') + f"  |  {walk['curb_h'] * 1000:.0f} mm curb"
        draw.text((x, y + 30), label, font=font(16), fill='#a6bfcd')
        image.paste(raster(b.arrays(), textures, (-.2, -.3, 14.2, 3.2), size=(750, 170)), (x, y + 57))
    image.save(out / 'regional-styles.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/sidewalk-uv')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    regions, rings = regional_audit(), island_audit()
    gallery(args.game, args.out)
    report = dict(regions=len(regions), routing_mismatches=0, regional_details=regions,
                  protected_roundabouts=rings, tile_benchmark=tile_benchmark(), native_game_acceptance='pending')
    (args.out / 'sanity-review.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'regional_details'}, indent=2))


if __name__ == '__main__':
    main()
