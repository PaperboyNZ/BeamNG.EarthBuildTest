"""Audit all regional roof priors and render synthetic massing (not game lighting)."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, default=Path(__file__).resolve().parents[1] / 'server')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--attics', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.server.resolve()))
    import buildings as b
    from buildgen import house_styles, regional_architecture, materials
    from buildgen.environments import Environment
    from buildgen.inference import resolve
    from buildgen.topology import Footprint
    from building_preview import raster

    rows = []
    for region in regional_architecture.catalogue():
        with patch('buildgen.house_styles.select', return_value=house_styles.HouseStyle('regional', region)), \
             patch('buildgen.environments.resolve', return_value=Environment(region=region)):
            for width in (8., 12., 18.):
                fp = Footprint(((0., 0.), (24., 0.), (24., width), (0., width)))
                for seed in range(24):
                    r = resolve({'class': 'house', 'num_floors': 1, 'seed_id': str(seed)}, fp, width / 2.)
                    rows.append(dict(region=region, width=width, seed=seed, roof=r.roof.value,
                                     variant=r.roof_variant, rise=r.roof_rise, body=r.body_height,
                                     equivalent_pitch=r.pitch))

    cases = [('NZ broad hip', 'nz_temperate', 'standard', 'hipped'),
             ('Northern gable', 'nordic_cold', 'standard', 'gabled')]
    cases += [(v.replace('_', ' ').title(), 'nz_temperate', v,
               'hipped' if v in ('mansard', 'flared_hip') else 'gabled')
              for v in ('gambrel', 'mansard', 'saltbox', 'shed', 'broad_eave', 'flared_hip', 'cross_gable')]
    cases += [('Joined courtyard', 'nz_temperate', 'standard', 'hipped')]
    if args.attics:
        cases = [('Attic gable windows', 'jp_temperate', 'standard', 'gabled'),
                 ('Gabled dormers', 'us_northeast', 'standard', 'gabled'),
                 ('Shed dormers', 'us_midwest', 'standard', 'hipped'),
                 ('Gambrel attic', 'us_northeast', 'gambrel', 'gabled'),
                 ('Mansard attic', 'france_regional', 'mansard', 'hipped'),
                 ('Low roof - no attic', 'us_northeast', 'standard', 'gabled')]
    canvas = Image.new('RGB', (1000, ((len(cases) + 1) // 2) * 270 + 40), '#e8edf0')
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 12), 'Synthetic roof proportions / approximate materials / not BeamNG screenshots', fill='#203040')
    preview = []
    original_choose = materials.choose
    for index, (label, region, variant, kind) in enumerate(cases):
        fp = Footprint(((0., 0.), (18., 0.), (18., 12.), (0., 12.)))
        if label == 'Joined courtyard':
            fp = Footprint(((0., 0.), (18., 0.), (18., 18.), (0., 18.)),
                           (((4., 4.), (4., 14.), (14., 14.), (14., 4.)),))
        def choose(identity, channel, options):
            return variant if channel == 'regional-roof-variant-v1' else original_choose(identity, channel, options)
        with patch('buildgen.house_styles.select', return_value=house_styles.HouseStyle('regional', region)), \
             patch('buildgen.environments.resolve', return_value=Environment(region=region)), \
             patch('buildgen.regional_architecture.roof_default', return_value=kind), \
             patch('buildgen.materials.choose', side_effect=choose):
            attrs = {'class': 'house', 'num_floors': 1, 'seed_id': 'roof-preview', '_footprint': fp}
            if args.attics:
                attrs.update(num_floors=2, roof_height=1.8 if label.startswith('Low roof') else 3.4)
            spec = b.plan(np.asarray(fp.outer), attrs)
        if args.attics:
            from buildgen import attics
            from dataclasses import replace
            spec.inference=replace(spec.inference,modifiers=('dormers',) if region!='jp_temperate' else ())
            for seed in np.linspace(.01, .99, 40):
                spec.seed = float(seed)
                if attics.plan(spec)[1]: break
        spec.gring = np.zeros(len(fp.outer))
        mesh = b.build([(spec, 0., 0.)])
        x, y = index % 2 * 500, 40 + index // 2 * 270
        canvas.paste(raster(mesh, [], [], 500, 230, b, tight=True, camera=[1.35, -2., .85]), (x, y))
        draw.text((x + 12, y + 230), label, fill='#203040')
        draw.text((x + 12, y + 247), f'Roof rise {spec.inference.roof_rise:.2f} m / walls {spec.height:.2f} m', fill='#203040')
        preview.append(dict(label=label, rise=spec.inference.roof_rise, body=spec.height))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    pitched = [r for r in rows if r['rise'] > 0.]
    report = dict(regions=64, cases=len(rows), pitched=len(pitched),
                  rise_median=float(np.median([r['rise'] for r in pitched])),
                  rise_max=max(r['rise'] for r in pitched),
                  roofs_at_least_wall_height=sum(r['rise'] >= r['body'] for r in pitched),
                  preview=preview, fixtures=rows)
    args.out.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('fixtures', 'preview')}, indent=2))


if __name__ == '__main__':
    main()
