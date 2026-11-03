"""Offline terminal facade and classification review, not a BeamNG playtest."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items, programme
from buildgen.topology import Footprint
from building_preview import raster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'build/architecture-next/terminals.png')
    args = parser.parse_args()
    canvas = Image.new('RGB', (1400, 1160), (232, 237, 240))
    draw = ImageDraw.Draw(canvas)
    def font_at(size):
        for name in ('Arial.ttf', 'DejaVuSans.ttf'):
            try:return ImageFont.truetype(name, size)
            except OSError:pass
        return ImageFont.load_default(size=size)
    font, small = font_at(20), font_at(16)
    draw.text((20, 15), 'Terminal shared programme / synthetic mesh review / construction era unknown', fill=(30,45,55), font=font)
    draw.text((20, 45), 'Public frontage at left; opposite side at right. No invented transport-side interfaces.', fill=(30,45,55), font=small)
    cases = [('Regional hall', 'airport_terminal', 40, 24, ''),
             ('Linear concourse', 'airport_concourse', 80, 12, ''),
             ('Keyword control', 'hotel', 36, 24, 'Terminal Hotel'),
             ('Freight control', 'freight_terminal', 48, 28, 'Freight Terminal')]
    records = []
    for row, (label, cls, w, d, name) in enumerate(cases):
        fp = Footprint(((0,0), (w,0), (w,d), (0,d)))
        start = time.perf_counter()
        s = b.plan(np.asarray(fp.outer), dict(_footprint=fp, seed_id=cls, name=name,
                    height=8., num_floors=1, roof_shape='flat', **{'class':cls}))
        s.gring = np.zeros(len(s.ring))
        props = b.doors([(s,0.,0.)], [(np.array([(-100.,-9.),(200.,-9.)]),3.,'residential',False)],
                        0.,0.,ground=lambda xy:np.zeros(len(xy)))
        frozen = freeze_items([(s,0.,0.)]); mesh = b.build(frozen)
        elapsed = (time.perf_counter()-start)*1000
        canvas.paste(raster(mesh,props,[],700,220,b),(0,80+row*270))
        reverse = mesh[0].copy(); reverse[:,:2] *= -1
        reverse_mesh = (reverse, *mesh[1:])
        canvas.paste(raster(reverse_mesh,[],[],700,220,b),(700,80+row*270))
        family = s.terminal['family'] or 'ordinary diagnosed shell'
        shared=programme.derive(frozen[0][0])
        draw.text((20,298+row*270), f'{label}: {family}', fill=(30,45,55), font=small)
        draw.text((20,320+row*270),f'{len(shared.datums)} shared datums / {len(shared.runs)} elevation runs / era: {shared.era.status}',fill=(60,75,85),font=small)
        records.append(dict(label=label, metadata=s.terminal, use=s.inference.use.value,
                            vertices=len(mesh[0]), triangles=len(mesh[2]), planning_near_ms=elapsed,
                            programme=asdict(shared),semantic_seed_channels={channel:shared.seed(channel) for channel in programme.CHANNELS},
                            layout=asdict(frozen[0][0].facades)))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(dict(status='synthetic_not_game_acceptance',fixtures=records),indent=2),encoding='utf-8')
    print(args.out)


if __name__ == '__main__':
    main()
