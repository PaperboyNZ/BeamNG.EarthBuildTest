"""Reproducible shared masked window grids; no per-building texture baking."""
from pathlib import Path
import json
import uuid
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'


def main():
    path=OUT/'buildings.materials.json'
    materials=json.loads(path.read_text())
    for kind,box in {'sash':(75,48,181,194),'tall':(87,30,169,211),
                     'wide':(49,78,207,180),'modern':(56,43,200,210),'glass':(0,0,255,255)}.items():
        name='bne_minimum_'+kind
        im=Image.new('RGBA',(256,256),(60,67,69,0));d=ImageDraw.Draw(im)
        x0,y0,x1,y1=box
        d.rectangle(box,fill=(59,63,64,255))
        d.rectangle((x0+2,y0+2,x1-2,y1-2),fill=(186,184,174,255))
        d.rectangle((x0+5,y0+5,x1-5,y1-5),fill=(43,58,65,255))
        for y in range(y0+7,y1-6):
            t=(y-y0)/(y1-y0)
            d.line((x0+7,y,x1-7,y),fill=(int(73-34*t),int(91-40*t),int(101-42*t),255))
        if kind not in ('modern','glass'):
            d.rectangle((126,y0+4,129,y1-4),fill=(164,165,160,255))
            d.rectangle((x0+4,(y0+y1)//2-1,x1-4,(y0+y1)//2+2),fill=(174,174,165,255))
        d.rectangle((x0-3,y1-2,x1+3,y1+3),fill=(192,190,180,255))
        im.save(OUT/(name+'.png'))
        # Sidecar avoids a large collection of per-building texture resources.
        im.save(OUT/(name+'.dds'),pixel_format='DXT5')
        im.getchannel('A').save(OUT/(name+'_opacity.data.png'))
        materials[name]=dict(name=name,mapTo=name,**{'class':'Material'},version=1.5,
            persistentId=str(uuid.uuid5(uuid.NAMESPACE_URL,'beamng-earth/minimum/'+kind)),
            Stages=[dict(baseColorMap='/levels/beamng_earth/art/shapes/beamngEarth/'+name+'.png',
                         baseColorFactor=[1,1,1,1],roughnessFactor=.45,metallicFactor=.05,vertColor=kind=='glass',
                         opacityMap='/levels/beamng_earth/art/shapes/beamngEarth/'+name+'_opacity.data.png',opacityFactor=1.)],
            alphaTest=kind!='glass',alphaRef=128,translucent=False,doubleSided=False,castShadows=False)
    path.write_text(json.dumps(materials,indent=2)+'\n')


if __name__=='__main__':main()
