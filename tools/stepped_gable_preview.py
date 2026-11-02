"""Same broad and narrow fixtures for comparing stepped-gable revisions."""
import argparse
from pathlib import Path
import sys
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--server',type=Path,default=root/'server')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--label',default='Revised')
parser.add_argument('--inferred',action='store_true',help='Use unmapped roof height to review the actual regional recipe')
args=parser.parse_args()
sys.path[:0]=[str(args.server),str(args.server/'tests'),str(root/'tools')]
from test_buildgen_architectural_modifiers import fixture
from buildgen.topology import Footprint
from buildgen import freeze_items
from building_preview import raster
import buildings as b
canvas=Image.new('RGB',(1400,510),'#e8edf0');draw=ImageDraw.Draw(canvas)
for i,(width,depth) in enumerate(((12.,10.),(6.,11.))):
    fp=Footprint(((0.,0.),(width,0.),(width,depth),(0.,depth)))
    spec=fixture('stepped_gable',_footprint=fp,height=9.,num_floors=2,
                 roof_shape='gabled',roof_height=None if args.inferred else 3.)
    mesh=b.build(freeze_items([(spec,0.,0.)]))
    canvas.paste(raster(mesh,[],[],700,440,b,tight=True,camera=[1.5,-2.5,.75]),(i*700,0))
    detail='Stepped gable' if 'stepped_gable' in spec.inference.modifiers else 'Ordinary gable: proportions unsuitable for steps'
    draw.text((i*700+15,450),f'{args.label} / {width:g} x {depth:g} m / 9 m total / roof rise {spec.inference.roof_rise:.2f} m',fill='#203040')
    draw.text((i*700+15,474),detail+' / synthetic preview',fill='#405060')
args.out.parent.mkdir(parents=True,exist_ok=True);canvas.save(args.out)
print(args.out)
