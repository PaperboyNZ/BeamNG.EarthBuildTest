"""Forced-feature QA sheets; runtime uses the catalogue's probabilistic gates."""
import argparse
from pathlib import Path
import sys
import json
from PIL import Image,ImageDraw


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=root/'build/roof-proportions/modifiers')
    args=parser.parse_args()
    sys.path[:0]=[str(root/'server'),str(root/'server/tests')]
    from test_buildgen_architectural_modifiers import fixture
    from buildgen import architectural_modifiers as modifiers,freeze_items
    import buildings as b
    from building_preview import raster
    args.out.mkdir(parents=True,exist_ok=True)
    report=[]
    for group in ('details','materials'):
        keys=[key for key,row in modifiers.catalogue().items() if bool(row.get('family'))==(group=='materials')]
        columns=4 if group=='details' else 3
        width,height=400,310
        canvas=Image.new('RGB',(columns*width,((len(keys)+columns-1)//columns)*height+40),'#e8edf0')
        draw=ImageDraw.Draw(canvas)
        draw.text((12,12),'Forced feature QA / runtime rates below / approximate materials, not game screenshots',fill='#203040')
        for i,key in enumerate(keys):
            row=modifiers.catalogue()[key];spec=fixture(key)
            items=freeze_items([(spec,0.,0.)]);mesh=b.build(items)
            x,y=(i%columns)*width,40+(i//columns)*height
            canvas.paste(raster(mesh,[],[],width,255,b,tight=True,camera=[1.35,-2.,1.25]),(x,y))
            draw.text((x+12,y+258),row['label'],fill='#203040')
            draw.text((x+12,y+278),f"Selection {row['chance']:.0%} of eligible style recipes; fit required",fill='#405060')
            report.append(dict(feature=key,chance=row['chance'],region=spec.inference.house_style.profile,
                               vertices=len(mesh[0]),triangles=len(mesh[2]),roof=spec.roof,
                               roof_material=spec.inference.roof_material.value,facade=spec.inference.facade.value))
        canvas.save(args.out/(group+'.png'))
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Rendered',len(report),'feature fixtures to',args.out)


if __name__=='__main__':main()
