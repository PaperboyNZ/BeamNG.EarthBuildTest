"""Bake tiny shared opaque detail textures once, never during streaming."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'


def main():
    n=256;y,x=np.mgrid[:n,:n]
    # Neutral multiplication masks; vertex colour supplies paint/concrete tint.
    slat=np.full((n,n),242,np.uint8)
    slat[(y%64)<3]=125;slat[(y%64)==3]=255
    paving=np.full((n,n),240,np.uint8)
    paving[(x<2)|(y<2)]=142
    materials={}
    for name,pixels,rough in (('bne_bld_shutter',slat,.55),('bne_bld_paving',paving,.9)):
        filename=name+'.png'
        Image.fromarray(np.repeat(pixels[:,:,None],3,axis=2)).save(OUT/filename,optimize=True)
        materials[name]=dict(name=name,mapTo=name,**{'class':'Material'},version=1.5,
            Stages=[dict(baseColorMap='/levels/beamng_earth/art/shapes/beamngEarth/'+filename,
                         baseColorFactor=[1,1,1,1],roughnessFactor=rough,metallicFactor=0,vertColor=True)],
            translucent=False)
    (OUT/'building_details.materials.json').write_text(json.dumps(materials,indent=2)+'\n')

if __name__=='__main__':main()
