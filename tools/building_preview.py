"""Render synthetic building geometry for visual review without game assets.

Surface colours are approximated from the existing material means. This is not
a BeamNG screenshot or a texture/lighting acceptance test. No map downloads.

  python tools/building_preview.py --out /tmp/building-preview.png
  python tools/building_preview.py --server /tmp/older/server --out /tmp/before.png
"""
import argparse
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def raster(mesh, props, drives, width, height, b, roof_grid=False, ground=None, *, camera=None, tight=False):
    p, uv, t, mid, mats, colour = mesh[:6]
    points, tris = p.tolist(), t.tolist()
    texcoords = uv.tolist()
    roof_triangles = {i for i, mat in enumerate(mid) if mats[mat] in (b.ROOF_SLATE, b.ROOF_METAL, b.ROOF_SHINGLE)}
    ground = ground or (lambda xy: np.zeros(len(xy)))
    surface = []
    textures={}
    texture_root=Path(__file__).resolve().parents[1]/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
    for i,mat in enumerate(mats):
        if mat.startswith('bne_minimum_') and (texture_root/(mat+'.png')).is_file():
            with Image.open(texture_root/(mat+'.png')) as image:textures[i]=np.asarray(image.convert('RGBA'))
    for mat, tri in zip(mid, t):
        mean = (.26, .33, .36) if mats[mat] in (b.FACADE, b.OFFICE, b.SHOP) else b.MAT_MEAN.get(mats[mat], (.78, .78, .76))
        if mat in textures:mean=(1.,1.,1.)
        surface.append(np.array(mean) * np.mean(colour[tri, :3], axis=0) / 255.)

    def quad(q, rgb):
        i = len(points)
        points.extend(q)
        texcoords.extend(((0., 0.),)*4)
        tris.extend(((i, i+1, i+2), (i, i+2, i+3)))
        surface.extend((np.asarray(rgb), np.asarray(rgb)))

    lo, hi = p[:, :2].min(0), p[:, :2].max(0)
    xs, ys = np.linspace(lo[0]-2, hi[0]+2, 9), np.linspace(lo[1]-(2 if tight else 10), hi[1]+2, 13)
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            xy = np.array([(x0,y0), (x1,y0), (x1,y1), (x0,y1)])
            quad([(*p, z) for p, z in zip(xy, ground(xy))], (.48, .55, .39))
    for drive in drives:
        line = np.asarray(drive["n"])
        for a, c in zip(line, line[1:]):
            d = c[:2] - a[:2]
            n = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9) * drive["w"] / 2
            xy = np.array([a[:2]-n, c[:2]-n, c[:2]+n, a[:2]+n])
            quad([(*p, z+.008) for p, z in zip(xy, ground(xy))], (.47, .47, .46))
    # The stock door is a separate game prop. Show its documented panel envelope
    # so this review also exposes overlap with generated windows.
    for row in props:
        if row[0] != "door":
            continue
        _, x, y, z, angle, _, h, _ = row
        d = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        outside = np.array([d[1], -d[0]])
        centre = np.array([x, y]) + outside * .021
        a, c = centre - d*.5, centre + d*.5
        quad([(*a, z), (*c, z), (*c, z+h), (*a, z+h)], (.25, .28, .29))
    p, tris, surface, texcoords = np.asarray(points), np.asarray(tris), np.asarray(surface), np.asarray(texcoords)
    view = np.array(camera or [1.35, -2., 1.2],dtype=float); view /= np.linalg.norm(view)
    right = np.cross([0., 0., 1.], view); right /= np.linalg.norm(right)
    up = np.cross(view, right)
    q = np.column_stack((p @ right, p @ up, p @ view))
    span = np.ptp(q[:, :2], axis=0)
    scale = min((width-40)/span[0], (height-40)/span[1])
    centre = (q[:, :2].min(0) + q[:, :2].max(0)) / 2
    q[:, :2] = (q[:, :2] - centre) * [scale, -scale] + [width/2, height/2]
    pixels = np.full((height, width, 3), (232, 237, 240), np.uint8)
    zbuf = np.full((height, width), -np.inf)
    light = np.array([-.3, -.6, 1.]); light /= np.linalg.norm(light)
    for triangle, (ids, rgb) in enumerate(zip(tris, surface)):
        abc = p[ids]
        normal = np.cross(abc[1]-abc[0], abc[2]-abc[0])
        length = np.linalg.norm(normal)
        if length < 1e-10 or normal @ view <= 0:
            continue
        rgb = np.clip(rgb * (.6 + .4 * max(0., normal @ light / length)) * 255., 0., 255.).astype(np.uint8)
        a, c, d = q[ids]
        x0 = max(0, int(min(a[0], c[0], d[0]))); x1 = min(width, int(max(a[0], c[0], d[0]))+2)
        y0 = max(0, int(min(a[1], c[1], d[1]))); y1 = min(height, int(max(a[1], c[1], d[1]))+2)
        if x0 >= x1 or y0 >= y1:
            continue
        xx, yy = np.meshgrid(np.arange(x0, x1)+.5, np.arange(y0, y1)+.5)
        den = (c[1]-d[1])*(a[0]-d[0]) + (d[0]-c[0])*(a[1]-d[1])
        if abs(den) < 1e-9:
            continue
        w0 = ((c[1]-d[1])*(xx-d[0]) + (d[0]-c[0])*(yy-d[1])) / den
        w1 = ((d[1]-a[1])*(xx-d[0]) + (a[0]-d[0])*(yy-d[1])) / den
        w2 = 1.-w0-w1
        z = w0*a[2]+w1*c[2]+w2*d[2]
        mask = (w0 >= -1e-8) & (w1 >= -1e-8) & (w2 >= -1e-8) & (z > zbuf[y0:y1, x0:x1])
        if triangle<len(mid) and mid[triangle] in textures:
            texture=textures[mid[triangle]]
            uv = w0[...,None]*texcoords[ids[0]] + w1[...,None]*texcoords[ids[1]] + w2[...,None]*texcoords[ids[2]]
            tx=(np.mod(uv[:,:,0],1.)*texture.shape[1]).astype(int)%texture.shape[1]
            ty=((1.-np.mod(uv[:,:,1],1.))*texture.shape[0]).astype(int)%texture.shape[0]
            sample=texture[ty,tx]
            mask &= sample[:,:,3]>=128
            pixels[y0:y1,x0:x1][mask]=np.clip(sample[:,:,:3]* (rgb.astype(float)/255.),0,255).astype(np.uint8)[mask]
        elif roof_grid and triangle in roof_triangles:
            uv = w0[...,None]*texcoords[ids[0]] + w1[...,None]*texcoords[ids[1]] + w2[...,None]*texcoords[ids[2]]
            grid = np.floor(uv*4).sum(axis=2) % 2
            shade = .7 + .3*grid
            pixels[y0:y1, x0:x1][mask] = np.clip(rgb * shade[...,None], 0, 255).astype(np.uint8)[mask]
        else:
            pixels[y0:y1, x0:x1][mask] = rgb
        zbuf[y0:y1, x0:x1][mask] = z[mask]
    return Image.fromarray(pixels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, default=Path(__file__).resolve().parents[1]/"server")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="Facade and roof geometry review")
    parser.add_argument("--roof-grid", action="store_true", help="Diagnostic checker using actual roof UVs; not game assets")
    parser.add_argument("--access-fixtures", action="store_true", help="Review entrance thresholds on synthetic slopes")
    parser.add_argument("--roof-fixtures", action="store_true", help="Twelve multi-wing, oblique and courtyard roofs")
    parser.add_argument("--hipped-roofs", action="store_true", help="Use hips for every complex roof fixture")
    parser.add_argument("--preset-fixtures", action="store_true", help="Zone and functional preset review")
    args = parser.parse_args()
    sys.path.insert(0, str(args.server.resolve()))
    import buildings as b
    from buildgen.topology import Footprint
    from buildgen.context import Context, ContextManifest, Neighbour
    from buildgen.evidence import normalise_attributes
    from buildgen import freeze_items

    rectangle = ((0., 0.), (14., 0.), (14., 12.), (0., 12.))
    notch = ((0., 0.), (16., 0.), (16., 9.), (10., 9.), (10., 15.), (0., 15.))
    examples = [("Missing tags / detached spacing", rectangle, {}),
                ("Irregular residential footprint", notch, {"class": "house"}),
                ("Mapped brick bungalow", rectangle, {"class": "bungalow", "facade_material": "brick", "num_floors": 1}),
                ("Mapped timber / one storey", rectangle, {"class": "house", "facade_material": "wood", "num_floors": 1}),
                ("Mapped two storeys", rectangle, {"class": "house", "num_floors": 2}),
                ("Narrow entrance / overlap regression", ((0., 0.), (8., 0.), (8., 12.), (0., 12.)), {"class": "house", "num_floors": 1})]
    if args.access_fixtures:
        examples = [(label, rectangle, {"class": "house", "num_floors": 1, "roof_shape": "hipped"})
                    for label in ("Level frontage", "Raised floor / entrance stairs", "High rear ground / lowered entry",
                                  "Cross-slope / garage apron", "Short setback / lowered entry", "Sloping driveway approach")]
    if args.roof_fixtures:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"server/tests"))
        from building_fixtures import complex_roofs
        examples = [(name, Footprint(outer, holes), {"class": "house", "num_floors": 1,
                     "roof_shape": "hipped" if i % 2 else "gabled", "roof_material": "metal" if i % 3 == 0 else "slate"})
                    for i, (name, outer, holes) in enumerate(complex_roofs())]
        if args.hipped_roofs:
            examples = [(name, fp, dict(attrs, roof_shape="hipped")) for name,fp,attrs in examples]
    if args.preset_fixtures:
        examples = [("Observed residential zone",rectangle,{"_land":"residential"}),
                    ("Mapped bungalow",rectangle,{"class":"bungalow","num_floors":1}),
                    ("Tropical house / sun hoods",rectangle,{"class":"house","_climate":2,"roof_shape":"hipped","num_floors":1}),
                    ("Narrow terrace",((0,0),(6,0),(6,12),(0,12)),{"class":"terrace","num_floors":2}),
                    ("Mixed use / shop base",rectangle,{"class":"mixed_use","num_floors":3}),
                    ("Workshop / service shutter",rectangle,{"class":"workshop","height":5.}),
                    ("Observed industrial zone",rectangle,{"_land":"industrial"}),
                    ("School / repeated bays",rectangle,{"class":"school","num_floors":2}),
                    ("Farmyard / agricultural shell",rectangle,{"_land":"farmyard"}),
                    ("Garden shed",((0,0),(5,0),(5,4),(0,4)),{"class":"shed","num_floors":1}),
                    ("Joined hip wings",notch,{"class":"house","roof_shape":"hipped","num_floors":1}),
                    ("Unknown evidence / generic shell",rectangle,{"_no_neighbours":True})]
    neighbours = tuple(Neighbour(f"N{i}", 30.+i*10, 130., normalise_attributes({})) for i in range(4))
    context = Context(ContextManifest("synthetic-observed-spacing"), neighbours, climate=15)
    canvas = Image.new("RGB", (1500, 120+410*math.ceil(len(examples)/3)), "#e8edf0")
    draw = ImageDraw.Draw(canvas)
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font_path.exists():
        font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    title = ImageFont.truetype(str(font_path), 26) if font_path.exists() else font
    draw.text((25, 14), args.label, font=title, fill="#1d2933")
    draw.text((25, 53), "Synthetic fixtures; diagnostic UV checker." if args.roof_grid else
              "Synthetic fixtures. Approximate surface colours and door envelopes; no game textures or lighting.", font=font, fill="#43515c")
    report = []
    for i, (label, ring, attrs) in enumerate(examples):
        fp = ring if isinstance(ring, Footprint) else Footprint(ring)
        attrs = dict(attrs)
        land = attrs.pop("_land", None)
        local = replace(context, climate=attrs.pop("_climate",15),
                        land_use=((land,1.),) if land else (),
                        neighbours=() if attrs.pop("_no_neighbours",False) else context.neighbours)
        spec = b.plan(np.asarray(fp.outer), dict(attrs, seed_id=f"preview-{i}", _footprint=fp, _context=local))
        drives = []
        terrain = lambda xy: np.zeros(len(xy))
        road_y = -13.
        if args.access_fixtures:
            if i in (1, 2, 4):
                rise = .9 if i == 1 else 3.
                terrain = lambda xy: np.maximum(xy[:, 1], 0)*rise/12.
            elif i == 3:
                terrain = lambda xy: .1*xy[:, 0]
            elif i == 5:
                terrain = lambda xy: .12*xy[:, 1]
            if i == 4:
                road_y = -4.
        spec.gring = terrain(np.asarray(fp.outer))
        low, high = float(spec.gring.min()), float(spec.gring.max())
        items = [(spec, low, high)]
        kwargs = {"ground": terrain}
        props = b.doors(items, [(np.array([(-50., road_y), (100., road_y)]), 3., "residential", False)], 0., 0., drives, **kwargs)
        mesh = b.build(freeze_items(items))
        x, y = (i % 3)*500, 100+(i // 3)*410
        canvas.paste(raster(mesh, props, drives, 500, 350, b, args.roof_grid, terrain), (x, y))
        draw.text((x+20, y+350), label, font=font, fill="#1d2933")
        desc = f"{spec.floors} storey  /  {spec.inference.facade.value}  /  {spec.roof}"
        draw.text((x+20, y+378), desc, font=font, fill="#43515c")
        report.append({"fixture": label, "floors": spec.floors, "facade": spec.inference.facade.value,
                       "roof": spec.roof, "vertices": len(mesh[0]), "triangles": len(mesh[2]),
                       "selection": asdict(spec.inference.selection) if hasattr(spec.inference,"selection") else None,
                       "diagnostics": spec.diagnostics,
                       "access": asdict(spec.access) if spec.access is not None else None})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    args.out.with_suffix(".json").write_text(json.dumps(report, indent=2)+"\n")
    print(args.out)


if __name__ == "__main__":
    main()
