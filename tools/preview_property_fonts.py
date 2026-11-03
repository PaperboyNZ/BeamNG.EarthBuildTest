"""Render a contact sheet from the exact runtime fascia pipeline."""
from pathlib import Path
import sys
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from buildgen import property_sign_text as sign, property_fonts as fonts
from PIL import Image, ImageDraw

# Text is illustrative, not a source of business identities.
SAMPLES=[
('English','Market Street','grocer',''),('French','Marché du Centre','grocer',''),('Spanish','Mercado Central','grocer',''),('Portuguese','Mercado da Praça','grocer',''),
('German','Bäckerei Müller','artisan',''),('Italian','Bottega Centrale','artisan',''),('Dutch','De Bakkerij','artisan',''),('Polish','Piekarnia Miejska','artisan',''),
('Czech','Městská pekárna','artisan',''),('Slovak','Mestská pekáreň','artisan',''),('Turkish','Merkez Çarşı','trade',''),('Vietnamese','Cửa hàng trung tâm','grocer',''),
('Indonesian','Toko pusat','trade',''),('Swahili','Duka la Mji','trade',''),('Māori','Te Whare Kai','grocer',''),('Samoan','Faleoloa Tutotonu','grocer',''),
('Greek','Κεντρική Αγορά','clinical',''),('Russian','Центральный магазин','clinical',''),('Ukrainian','Центральний магазин','clinical',''),('Armenian','Կենտրոնական խանութ','artisan',''),
('Georgian','ცენტრალური მაღაზია','clinical',''),('Hebrew','חנות מרכזית','clinical',''),('Arabic','متجر المدينة','arabic_naskh',''),('Arabic / Latin','Cafe متجر','arabic_kufi',''),
('Hindi','केंद्रीय दुकान','clinical',''),('Bengali','কেন্দ্রীয় দোকান','clinical',''),('Thai','ร้านค้ากลาง','clinical',''),('Lao','ຮ້ານຄ້າ','clinical',''),
('Japanese','中央商店','clinical','ja'),('Korean','중앙 상점','clinical','ko'),('Chinese simplified','中央商店','clinical','zh-Hans'),('Chinese traditional','中央商店','clinical','zh-Hant'),
('Tamil','தமிழ் கடை','clinical',''),('Telugu','తెలుగు దుకాణం','clinical',''),('Gujarati','ગુજરાતી દુકાન','clinical',''),('Kannada','ಕನ್ನಡ ಅಂಗಡಿ','clinical',''),
('Malayalam','മലയാളം കട','clinical',''),('Punjabi','ਪੰਜਾਬੀ ਦੁਕਾਨ','clinical',''),('Odia','ଓଡ଼ିଆ ଦୋକାନ','clinical',''),('Sinhala','සිංහල කඩය','clinical',''),
('Burmese','မြန်မာ','clinical',''),('Khmer','ភាសាខ្មែរ','clinical',''),('Tibetan','བོད་ཡིག','clinical',''),('Amharic','አማርኛ','clinical',''),
('Syriac','ܫܠܡܐ','clinical',''),('Dhivehi','ދިވެހި','clinical',''),('Cherokee','ᏣᎳᎩ','clinical',''),('Inuktitut','ᐃᓄᒃ','clinical',''),
('Tifinagh','ⵜⴰⵎⴰⵣⵉⵖⵜ','clinical',''),('Nuosu Yi','ꆈꌠ','clinical',''),('Vai','ꕙꔤ','clinical',''),('Mongolian (vertical)','ᠮᠣᠩᠭᠣᠯ','clinical','')]

def main():
    width,height=2000,65+((len(SAMPLES)+3)//4)*235
    canvas=Image.new('RGB',(width,height),(232,234,230));d=ImageDraw.Draw(canvas)
    heading=fonts.font(str(fonts.ROOT/'NotoSans-Bold.ttf'),27)
    label=fonts.font(str(fonts.ROOT/'NotoSans-Regular.ttf'),16)
    d.text((24,15),f'Property sign typography — {len(SAMPLES)} representative samples',font=heading,fill=(27,36,34))
    for i,(language,value,role,locale) in enumerate(SAMPLES):
        x=20+(i%4)*495;y=65+(i//4)*235
        try:
            board=sign.prepare_fascia(value,role,locale)
            panel=Image.open(BytesIO(board.png)).transpose(Image.Transpose.FLIP_TOP_BOTTOM).resize((470,118),Image.Resampling.LANCZOS)
            canvas.paste(panel,(x,y+29))
            selected=Path(fonts.resolve(value,role,locale)).stem
        except fonts.TextUnavailable as exc:
            d.rectangle((x,y+29,x+470,y+147),fill=(35,42,44))
            d.text((x+14,y+75),'UNLABELLED — '+str(exc),font=label,fill=(243,241,228))
            selected='Explicit diagnostic; no text rendered'
        d.text((x,y),language+'  •  '+role,font=label,fill=(24,35,33))
        d.text((x,y+155),selected,font=label,fill=(60,68,66))
    dest=Path(__file__).resolve().parents[2]/'font-preview.png'
    canvas.save(dest)
    print(dest)
if __name__=='__main__':main()
