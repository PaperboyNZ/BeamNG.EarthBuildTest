"""Bundled OFL font selection and fail-closed shaping capability checks."""
from functools import lru_cache
from pathlib import Path
import hashlib
import unicodedata
from . import font_bootstrap
import PIL
from PIL import ImageFont, features

ROOT=Path(__file__).with_name('fonts')
AVAILABLE=frozenset(p.name for p in ROOT.iterdir() if p.is_file())
VARIABLE_WEIGHTS={'LibreFranklin.ttf':600, 'Oswald.ttf':600, 'Lora.ttf':500}
ROLES={'clinical':'NotoSans-Regular.ttf', 'trade':'BarlowCondensed.ttf', 'big_box':'Oswald.ttf',
       'artisan':'Lora.ttf', 'grocer':'LibreFranklin.ttf',
       'noto_serif':'NotoSerif-Regular.ttf', 'arabic_naskh':'NotoNaskhArabic-Regular.ttf',
       'arabic_kufi':'NotoKufiArabic-Regular.ttf'}
FALLBACK=('NotoSans-Regular.ttf','NotoSansArmenian-Regular.ttf','NotoSansGeorgian-Regular.ttf',
          'NotoSansHebrew-Regular.ttf','NotoSansArabic-Regular.ttf','Amiri-Regular.ttf','NotoSansDevanagari.ttf',
          'NotoSansBengali.ttf','NotoSansThai.ttf','NotoSansLao-Regular.ttf','NotoSansLisu-Regular.ttf',
          'NotoSansCJKsc.otf','NotoSansCJKjp.otf','NotoSansCJKkr.otf','NotoSansCJKtc.otf')
SCRIPT_FALLBACK=tuple(sorted(n for n in AVAILABLE if n.startswith('NotoSans') and n.endswith('-Regular.ttf'))) + ('NotoSerifTibetan-Regular.ttf',)

class TextUnavailable(ValueError):
    """Text must remain unlabelled; the containing tile must remain usable."""

