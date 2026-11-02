"""Compile the approved textual block proposals, independently of house styles."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def colour(text, fallback):
    # Authored, restrained material tints; these are not sampled regional colours.
    words = (
        ('charcoal', (.24,.27,.28)), ('graphite', (.28,.30,.30)),
        ('bronze', (.43,.37,.28)), ('dark', (.32,.33,.30)),
        ('red', (.66,.40,.30)), ('russet', (.64,.40,.29)),
        ('brown', (.55,.43,.34)), ('umber', (.55,.43,.34)),
        ('ochre', (.76,.65,.45)), ('terracotta', (.70,.47,.35)),
        ('blue', (.49,.59,.63)), ('green', (.51,.59,.49)),
        ('grey', (.64,.65,.62)), ('gray', (.64,.65,.62)),
        ('sand', (.79,.73,.62)), ('buff', (.78,.70,.56)),
        ('cream', (.88,.84,.73)), ('white', (.89,.88,.83)),
        ('pale', (.81,.80,.73)), ('light', (.80,.81,.76)),
        ('warm', (.74,.66,.54)), ('timber', (.58,.46,.33)),
    )
    return next((rgb for word,rgb in words if word in text.lower()),fallback)


def family(text, default):
    t=text.lower()
    for words, value in ((('brick',),'brick'),(('stone','limestone'),'stone'),
                         (('render','lime','whitewash'),'render'),
                         (('boards','weatherboard','siding','shingle','timber'),'wood'),
                         (('concrete','precast'),'concrete'),(('metal','insulated-panel'),'metal')):
        if any(w in t for w in words):return value
    return default


def compile_catalogue():
    source=ROOT/'docs/regional-block-proposals.json'
    data=json.loads(source.read_text(encoding='utf-8'))
    result={}
    defaults={'masonry':'brick','terrace':'render','frame':'concrete','gallery':'render',
              'screen':'render','ribbon':'concrete','timber':'wood','panel':'concrete','solid':'render','arcade':'render'}
    for region in data['regions']:
        rows=[]
        for p in region['proposals']:
            parts=p['palette'].split(';')
            main=parts[0];base=parts[1] if len(parts)>1 else 'grey mineral base'
            accent=parts[-1]
            rows.append(dict(id=p['id'],name=p['name'],grammar=p['grammar'],
                bay=p['bay_range_m'],groups=p['bays_per_group'],reveal=p['reveal_range_m'],
                suggested_floors=p['floor_range'],
                wall_family=family(main,defaults[p['grammar']]),wall_colour=colour(main,(.77,.75,.68)),
                base_family=family(base,'stone'),base_colour=colour(base,(.57,.57,.52)),
                accent_colour=colour(accent,(.33,.35,.32)),trim_colour=[.84,.82,.74],
                palette_text=p['palette']))
        result[region['id']]=rows
    assert len(result)==64 and all(len(rows)==3 for rows in result.values())
    return dict(schema=1,version='regional-blocks-v1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                note='Approved block proposals; all A/B/C variants selectable. Window proportions are deliberately restrained. No regional_profiles dependency.',
                regions=result)


if __name__=='__main__':
    path=ROOT/'server/buildgen/catalog/regional_blocks.json'
    path.write_text(json.dumps(compile_catalogue(),indent=2)+'\n',encoding='utf-8')
    print(path)
