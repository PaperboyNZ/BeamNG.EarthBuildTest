"""Rebuild the bundled font checksum and embedded-license inventory."""
from pathlib import Path
import hashlib,json,struct,re
root=Path(__file__).resolve().parents[1]/'server/buildgen/fonts'
commit='ffebf8c1ee449e544955a7e813c54f9b73848eac'
base='https://raw.githubusercontent.com/notofonts/noto-fonts/'
family_urls={'BarlowCondensed.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-Bold.ttf',
'Amiri-Regular.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf',
'Oswald.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/Oswald%5Bwght%5D.ttf',
'Lora.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/lora/Lora%5Bwght%5D.ttf',
'LibreFranklin.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/librefranklin/LibreFranklin%5Bwght%5D.ttf'}
cjk={'jp':'Japanese','kr':'Korean','sc':'SimplifiedChinese','tc':'TraditionalChinese'}
notices=['Embedded copyright and license metadata for bundled fonts. Full license texts are in this directory.','']
manifest=[]
for path in sorted(root.iterdir()):
    if path.suffix.lower() not in ('.ttf','.otf'): continue
    name=path.name; raw=path.read_bytes(); source=family_urls.get(name)
    if source:
        pass
    elif name.startswith('NotoSansCJK'):
        code=name[len('NotoSansCJK'):len('NotoSansCJK')+2]
        source='https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/'+cjk[code]+'/'+name[:-4]+'-Regular.otf'
    elif re.search(r'-(?:Regular|Bold|Italic|BoldItalic)\.ttf$',name):
        family=re.sub(r'-(?:Regular|Bold|Italic|BoldItalic)\.ttf$','',name);source=base+commit+'/hinted/ttf/'+family+'/'+name
    elif name in ('NotoSansDevanagari.ttf','NotoSansBengali.ttf','NotoSansThai.ttf'):
        family=name[:-4];source=base+'main/hinted/ttf/'+family+'/'+family+'-Regular.ttf'
    if not source: raise ValueError('Unknown font source: '+name)
    manifest.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),source=source))
    count=struct.unpack_from('>H',raw,4)[0];table=None
    for i in range(count):
        tag,_,offset,length=struct.unpack_from('>4sIII',raw,12+i*16)
        if tag==b'name': table=raw[offset:offset+length];break
    if table is None:continue
    _,num,start=struct.unpack_from('>HHH',table,0);rows={}
    for i in range(num):
        platform,enc,lang,key,length,offset=struct.unpack_from('>HHHHHH',table,6+12*i)
        if key not in (0,13,14):continue
        value=table[start+offset:start+offset+length]
        try:value=value.decode('utf-16-be' if platform in (0,3) else 'mac_roman').strip()
        except UnicodeError:continue
        if value and value not in rows.setdefault(key,[]):rows[key].append(value)
    notices.append(name)
    for key in (0,13,14):
        for value in rows.get(key,[]):notices.append('  '+str(key)+': '+value.replace('\n',' '))
    notices.append('')
(root/'FONT-NOTICES.txt').write_text('\n'.join(notices),encoding='utf-8')
(root/'manifest.json').write_text(json.dumps({'version':1,'fonts':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(manifest),'font files indexed')
