"""Build seamless, irregular surface deposits without per-building assets."""
from pathlib import Path
import struct
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering.png'


def _noise(rng,x,y,cells):
    """Periodic value noise; quintic interpolation keeps tile edges smooth."""
    grid=rng.random((cells,cells))
    px=x*cells;py=y*cells
    ix=np.floor(px).astype(int);iy=np.floor(py).astype(int)
    fx=px-ix;fy=py-iy
    sx=fx**3*(fx*(fx*6-15)+10);sy=fy**3*(fy*(fy*6-15)+10)
    a=grid[iy%cells,ix%cells]*(1-sx)+grid[iy%cells,(ix+1)%cells]*sx
    c=grid[(iy+1)%cells,ix%cells]*(1-sx)+grid[(iy+1)%cells,(ix+1)%cells]*sx
    return a*(1-sy)+c*sy


def texture(size=256):
    rng=np.random.default_rng(20261102)
    y,x=np.mgrid[0:size,0:size]/size
    # Two-dimensional domain warping breaks up aligned cells and straight runs.
    wx=x+.16*(_noise(rng,x,y,4)-.5)
    wy=y+.16*(_noise(rng,x,y,4)-.5)
    broad=.60*_noise(rng,wx,wy,5)+.28*_noise(rng,wx,wy,11)+.12*_noise(rng,wx,wy,23)
    patches=np.clip((broad-.27)/.48,0.,1.)
    patches=patches*patches*(3-2*patches)
    pores=_noise(rng,wx,wy,55)
    # Mostly clean paint, soft irregular deposits, and sparse granular edges.
    # No one-dimensional streak signal or preferred diagonal direction.
    value=.505-.145*patches-.022*pores*patches
    return np.clip(np.rint(value[:,:,None]*np.array([1.012,1.,.987])*255),0,255).astype(np.uint8)


def roughness(pixels):
    """Linear roughness on the same UV1 as dirt: stained patches are rougher.

    A high floor prevents low values in stock zinc/slate maps restoring gloss.
    Keep this shared, original map independent of proprietary game assets.
    """
    dirt=np.clip((.51-pixels[:,:,1].astype(float)/255.)/.30,0.,1.)
    value=np.rint((.84+.15*dirt)*255).astype(np.uint8)
    return np.repeat(value[:,:,None],3,axis=2)


def streak_texture(size=256):
    """The original streaky texture, retained exactly for the roof-stain blend."""
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
    value=.51-.18*broad-.18*streak**3*(.6+.4*np.cos(2*np.pi*y)**2)
    return np.clip(np.rint(value[:,:,None]*np.array([1.025,1.,.97])*255),0,255).astype(np.uint8)


def packed_texture(size=256):
    # RGB remains a fully usable organic fallback on engines without the hook.
    # The streak map's green/luminance signal is linear data in the alpha lane.
    return np.dstack((texture(size),streak_texture(size)[:,:,1]))


def encode(pixels):
    """Legacy RGBA8 DDS: the ordinary shape-material reader rejects DX10 RGBA8.

    Use the same RGB masks as the shipped ground-detail texture. Terrain's
    separate BC7/DX10 texture-array reader is not a compatibility precedent.
    """
    pixels=np.asarray(pixels,dtype=np.uint8)
    size=len(pixels)
    if pixels.shape not in ((size,size,3),(size,size,4)) or size<1 or size&(size-1):
        raise ValueError('Expected a square power-of-two RGB or RGBA image')
    chain=[];level=pixels if pixels.shape[2]==4 else np.dstack((pixels,np.full((size,size),255,np.uint8)))
    while True:
        chain.append(level.tobytes())
        if len(level)==1:break
        level=np.rint(level.reshape(len(level)//2,2,len(level)//2,2,4).mean((1,3))).astype(np.uint8)
    header=(b'DDS '+struct.pack('<7I',124,0x2100F,size,size,size*4,0,len(chain))+b'\0'*44+
            struct.pack('<2I4s5I',32,0x41,b'\0'*4,32,0xff,0xff00,0xff0000,0xff000000)+
            struct.pack('<5I',0x401008,0,0,0,0))
    assert len(header)==128
    return header+b''.join(chain)


if __name__=='__main__':
    pixels=texture();Image.fromarray(pixels).save(OUT)
    OUT.with_suffix('.dds').write_bytes(encode(pixels))
    OUT.with_name('bne_weathering_roughness.data.dds').write_bytes(encode(roughness(pixels)))
    Image.fromarray(streak_texture()).save(OUT.with_name('bne_weathering_streaks.png'))
    OUT.with_name('bne_weathering_blend.dds').write_bytes(encode(packed_texture()))
    print(OUT.with_suffix('.dds'),pixels.shape,'legacy RGBA8, full mip chain')