@lru_cache(maxsize=1)
def revision():
    h=hashlib.sha256()
    h.update(repr(sorted(VARIABLE_WEIGHTS.items())).encode())
    h.update(repr((PIL.__version__, features.version('raqm'), features.version('harfbuzz'), features.version('fribidi'))).encode())
    for p in sorted(ROOT.iterdir()):
        if p.suffix.lower() not in ('.ttf','.otf'): continue
        h.update(p.name.encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

@lru_cache(maxsize=128)
def font(path,size):
    result=ImageFont.truetype(path,size)
    weight=VARIABLE_WEIGHTS.get(Path(path).name)
    if weight is not None:
        axes=result.get_variation_axes()
        values=[max(a['minimum'],min(a['maximum'],weight)) if a['name'].lower()==b'weight' else a['default'] for a in axes]
        result.set_variation_by_axes(values)
    return result

@lru_cache(maxsize=16384)
def covered(path,ch):
    f=font(path,32); a=f.getmask(ch); b=f.getmask('\U0010ffff')
    return (a.size,bytes(a)) != (b.size,bytes(b))

def valid_role(role):
    return role in ROLES or any(role == base+suffix for base in ROLES for suffix in ('_bold','_italic','_bold_italic'))

@lru_cache(maxsize=4096)
def resolve(value,role='clinical',locale=''):
    if not valid_role(role): raise ValueError('unsupported typography role')
    base=role
    weight='Regular'
    for suffix, variant in (('_bold_italic','BoldItalic'),('_italic','Italic'),('_bold','Bold')):
        if base.endswith(suffix): base=base[:-len(suffix)]; weight=variant; break
    # Conservative: require the complete HarfBuzz/FriBidi layout engine for
    # every non-ASCII line; this includes scripts outside our explicit list.
    complex_text=any(ord(c)>127 for c in value)
    if complex_text and not features.check('raqm'):
        raise TextUnavailable('text requires RAQM shaping and bidirectional support')
    if any(0x1800 <= ord(c) <= 0x18af for c in value):
        raise TextUnavailable('Mongolian text requires vertical layout')
    # A single shaping run preserves ligatures, contextual shaping and bidi.
    # Prefer Japanese/Korean forms when their distinctive syllabaries appear.
    names=list(FALLBACK)+list(SCRIPT_FALLBACK)
    if base in ('artisan','noto_serif'):
        names=[n.replace('NotoSans','NotoSerif') if n in (
            'NotoSans-Regular.ttf','NotoSansArmenian-Regular.ttf','NotoSansGeorgian-Regular.ttf',
            'NotoSansHebrew-Regular.ttf','NotoSansLao-Regular.ttf') else n for n in names]
    preferred={'ja':'NotoSansCJKjp.otf','ko':'NotoSansCJKkr.otf','zh-Hans':'NotoSansCJKsc.otf','zh-Hant':'NotoSansCJKtc.otf'}.get(locale)
    if locale and not preferred: raise ValueError('unsupported CJK locale')
    if preferred: names.remove(preferred); names.insert(0,preferred)
    elif any('\u3040'<=c<='\u30ff' for c in value): names.remove('NotoSansCJKjp.otf'); names.insert(0,'NotoSansCJKjp.otf')
    elif any('\uac00'<=c<='\ud7af' for c in value): names.remove('NotoSansCJKkr.otf'); names.insert(0,'NotoSansCJKkr.otf')
    first=ROLES[base]
    variant=first.replace('-Regular.ttf','-'+weight+'.ttf')
    names.insert(0,variant if variant in AVAILABLE else first)
    # Prefer the dedicated script family over a broad Latin family that happens
    # to include that script. Explicit Arabic display families remain choices.
    scripts=((0x0900,0x097f,'NotoSansDevanagari.ttf'),(0x0980,0x09ff,'NotoSansBengali.ttf'),
             (0x0a00,0x0a7f,'NotoSansGurmukhi-Regular.ttf'),(0x0a80,0x0aff,'NotoSansGujarati-Regular.ttf'),
             (0x0b00,0x0b7f,'NotoSansOriya-Regular.ttf'),(0x0b80,0x0bff,'NotoSansTamil-Regular.ttf'),
             (0x0c00,0x0c7f,'NotoSansTelugu-Regular.ttf'),(0x0c80,0x0cff,'NotoSansKannada-Regular.ttf'),
             (0x0d00,0x0d7f,'NotoSansMalayalam-Regular.ttf'),(0x0d80,0x0dff,'NotoSansSinhala-Regular.ttf'),
             (0x0e00,0x0e7f,'NotoSansThai.ttf'),(0x0e80,0x0eff,'NotoSansLao-Regular.ttf'),
             (0x0f00,0x0fff,'NotoSerifTibetan-Regular.ttf'),(0x1000,0x109f,'NotoSansMyanmar-Regular.ttf'),
             (0x1780,0x17ff,'NotoSansKhmer-Regular.ttf'),(0x1200,0x137f,'NotoSansEthiopic-Regular.ttf'),
             (0x0700,0x074f,'NotoSansSyriac-Regular.ttf'),(0x0780,0x07bf,'NotoSansThaana-Regular.ttf'),
             (0x13a0,0x13ff,'NotoSansCherokee-Regular.ttf'),(0x1400,0x167f,'NotoSansCanadianAboriginal-Regular.ttf'),
             (0x2d30,0x2d7f,'NotoSansTifinagh-Regular.ttf'),(0xa000,0xa4cf,'NotoSansYi-Regular.ttf'),
             (0xa500,0xa63f,'NotoSansVai-Regular.ttf'),
             (0x0530,0x058f,'NotoSansArmenian-Regular.ttf'),(0x10a0,0x10ff,'NotoSansGeorgian-Regular.ttf'),
             (0x0590,0x05ff,'NotoSansHebrew-Regular.ttf'),(0x0600,0x06ff,'NotoSansArabic-Regular.ttf'),
             (0xa4d0,0xa4ff,'NotoSansLisu-Regular.ttf'))
    for low,high,dedicated in scripts:
        if not any(low <= ord(c) <= high for c in value): continue
        if base in ('arabic_naskh','arabic_kufi') and low == 0x0600: break
        if base in ('artisan','noto_serif') and 'NotoSans' in dedicated:
            alternate=dedicated.replace('NotoSans','NotoSerif')
            if alternate in AVAILABLE: dedicated=alternate
        alternate=dedicated.replace('-Regular.ttf','-'+weight+'.ttf')
        if alternate in AVAILABLE: dedicated=alternate
        names.insert(0,dedicated)
        break
    for name in dict.fromkeys(names):
        alternate=name.replace('-Regular.ttf','-'+weight+'.ttf')
        if alternate in AVAILABLE: name=alternate
        path=str(ROOT/name)
        if name in AVAILABLE and all(c.isspace() or unicodedata.category(c)=='Cf' or covered(path,c) for c in value):
            return path
    raise TextUnavailable('no bundled font covers the complete text')
