"""Cached, bounded text panels prepared once per directory revision."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import hashlib
import math
import os
import unicodedata
import uuid
from . import font_bootstrap  # Must run before Pillow imports its text engine.
from PIL import Image, ImageDraw

VERSION = 5
WIDTH, HEADER, ROW, FOOTER, PHYSICAL_WIDTH = 512, .65, .40, .12, 1.4
STYLES = {'metal': ((35,42,44),(243,241,228)), 'timber': ((48,57,49),(243,241,228)), 'light': ((239,235,222),(30,43,43))}
PANELS = (((237,229,207),(53,48,38)), ((35,67,61),(244,238,214)), ((39,81,111),(247,242,230)), ((155,76,48),(255,247,231)), ((67,59,76),(247,241,228)), ((217,221,214),(42,57,54)))

@dataclass(frozen=True, slots=True)
class Board:
    material: str
    filename: str
    png: bytes
    used_ratio: float
    physical_width: float
    physical_height: float
    shortened: tuple
    revision: str

    def material_definition(self, vfs_dir):
        return {'name':self.material, 'mapTo':self.material, 'class':'Material', 'version':1.5,
                'persistentId':str(uuid.uuid5(uuid.NAMESPACE_URL,self.material)),
                'Stages':[{'baseColorMap':vfs_dir.rstrip('/')+'/'+self.filename, 'metallicFactor':0, 'roughnessFactor':.8}, {}, {}, {}]}

from . import property_fonts as fonts

def _palette(value):
    if value is None: return None
    if not isinstance(value,(tuple,list)) or len(value)!=3: raise ValueError('palette requires background, foreground and accent')
    result=[]
    for color in value:
        if not isinstance(color,(tuple,list)) or len(color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in color):
            raise ValueError('palette colors require three integer RGB components')
        result.append(tuple(color))
    return tuple(result)

def _panel_color(palette,index):
    background,_,accent=palette
    weight=.28 if index%2==0 else .55
    color=tuple(round(a*(1-weight)+b*weight) for a,b in zip(background,accent))
    def linear(v):
        c=v/255
        return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
    lum=sum(w*linear(v) for w,v in zip((.2126,.7152,.0722),color))
    return color, ((0,0,0) if (lum+.05)/.05 >= 1.05/(lum+.05) else (255,255,255))

def _clusters(value):
    """Keep combining marks, variation selectors and joiner sequences together."""
    clusters=[]
    for char in value:
        code=ord(char)
        continuation=(unicodedata.category(char).startswith('M') or char == '\u200d' or
                      0xfe00 <= code <= 0xfe0f or 0xe0100 <= code <= 0xe01ef or
                      0x1f3fb <= code <= 0x1f3ff)
        if clusters and (continuation or clusters[-1].endswith('\u200d')):
            clusters[-1]+=char
        else:
            clusters.append(char)
    return clusters

def _fit(draw,value,box,path,maximum,minimum,color):
    if not value: return False
    role,locale = path if isinstance(path, tuple) else (path, '')
    path=fonts.resolve(value,role,locale)
    x0,y0,x1,y1=box
    for size in range(maximum,minimum-1,-2):
        f=fonts.font(path,size)
        if draw.textlength(value,font=f)<=x1-x0 and size*1.24<=y1-y0:
            draw.text(((x0+x1)/2,(y0+y1)/2),value,font=f,fill=color,anchor='mm'); return False
    f=fonts.font(path,minimum); clusters=_clusters(value); short=value
    while clusters and draw.textlength(short+'…',font=f)>x1-x0:
        clusters.pop(); short=''.join(clusters)
    draw.text(((x0+x1)/2,(y0+y1)/2),short+'…',font=f,fill=color,anchor='mm'); return True

def _pixel_width(value):
    if type(value) is not int or value not in (256,512,1024):
        raise ValueError('text pixel width must be 256, 512 or 1024')
    return value

@lru_cache(maxsize=128)
def _prepare(directory,path,font_revision,palette,pixel_width):
    revision=hashlib.sha256((str(VERSION)+directory.digest+font_revision+repr(palette)+str(pixel_width)).encode()).hexdigest()
    result=[]
    for page,tenants in enumerate(directory.boards):
        physical_height=HEADER+len(tenants)*ROW+FOOTER
        used_base=round(WIDTH*physical_height/PHYSICAL_WIDTH)
        used=round(pixel_width*physical_height/PHYSICAL_WIDTH); height=1 << (used-1).bit_length()
        resolution=pixel_width/WIDTH
        background,foreground=STYLES[directory.style] if palette is None else palette[:2]
        image=Image.new('RGB',(pixel_width,height),background); draw=ImageDraw.Draw(image)
        def fit(value,box,role,maximum,minimum,color):
            return _fit(draw,value,tuple(v*resolution for v in box),role,
                        max(4,round(maximum*resolution)),max(4,round(minimum*resolution)),color)
        scale=WIDTH/PHYSICAL_WIDTH; head=round(HEADER*scale); shortened=[]
        if fit(directory.number,(20,10,WIDTH-20,head*.58),path,116,36,foreground): shortened.append('address:number')
        if fit(directory.street,(20,head*.58,WIDTH-20,head-8),path,32,18,foreground): shortened.append('address:street')
        for i,tenant in enumerate(tenants):
            y0=round((HEADER+i*ROW)*scale); y1=round((HEADER+(i+1)*ROW)*scale)
            bg,fg=(PANELS[int(hashlib.sha256(tenant.identity.encode()).hexdigest()[:4],16)%len(PANELS)]
                   if palette is None else _panel_color(palette,i))
            draw.rectangle(tuple(round(v*resolution) for v in (6,y0+4,WIDTH-7,y1-4)),fill=bg)
            if tenant.unit and fit(tenant.unit,(15,y0+8,WIDTH-15,y0+34),path,22,16,fg): shortened.append(tenant.identity+':unit')
            top=y0+37 if tenant.unit else y0+10; bottom=y1-35 if tenant.descriptor else y1-10
            if fit(tenant.name,(18,top,WIDTH-18,bottom),tenant.typography_role,48,22,fg): shortened.append(tenant.identity+':name')
            if tenant.descriptor and fit(tenant.descriptor,(18,y1-34,WIDTH-18,y1-6),path,19,15,fg): shortened.append(tenant.identity+':descriptor')
        caption=f'{page+1} / {len(directory.boards)}' if len(directory.boards)>1 else directory.property_name
        if fit(caption,(18,used_base-round(FOOTER*scale),WIDTH-18,used_base-3),path,17,13,foreground): shortened.append('property_name')
        out=BytesIO(); image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out,format='PNG')
        stem=f'bne_directory_{revision[:24]}_{page}'
        result.append(Board(stem+'_face',stem+'.png',out.getvalue(),used/height,PHYSICAL_WIDTH,physical_height,tuple(shortened),revision))
    return tuple(result)

def prepare(directory,palette=None,pixel_width=512):
    """Return immutable PNG/material records, cached by data and font revision.

    Face UV bounds are (0,0)-(1,used_ratio); caller chooses face winding.
    """
    return _prepare(directory,'clinical',fonts.revision(),_palette(palette),_pixel_width(pixel_width))

@lru_cache(maxsize=128)
def _fascia(name, path, font_revision, aspect, palette, pixel_width):
    revision=hashlib.sha256((str(VERSION)+'fascia'+name+repr(path)+font_revision+repr(aspect)+repr(palette)+str(pixel_width)).encode('utf-8')).hexdigest()
    used=round(pixel_width/aspect)
    height=max(64,1 << (used-1).bit_length())
    background,foreground,accent=palette or ((35,42,44),(243,241,228),(35,42,44))
    image=Image.new('RGB',(pixel_width,height),background); draw=ImageDraw.Draw(image)
    if palette is not None: draw.rectangle((1,1,pixel_width-2,used-2),outline=accent,width=max(1,round(used*.018)))
    margin=max(3,round(used*.0625))
    resolution=pixel_width/1024
    shortened=_fit(draw,name,(24*resolution,margin,pixel_width-24*resolution,used-margin),path,
                   max(4,round(min(160,max(12,round((1024/aspect)*.625)))*resolution)),
                   max(4,round(max(8,round((1024/aspect)*.14))*resolution)),foreground)
    out=BytesIO(); image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out,format='PNG')
    stem='bne_fascia_'+revision[:24]
    return Board(stem+'_face',stem+'.png',out.getvalue(),used/height,aspect,1.,('name',) if shortened else (),revision)

def prepare_fascia(name, style='clinical', locale='', aspect=4., palette=None, pixel_width=1024):
    """Prepare a single named store fascia; no name or unit is invented."""
    if not isinstance(name,str) or not name.strip() or len(name)>160 or any(unicodedata.category(c) in ('Cc','Cs') for c in name):
        raise ValueError('invalid fascia name')
    name=unicodedata.normalize('NFC',' '.join(name.split()))
    if not fonts.valid_role(style): raise ValueError('unsupported typography role')
    if type(aspect) not in (int,float) or not math.isfinite(aspect) or not 2. <= aspect <= 24.:
        raise ValueError('fascia aspect must be finite and between 2 and 24')
    # Quantize to a stable 1/64 aspect budget to avoid unbounded near-identical
    # textures caused by floating point site geometry differences.
    aspect=round(float(aspect)*64)/64
    return _fascia(name,(style,locale),fonts.revision(),aspect,_palette(palette),_pixel_width(pixel_width))
