"""Multi-angle evidence sheets for personal review; not native-game captures."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from regional_theme_preview import fixture,regional,environments,b,raster,ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/regional-runtime/personal-audit')
    parser.add_argument('--keys',nargs='*')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    keys=args.keys or list(environments.catalogue()['regions'])
    font=ImageFont.truetype('arial.ttf',19)
    refs=ROOT/'build/regional-runtime/reference-images'
    rows=[];report={}
    for i,key in enumerate(keys):
        item=fixture(key,representative=True);spec=item[0];mesh=b.build([item]);p=regional.catalogue()[key]
        row=Image.new('RGB',(1800,470),'#e8edf0');draw=ImageDraw.Draw(row)
        draw.text((12,8),f'{i+1:02d} {key} | {p["massing_grammar"]} | {spec.inference.roof_variant}',font=font,fill='#172b3a')
        paths=list(refs.rglob(key+'_documentary.*')) or list(refs.rglob(key+'.*'))
        # These research photographs are used only locally, never packaged.
        if paths:
            photo=ImageOps.contain(Image.open(paths[0]).convert('RGB'),(390,400))
            row.paste(photo,((400-photo.width)//2,45+(400-photo.height)//2))
        for j,camera in enumerate(((1.35,-2.,.75),(-1.35,2.,.75))):
            rendered=raster(mesh,[('door',2.3,0.,0.,0.,'',2.25,'')],[],700,400,b,camera=camera,tight=True)
            row.paste(rendered,(400+j*700,45))
        draw.text((410,445),'Front / side',font=font,fill='#526878')
        draw.text((1110,445),'Rear / opposite side',font=font,fill='#526878')
        rows.append(row)
        report[key]=dict(roof=spec.roof,roof_variant=spec.inference.roof_variant,grammar=p['massing_grammar'],
            wall=p['facade'],opening_pattern=p['opening_pattern'],opening_shape=p['opening_shape'],
            vertices=len(mesh[0]),triangles=len(mesh[2]),reference=str(paths[0]) if paths else None)
        if len(rows)==4 or i==len(keys)-1:
            canvas=Image.new('RGB',(1800,40+470*len(rows)),'#e8edf0')
            ImageDraw.Draw(canvas).text((12,8),'LOCAL REVIEW: reference + actual generated mesh, approximate colours; not an exact reconstruction',font=font,fill='#172b3a')
            for n,row in enumerate(rows):canvas.paste(row,(0,40+n*470))
            canvas.save(args.out/f'audit-{i//4+1:02d}.jpg',quality=94);rows=[]
            print(f'Rendered {i+1}/{len(keys)}',flush=True)
    (args.out/'fixtures.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
