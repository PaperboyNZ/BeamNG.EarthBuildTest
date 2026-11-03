"""Render actual old/new planting triangles on representative accepted beds.

Synthetic mesh review with approximate material colours, not a game screenshot.
"""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import landscaping
from buildgen.access import AccessPlan, Solid
from buildgen.topology import Footprint


def raster(a,width=800,height=330):
    p,uv,t,m,c=a
    view=np.array([.35,-1.,.72]);view/=np.linalg.norm(view)
    right=np.cross([0.,0.,1.],view);right/=np.linalg.norm(right)
    up=np.cross(view,right)
    q=np.column_stack((p@right,p@up,p@view))
    span=np.ptp(q[:,:2],axis=0)
    scale=min((width-42)/span[0],(height-45)/span[1])
    centre=(q[:,:2].min(0)+q[:,:2].max(0))/2
    q[:,:2]=(q[:,:2]-centre)*[scale,-scale]+[width/2,height/2]
    im=Image.new('RGB',(width,height),'#e8edf0');draw=ImageDraw.Draw(im)
    light=np.array([-.3,-.5,1.]);light/=np.linalg.norm(light)
    cover=np.isin(m,[b.MATERIALS.index(v) for v in (b.LAWN,b.GARDEN,b.GRAVEL)])
    order=np.argsort(q[t,2].mean(1))
    # Planting is wholly above the cover; draw the two large cover faces first
    # so centre-depth sorting cannot incorrectly hide the distant end shrubs.
    for i in np.concatenate((order[cover[order]],order[~cover[order]])):
        ids=t[i];xyz=p[ids]
        normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);size=np.linalg.norm(normal)
        if size<1e-9 or normal@view<=0:continue
        colour=c[ids,:3].mean(0)/255
        mean=np.array(b.MAT_MEAN.get(b.MATERIALS[m[i]],(.78,.78,.76)))
        rgb=np.clip(colour*mean*(.65+.35*max(0.,normal@light/size))*255,0,255).astype(np.uint8)
        draw.polygon([tuple(x) for x in q[ids,:2]],fill=tuple(map(int,rgb)))
    return im


def spec_for(p,seed):
    fp=Footprint(((0,5),(30,5),(30,20),(0,20)))
    spec=b.plan(np.asarray(fp.outer),{'class':'supermarket','height':6.,'seed_id':seed,'_footprint':fp})
    spec.access=AccessPlan(0.,None,(),landscape=(Solid('site_garden_bed',tuple(tuple(v) for v in p),-.1),))
    return spec


def main():
    out=ROOT/'build/visible-sites/landscaping-geometry-preview.png';out.parent.mkdir(parents=True,exist_ok=True)
    original_path=ROOT/'build/visible-sites/original/landscaping.py'
    loader=importlib.util.spec_from_file_location('buildgen._landscape_before',original_path)
    before=importlib.util.module_from_spec(loader);sys.modules[loader.name]=before;loader.loader.exec_module(before)
    fixtures=[('20 x 2 m commercial garden bed',np.array([[0,0,0],[20,0,0],[20,2,0],[0,2,0]],float)),
              ('Skewed tapered bed on 22% grade',np.array([[0,0,0],[17,3,0],[15,5,0],[-1,2,0]],float))]
    fixtures[1][1][:,2]=fixtures[1][1][:,0]*.22
    canvas=Image.new('RGB',(2400,850),'#e8edf0');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    draw.text((25,12),'Actual emitted landscaping mesh / representative accepted soft beds',font=font,fill='#1d2933')
    draw.text((25,44),'Approximate material colours; synthetic geometry review, not BeamNG screenshots',font=font,fill='#48545b')
    stats=[]
    for row,(label,p) in enumerate(fixtures):
        spec=spec_for(p,'visible-beds')
        for column,(title,module,detail) in enumerate((('Previous near',before,True),('New near',landscaping,True),('New lite',landscaping,False))):
            mesh=b.Mesh();module.draw(mesh,spec,detail);a=mesh.arrays()
            x=column*800;y=96+row*375
            canvas.paste(raster(a),(x,y))
            draw.text((x+24,y+315),f'{title}: {len(a[2])} triangles',font=font,fill='#1d2933')
            draw.text((x+24,y+345),label,font=font,fill='#48545b')
            stats.append(dict(fixture=label,tier=title,triangles=len(a[2]),height_m=float(a[0][:,2].max()-p[:,2].max())))
    canvas.save(out)
    out.with_suffix('.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(out)
    # Also exercise the production automatic-site planner and full building
    # renderer, rather than treating representative bands as site evidence.
    sys.path.insert(0,str(ROOT/'server/tests'))
    from test_buildgen_commercial import fixture
    from buildgen import automatic_sites, freeze_items
    from building_preview import raster as building_raster
    spec,lo,hi=fixture('supermarket',40.,20.)
    roads=[(np.array([[-50.,-25.],[90.,-25.]]),3.,'residential',False)]
    automatic_sites.resolve([(spec,lo,hi)],roads,0.,0.,ground=lambda p:np.zeros(len(p)))
    assert any(v.kind=='site_garden_bed' for v in spec.access.landscape)
    integrated=Image.new('RGB',(2400,720),'#e8edf0');pen=ImageDraw.Draw(integrated)
    for index,(title,module,lite) in enumerate((('Previous planting / current automatic grounds',before,False),
                                             ('New planting / automatic grounds',landscaping,False),
                                             ('New lite / automatic grounds',landscaping,True))):
        draw_fn=module.draw
        with patch.object(landscaping,'draw',draw_fn):
            mesh=b.build(freeze_items([(spec,lo,hi)]),lite=lite)
        integrated.paste(building_raster(mesh,[],[],800,620,b),(index*800,40))
        pen.text((index*800+20,18),title,font=font,fill='#1d2933')
        pen.text((index*800+20,665),f'{len(spec.access.landscape)} accepted soft patches / {len(mesh[2])} full-mesh triangles',font=font,fill='#48545b')
    full_out=out.with_name('landscaping-integrated-preview.png');integrated.save(full_out);print(full_out)


if __name__=='__main__':main()
