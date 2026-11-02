"""Build the shared seamless dirt/rain-streak detail map, without per-building assets."""
from pathlib import Path
import struct
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering.png'


def texture(size=256):
    rng=np.random.default_rng(20261102)
    y,x=np.mgrid[0:size,0:size]/size
    broad=np.zeros_like(x);streak=np.zeros_like(x)
    for frequency,amplitude in ((1,1),(2,.6),(4,.3),(8,.15),(16,.07)):
        for _ in range(4):
            kx,ky=rng.integers(1,frequency+1,2)
            broad+=amplitude*np.cos(2*np.pi*(kx*x+ky*y)+rng.random()*2*np.pi)
    for k in range(8,53):
        streak+=np.sin(2*np.pi*k*x+rng.random()*2*np.pi)/np.sqrt(k)
    broad=(broad-broad.min())/np.ptp(broad)
    streak=(streak-streak.min())/np.ptp(streak)
    # Detail blending is centered on half grey. Keep stains subtle and bounded;
    # the building's seed/height tint supplies the broad aging strength.
    value=.51-.11*broad-.10*streak**3*(.6+.4*np.cos(2*np.pi*y)**2)
    return np.clip(np.rint(value[:,:,None]*np.array([1.025,1.,.97])*255),0,255).astype(np.uint8)


def encode(pixels):
    """Legacy RGBA8 DDS: the ordinary shape-material reader rejects DX10 RGBA8.

    Use the same RGB masks as the shipped ground-detail texture. Terrain's
    separate BC7/DX10 texture-array reader is not a compatibility precedent.
    """
    pixels=np.asarray(pixels,dtype=np.uint8)
    size=len(pixels)
    if pixels.shape!=(size,size,3) or size<1 or size&(size-1):
        raise ValueError('Expected a square power-of-two RGB image')
    chain=[];level=pixels
    while True:
        chain.append(np.dstack((level,np.full(level.shape[:2],255,np.uint8))).tobytes())
        if len(level)==1:break
        level=np.rint(level.reshape(len(level)//2,2,len(level)//2,2,3).mean((1,3))).astype(np.uint8)
    header=(b'DDS '+struct.pack('<7I',124,0x2100F,size,size,size*4,0,len(chain))+b'\0'*44+
            struct.pack('<2I4s5I',32,0x41,b'\0'*4,32,0xff,0xff00,0xff0000,0xff000000)+
            struct.pack('<5I',0x401008,0,0,0,0))
    assert len(header)==128
    return header+b''.join(chain)


if __name__=='__main__':
    pixels=texture();Image.fromarray(pixels).save(OUT)
    OUT.with_suffix('.dds').write_bytes(encode(pixels))
    print(OUT.with_suffix('.dds'),pixels.shape,'legacy RGBA8, full mip chain')
