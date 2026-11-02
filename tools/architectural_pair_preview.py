"""Close review of stepped masonry gables and opening-aligned timber framing."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw

root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'server'),str(root/'server/tests')]
from test_buildgen_architectural_modifiers import fixture
from building_preview import raster
from buildgen import freeze_items
import buildings as b

canvas=Image.new('RGB',(1400,940),'#e8edf0');draw=ImageDraw.Draw(canvas)
for i,(key,h,nf,rise) in enumerate([('stepped_gable',6.,1,2.8),('half_timber',6.,1,2.8),
                                    ('stepped_gable',9.,2,3.),('half_timber',9.,2,3.)]):
    spec=fixture(key,height=h,num_floors=nf,roof_height=rise)
    mesh=b.build(freeze_items([(spec,0.,0.)]));x=i%2*700;y=i//2*470
    canvas.paste(raster(mesh,[],[],700,420,b,tight=True,camera=[1.7,-2.,.9]),(x,y))
    draw.text((x+16,y+425),key.replace('_',' ').title()+' / '+str(nf)+' storey / revised geometry',fill='#203040')
    draw.text((x+16,y+447),'Synthetic preview; approximate materials, not game textures',fill='#405060')
dest=root/'build/roof-proportions/modifiers/revised-gable-timber.png'
dest.parent.mkdir(parents=True,exist_ok=True);canvas.save(dest)
print(dest)
