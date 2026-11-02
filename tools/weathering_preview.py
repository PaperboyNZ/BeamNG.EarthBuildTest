"""Actual mesh tint comparison; shared material detail and game lighting excluded."""
from pathlib import Path
import argparse
import sys
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'tools')]
import buildings as b
from buildgen import weathering,freeze_items
from buildgen.topology import Footprint
from buildgen.context import Context
from building_preview import raster


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
    spec=b.plan(np.asarray(fp.outer),dict(seed_id='weathering-review',_footprint=fp,
        _context=Context(location=(-36.9141,174.90925)),height=8.,num_floors=2,**{'class':'house'}))
    spec.gring=np.zeros(4);spec.door=(0,2.3);spec.front=0
    items=freeze_items([(spec,0.,0.)])
    canvas=Image.new('RGB',(1280,330),'#e8edf0');draw=ImageDraw.Draw(canvas)
    draw.text((12,10),'Same generated house: vertex aging only; rain-streak texture and BeamNG lighting excluded',fill='#203040')
    for index,(label,amount) in enumerate((('Previous clean tint',0.),('Maintained',.1),('Weathered',.55),('Strong aging',1.))):
        with patch.object(weathering,'strength',return_value=amount):mesh=b.build(items)
        canvas.paste(raster(mesh,[],[],320,270,b),(index*320,30))
        draw.text((index*320+15,310),label,fill='#203040')
    args.out.parent.mkdir(parents=True,exist_ok=True);canvas.save(args.out)
    print(args.out)


if __name__=='__main__':main()
