"""Export an isolated facade-baking and material-based shadow-detail experiment.

Reads the user's installed stock textures; writes only to the chosen output.
No live server, game installation or active playtest is modified.
"""
import argparse
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import time
from unittest.mock import patch
import zipfile

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import buildings as b
from buildgen import components,facade_bake,freeze_items


class Library:
    def __init__(self,game):
        self.mod=ROOT/'mod/beamng_earth'
        self.materials={}
        for p in (self.mod/'levels/beamng_earth/art/shapes/beamngEarth').glob('*.materials.json'):
            self.materials.update(json.loads(p.read_text()))
        self.files={}
        for p in sorted((game/'content/assets/materials').glob('*.zip')):
            with zipfile.ZipFile(p) as z:
                self.files.update({n.lower():(p,n) for n in z.namelist() if n.lower().endswith(('.png','.dds'))})

    @lru_cache(maxsize=32)
    def texture(self,path):
        rel=path.lstrip('/')
        local=self.mod/rel
        if local.is_file():
            data=local.read_bytes()
        else:
            key=rel.lower()
            if key not in self.files and key.endswith('.png'):key=key[:-4]+'.dds'
            if key not in self.files:raise FileNotFoundError(path)
            archive,name=self.files[key]
            with zipfile.ZipFile(archive) as z:data=z.read(name)
        with Image.open(io.BytesIO(data)) as image:
            if max(image.size)>4096:raise ValueError('source texture exceeds laboratory budget')
            return np.asarray(image.convert('RGB')).copy()

    @lru_cache(maxsize=64)
    def mip(self,path,level,color):
        a=self.texture(path).astype(np.float32)/255.
        if color:a=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
        for _ in range(level):
            if min(a.shape[:2])<2:break
            h,w=a.shape[:2];a=a[:h//2*2,:w//2*2].reshape(h//2,2,w//2,2,3).mean((1,3))
        return a

    def sample_map(self,path,uv,jac,color=False):
        image=self.texture(path);h,w=image.shape[:2]
        footprint=max(np.linalg.norm(jac[0]*[w,h]),np.linalg.norm(jac[1]*[w,h]),1.)
        level=max(0,min(10,int(np.log2(footprint))))
        a=self.mip(path,level,color);h,w=a.shape[:2]
        xy=(uv*np.array([w,-h]))-.5
        lower=np.floor(xy).astype(int);f=xy-lower
        x,y=lower[:,0]%w,lower[:,1]%h;X,Y=(x+1)%w,(y+1)%h
        return ((a[y,x]*(1-f[:,0,None])+a[y,X]*f[:,0,None])*(1-f[:,1,None])+
                (a[Y,x]*(1-f[:,0,None])+a[Y,X]*f[:,0,None])*f[:,1,None])

    def __call__(self,material,uv,tint,jac):
        definition=self.materials[material]
        if definition.get('translucent') or definition.get('alphaTest'):
            raise ValueError('nonopaque source material')
        stage=definition.get('Stages',[{}])[0]
        channels={}
        for channel,field,default in (('color','baseColorMap',1.),('normal','normalMap',None),
                ('roughness','roughnessMap',1.),('metallic','metallicMap',0.),
                ('ao','ambientOcclusionMap',1.),('emissive','emissiveMap',0.)):
            if stage.get(field):value=self.sample_map(stage[field],uv,jac,channel=='color')
            else:value=np.tile((.5,.5,1.) if default is None else (default,)*3,(len(uv),1))
            if channel=='color':
                value=value*np.asarray(stage.get('baseColorFactor',(1,1,1,1)))[:3]
                if stage.get('vertColor',False):value=value*tint
                value=np.where(value<=.0031308,value*12.92,1.055*np.maximum(value,0)**(1/2.4)-.055)
            elif channel in ('roughness','metallic'):
                value=value*stage.get(channel+'Factor',1.) if stage.get(field) else np.full_like(value,stage.get(channel+'Factor',default))
            elif channel=='emissive':
                # Encode each source's existing night intensity/tint into one
                # atlas, with the page material driven at a common 200 nits.
                glow={'bne_bld_facade':((1,1,1),200),'bne_bld_office':((.95,.97,1),70),
                      'bne_bld_shop':((1,.8,.58),30)}.get(material,((0,0,0),0))
                value=value*np.asarray(glow[0])*glow[1]/200.
            channels[channel]=np.clip(np.rint(value*255),0,255).astype(np.uint8)
        return channels


def shadow_candidate(items):
    """Explicitly classify only known micro-components; preserve everything else.

    This diagnostic runs in its own process. Patches are restored on exit and
    never installed into a server worker.
    """
    excluded=[]
    original_facade,original_beam=components.facade,components.beam
    def facade(mesh,template,*args,**kw):
        start=len(mesh.M)
        original_facade(mesh,template,*args,**kw)
        if len(template.indices)==32:
            # Keep all four recess closures. Only the four flat face strips
            # stop casting; otherwise sunlight could leak around recessed glass.
            excluded.extend(range(start+8,len(mesh.M)))
        elif len(template.indices)==20 and template.points[:,2].max()<=.12:
            excluded.extend(range(start,len(mesh.M)))
        # Wider sun hoods/canopies retain their complete shadow geometry.
    def beam(mesh,a,c,radius,mat,sides=8):
        start=len(mesh.M);original_beam(mesh,a,c,radius,mat,sides)
        if radius<=.04:excluded.extend(range(start,len(mesh.M)))
    with patch.object(components,'facade',facade),patch.object(components,'beam',beam):
        mesh=b.build(items)
    p,uv,t,mi,mats,col=mesh
    names=list(mats);mapped=mi.copy();aliases={}
    for index in np.unique(mi[excluded]):
        old=mats[index];name='bne_lab_micro_'+old
        aliases[name]=old;names.append(name)
        choose=np.asarray(excluded,dtype=np.int64)
        choose=choose[mi[choose]==index];mapped[choose]=len(names)-1
    candidate=p,uv,t,mapped,tuple(names),col
    keep=np.ones(len(t),bool);keep[excluded]=False
    caster=p,uv,t[keep],mi[keep],mats,col
    return mesh,candidate,caster,aliases


def dds(image,channel='color'):
    """Uncompressed RGBA8 with a complete mip chain, for diagnostic assets."""
    chain=[];current=image.astype(np.float32)/255.
    if channel=='color':current=np.where(current<=.04045,current/12.92,((current+.055)/1.055)**2.4)
    while True:
        output=current
        if channel=='color':output=np.where(current<=.0031308,current*12.92,1.055*current**(1/2.4)-.055)
        if channel=='normal':
            normal=current*2-1;normal/=np.maximum(np.linalg.norm(normal,axis=2)[:,:,None],1e-20)
            output=(normal+1)/2
        rgb=np.clip(np.rint(output*255),0,255).astype(np.uint8)
        chain.append(np.concatenate((rgb,np.full((*rgb.shape[:2],1),255,np.uint8)),axis=2).tobytes())
        h,w=current.shape[:2]
        if (h,w)==(1,1):break
        current=current.reshape(max(1,h//2),min(2,h),max(1,w//2),min(2,w),3).mean((1,3))
    h,w=image.shape[:2]
    header=(b'DDS '+struct.pack('<7I',124,0x2100F,h,w,w*4,0,len(chain))+b'\0'*44+
            struct.pack('<2I4s5I',32,0x41,b'\0'*4,32,0xff,0xff00,0xff0000,0xff000000)+
            struct.pack('<5I',0x401008,0,0,0,0))
    return header+b''.join(chain)


def atlas(cards,folder,vfs,size=1024,max_pages=4,gutter=8):
    unique={c.signature:c for c in cards};pages=[];slots={};x=y=row=0
    for key,card in sorted(unique.items()):
        h,w=card.pixels['color'].shape[:2];W,H=w+2*gutter,h+2*gutter
        if W>size or H>size:raise ValueError('card exceeds atlas page')
        if not pages:pages.append({k:np.zeros((size,size,3),np.uint8) for k in facade_bake.CHANNELS})
        if x+W>size:x=0;y+=row;row=0
        if y+H>size:
            if len(pages)>=max_pages:raise ValueError('atlas page budget exceeded')
            pages.append({k:np.zeros((size,size,3),np.uint8) for k in facade_bake.CHANNELS});x=y=row=0
        slots[key]=(len(pages)-1,x+gutter,y+gutter,w,h)
        for channel in facade_bake.CHANNELS:
            pages[-1][channel][y:y+H,x:x+W]=np.pad(card.pixels[channel],((gutter,gutter),(gutter,gutter),(0,0)),mode='edge')
        x+=W;row=max(row,H)
    placements={};materials={};nbytes=0
    for page,images in enumerate(pages):
        digest=hashlib.sha256(b''.join(images[k].tobytes() for k in facade_bake.CHANNELS)).hexdigest()[:16]
        name='bne_lab_baked_'+digest;stage={'baseColorFactor':[1,1,1,1],'vertColor':False,
                                           'emissiveFactor':[0,0,0],'emissiveIntensityNits':-1}
        for channel,field in zip(facade_bake.CHANNELS,('baseColorMap','normalMap','roughnessMap','metallicMap','ambientOcclusionMap','emissiveMap')):
            file=f'{digest}_{channel}.dds';data=dds(images[channel],channel);(folder/file).write_bytes(data);nbytes+=len(data)
            stage[field]=vfs+'/'+file
        Image.fromarray(images['color']).save(folder/f'atlas_{page}.png')
        materials[name]={'name':name,'mapTo':name,'class':'Material','version':1.5,'Stages':[stage],
                         'translucent':False,'castShadows':True}
        for key,(pg,x,y,w,h) in slots.items():
            if pg==page:
                placements[key]=(name,((x/size,1-(y+h)/size),((x+w)/size,1-(y+h)/size),
                                       ((x+w)/size,1-y/size),(x/size,1-y/size)))
    return placements,materials,dict(pages=len(pages),unique_facades=len(unique),texture_bytes=nbytes,
                                    uncompressed_diagnostic_textures=True)


def metrics(mesh):
    return dict(vertices=len(mesh[0]),referenced_vertices=len(np.unique(mesh[2])),
                triangles=len(mesh[2]),material_primitives=len(np.unique(mesh[3])))


def private_materials(mesh,library,definitions):
    """Probe lighting changes must never modify materials on the user's map."""
    names=list(mesh[4])
    for index in np.unique(mesh[3]):
        source=names[index]
        if source.startswith('bne_lab_'):continue
        name='bne_lab_source_'+source
        definition=json.loads(json.dumps(library.materials[source]));definition.pop('persistentId',None)
        definition.update(name=name,mapTo=name);definitions[name]=definition;names[index]=name
    return (*mesh[:4],tuple(names),mesh[5])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'build/component-rendering/lab')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    folder=args.out/'mod/levels/beamng_earth/art/shapes/buildingRenderLab';folder.mkdir(parents=True,exist_ok=True)
    vfs='/levels/beamng_earth/art/shapes/buildingRenderLab'
    library=Library(args.game)
    from test_buildgen_regions import building as house
    from test_buildgen_regional_blocks import building as block
    from test_buildgen_city import make as city
    from buildgen.topology import Footprint
    fixtures=[('house',house('nz_temperate')),('block',block()),('office',city()[0]),
              ('courtyard',house('italy_regional',fp=Footprint(((0,0),(24,0),(24,22),(0,22)),
                                      (((8,6),(16,6),(16,16),(8,16)),))))]
    rows=[];allcards=[];materials={}
    for name,spec in fixtures:
        items=freeze_items([(spec,0.,0.)]);near,hybrid,casters,aliases=shadow_candidate(items)
        lite=b.build(items,lite=True)
        start=time.perf_counter();cards,notes=facade_bake.cards(lite,items[0][0],0.,0.,library)
        ms=1000*(time.perf_counter()-start);allcards.extend(cards)
        for alias,source in aliases.items():
            definition=json.loads(json.dumps(library.materials[source]));definition.pop('persistentId',None)
            definition.update(name=alias,mapTo=alias,castShadows=False);materials[alias]=definition
        for suffix,mesh in (('near',near),('lite',lite),('shadow_detail',hybrid),('shadow_geometry',casters)):
            b.write(str(folder/f'{name}_{suffix}.cdae'),private_materials(mesh,library,materials))
        rows.append((name,spec,lite,cards,dict(name=name,near=metrics(near),lite=metrics(lite),
                    shadow_candidate=metrics(hybrid),shadow_casters=metrics(casters),
                    candidate_shadow_triangle_reduction_pct=100*(1-len(casters[2])/len(near[2])),
                    baked_facades=len(cards),cold_bake_ms=ms,retained_faces=notes)))
        print(name,'cards',len(cards),'shadow triangles',len(near[2]),'->',len(casters[2]),flush=True)
    placements,baked_materials,atlas_stats=atlas(allcards,folder,vfs);materials.update(baked_materials)
    report={'status':'experimental_offline_assets_not_enabled_in_streaming','atlas':atlas_stats,'fixtures':[]}
    for name,spec,lite,cards,row in rows:
        baked=facade_bake.assemble(lite,cards,placements)
        b.write(str(folder/f'{name}_baked.cdae'),private_materials(baked,library,materials))
        row['baked']=metrics(baked);row['lite_triangle_reduction_pct']=100*(1-len(baked[2])/len(lite[2]))
        report['fixtures'].append(row)
    (folder/'render_lab.materials.json').write_text(json.dumps(materials,indent=2)+'\n')
    # Include source materials and the mod's small custom textures. Game stock
    # assets continue to resolve from the user's installation.
    source=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
    target=args.out/'mod/levels/beamng_earth/art/shapes/beamngEarth';target.mkdir(parents=True,exist_ok=True)
    import shutil
    for p in source.iterdir():
        if p.suffix in ('.png','.dds'):shutil.copy2(p,target/p.name)
    extension=args.out/'mod/lua/ge/extensions';extension.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'probes/building_render_lab.lua',extension/'beamngEarth_renderLab.lua')
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    # Package only current referenced assets, not stale content-addressed maps
    # left by earlier experiments in the same output folder.
    package_files={folder/'render_lab.materials.json',extension/'beamngEarth_renderLab.lua'}
    for name,_,_,_,_ in rows:
        for mode in ('near','lite','baked','shadow_detail','shadow_geometry'):
            package_files.add(folder/f'{name}_{mode}.cdae')
    for definition in materials.values():
        for key,value in definition['Stages'][0].items():
            if key.endswith('Map') and isinstance(value,str) and value.startswith('/levels/'):
                path=args.out/'mod'/value.lstrip('/')
                if not path.is_file():raise FileNotFoundError(value)
                package_files.add(path)
    with zipfile.ZipFile(args.out/'building_render_lab.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_files):archive.write(path,path.relative_to(args.out/'mod').as_posix())
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
