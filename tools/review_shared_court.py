"""Review an actual accepted shared court and encoded production contact mesh."""
import hashlib
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'server'),str(ROOT/'server/tests')]
import buildings as b
import roadmesh
from buildgen import freeze_items
from sitegen import shared_courts as sc
from sitegen.plan import SiteGraph
from test_sitegen_shared_courts import fixture
from building_preview import raster


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'build/world-architecture-programme/m1-shared-court-review')
    destination = parser.parse_args().out
    destination.mkdir(exist_ok=False)
    tile, plan, items = fixture()
    court, why = sc.fit(plan,lambda lat,lon:np.full(np.shape(lat),20.))
    assert court is not None and why is None
    source = sc._frame(plan)
    mesh = sc.compile((court,),tile.frame,(*tile.box[:2],0.))
    path = destination/'court.cdae'
    roadmesh.write(str(path),mesh)
    graph = destination/'synthetic-sites.json'
    graph.write_text(SiteGraph((plan,)).to_json()+'\n',encoding='utf-8')
    houses = list(b.build(freeze_items(items)))
    houses[0] = sc.project_points(houses[0]+(*tile.box[:2],0.),tile.frame,source)
    common = sc.compile((court,),source)
    offset = len(houses[0])
    reviewed = (np.vstack((houses[0],common[0])),np.vstack((houses[1],common[2])),
        np.vstack((houses[2],common[1]+offset)),np.r_[houses[3],common[4]+len(houses[4])],
        [*houses[4],*common[3]],np.vstack((houses[5],np.full((len(common[0]),4),255,np.uint8))))
    image = Image.new('RGB',(1280,520),'white')
    draw = ImageDraw.Draw(image)
    draw.text((16,8),'Canonical mapped court / two member buildings / preserved source hole',(20,30,40))
    draw.text((16,28),'Offline geometry review. Shared road interfaces and native contact are not accepted.',(40,50,60))
    for x,camera in ((0,(1.4,-2.,1.5)),(640,(.1,-.4,2.5))):
        picture = raster(reviewed,[],[],640,450,b,ground=lambda xy:np.full(len(xy),20.),camera=camera,tight=True)
        image.paste(picture,(x,56))
    image.save(destination/'review.png')
    sites,boxes,masks = sc.metadata((court,),tile.frame)
    report = dict(scope='synthetic mapped common court; not native appearance/contact/retention acceptance',
        source_schema=23,host=tile.key,revision=court.revision,terrain_points=court.terrain_points,
        vertices=len(mesh[0]),triangles=len(mesh[1]),material_primitives=len(mesh[3]),
        producer=plan.evidence.ref.to_dict(),consumers=[c.to_dict() for c in plan.resources[0].consumers],
        encoded_mesh_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),sites=sites,colliders=boxes,masks=masks,
        source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            'server/sitegen/shared_courts.py','server/blockworker.py','server/buildgen/products.py',
            'server/revisit.py','server/tests/test_sitegen_shared_courts.py','tools/review_shared_court.py')})
    (destination/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('revision','terrain_points','vertices','triangles','encoded_mesh_sha256')}))


if __name__ == '__main__': main()
