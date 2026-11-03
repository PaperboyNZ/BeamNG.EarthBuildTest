"""Offline review of the authored meshes and their actual sign textures."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from buildgen import font_bootstrap
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
import numpy as np
import buildings as b
from buildgen import freeze_items,property_assets as assets,property_sign_text as text
from buildgen.property_palette import resolve as sign_palette
from buildgen.topology import Footprint
from buildgen.context import Context
from sitegen.property_directories import Directory,Tenant
from building_preview import raster

FAMILIES=(
    ('grocery_store','grocery_store',14,12,1,4.2,'Māia Fresh Foods',(-36.85,174.76)),
    ('supermarket','supermarket',42,24,1,6.0,'HARBOUR MARKET',(-43.53,172.63)),
    ('strip_shops','strip_shops',48,14,1,4.3,'Riverside Shops',(51.5,-.1)),
    ('trade_units','trade_units',52,25,1,6.0,'NORTHSIDE WORKSHOPS',(-36.85,174.76)),
    ('clinic','clinic',24,16,2,7.2,'Central Medical',(35.67,139.75)),
    ('hospital','hospital',54,25,4,15.0,'Harbour Hospital',(1.3,103.8)),
)


def fixture(row):
    kind,cls,w,d,floors,height,name,location=row
    fp=Footprint(((0,0),(w,0),(w,d),(0,d)))
    identity=dict(kind=kind,status='supported',display_name=name,revision=kind,occupants=(),size_modifier=None)
    s=b.plan(np.asarray(fp.outer),dict(_footprint=fp,_property_identity=identity,
        _context=Context(location=location),seed_id=kind,**{'class':cls,'num_floors':floors,'height':height,'roof_shape':'flat'}))
    s.gring=np.zeros(4)
    items=[(s,0.,0.)]
    props=b.doors(items,[(np.array([(-50.,-12.),(w+50.,-12.)]),3.,'residential',False)],0,0,ground=lambda xy:np.zeros(len(xy)))
    return freeze_items(items),props


def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'review'
    out.mkdir(parents=True,exist_ok=True)
    fontpath=ROOT/'server/buildgen/fonts/NotoSans-Regular.ttf'
    heading=ImageFont.truetype(str(fontpath),24);small=ImageFont.truetype(str(fontpath),16)
    canvas=Image.new('RGB',(1560,1000),'#e8edf0');draw=ImageDraw.Draw(canvas)
    draw.text((24,14),'COMMERCIAL PROPERTIES / STAGE ONE',font=heading,fill='#20323d')
    draw.text((24,49),'Actual generated geometry • fictional review names • approximate material lighting',font=small,fill='#53636b')
    report=[]
    definitions={}
    asset_vfs='/levels/beamng_earth/art/shapes/beamngEarth/commercial_review'
    for i,row in enumerate(FAMILIES):
        items,props=fixture(row);m=assets.Mesh();m.append(b.build(items));extra,boards=assets.visuals(items)
        for part in extra:m.append(part)
        textures={a.material:Image.open(BytesIO(a.png)) for a in boards}
        x=(i%3)*520;y=90+(i//3)*440
        canvas.paste(raster(m.arrays(),props,[],520,360,b,tight=True,texture_images=textures),(x,y))
        draw.text((x+20,y+364),row[0].replace('_',' ').title(),font=heading,fill='#20323d')
        s=items[0][0]
        from buildgen.property_programme import for_spec
        p=for_spec(s)
        draw.text((x+20,y+398),p.regional_style.replace('_',' ') if p else 'NO PROGRAMME',font=small,fill='#53636b')
        report.append(dict(kind=row[0],preset=s.inference.selection.preset.id,vertices=len(m.points),triangles=len(m.tris),named_panels=len(boards)))
        b.write(str(out/(row[0]+'.cdae')),m.arrays())
        for board in boards:
            (out/board.filename).write_bytes(board.png)
            definitions[board.material]=board.material_definition(asset_vfs)
    canvas.save(out/'building-preview.png')
    directory=Directory('demo:lot','6','MAIN ROAD','',tuple(Tenant('demo:'+str(i),'demo:member',name,'UNIT '+str(i+1),'')
        for i,name in enumerate(('Harbour Bakery','Māia Design','Willow & Blue','Northside Workshop'))),'metal','geometry-preview-v1')
    palette=sign_palette(fixture(FAMILIES[0])[0][0][0])
    board=text.prepare(directory,palette=palette)[0]
    assets_list=[('Property directory',assets.directory(board,palette=palette)),('Trolley shelter',assets.trolley_shelter()),
        ('Entrance bench',assets.furniture('bench')),('Bike stand',assets.furniture('bike_rack')),
        ('Service cabinet',assets.furniture('service_cabinet')),('Planter and bollard',assets.furniture('planter'))]
    assets_list[-1][1].append(assets.furniture('bollard'),lambda p:p+(.9,0,0))
    canvas=Image.new('RGB',(1560,1000),'#e8edf0');draw=ImageDraw.Draw(canvas)
    draw.text((24,14),'PROPERTY FURNITURE / AUTHORED GEOMETRY',font=heading,fill='#20323d')
    draw.text((24,49),'Metre-scale reusable meshes • shared-site clearance placement • visual-only runtime props',font=small,fill='#53636b')
    for i,(label,m) in enumerate(assets_list):
        x=i%3*520;y=90+i//3*440
        canvas.paste(raster(m.arrays(),[],[],520,360,b,tight=True,camera=(.55,-2.,.85),
            texture_images={board.material:Image.open(BytesIO(board.png))}),(x,y))
        draw.text((x+20,y+364),label,font=heading,fill='#20323d')
        draw.text((x+20,y+398),str(len(m.tris))+' triangles',font=small,fill='#53636b')
        b.write(str(out/(label.lower().replace(' ','_')+'.cdae')),m.arrays())
    (out/board.filename).write_bytes(board.png)
    definitions[board.material]=board.material_definition(asset_vfs)
    (out/'main.materials.json').write_text(json.dumps(definitions,indent=2)+'\n')
    canvas.save(out/'furniture-preview.png')
    palette_sheet=Image.new('RGB',(1560,540),'#e8edf0');pd=ImageDraw.Draw(palette_sheet)
    pd.text((24,14),'SIGN COLOURS / REGION + BUILDING',font=heading,fill='#20323d')
    from dataclasses import replace
    samples=(('NZ / painted green','nz_temperate',(.30,.50,.36)),
             ('Britain / warm masonry','eu_atlantic',(.64,.36,.27)),
             ('Japan / pale concrete','jp_temperate',(.88,.89,.86)),
             ('Tropics / ochre render','tropical_humid',(.85,.63,.34)))
    original=fixture(FAMILIES[0])[0][0][0]
    for i,(label,region,colour) in enumerate(samples):
        env=replace(original.inference.selection.environment,region=region)
        inference=replace(original.inference,selection=replace(original.inference.selection,environment=env))
        spec=replace(original,inference=inference,facade=b.custom_look(b.PANEL,colour))
        colors=sign_palette(spec);board=text.prepare(directory,palette=colors)[0]
        x=i*390
        pd.rectangle((x+20,70,x+370,106),fill=tuple(round(v*255) for v in colour))
        pd.text((x+20,116),label,font=small,fill='#20323d')
        m=assets.directory(board,palette=colors)
        palette_sheet.paste(raster(m.arrays(),[],[],390,360,b,tight=True,camera=(.15,-2.,.45),
            texture_images={board.material:Image.open(BytesIO(board.png))}),(x,155))
    palette_sheet.save(out/'palette-preview.png')
    (out/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
