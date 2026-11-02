"""Compile city briefs from descriptive prose only; no regional style inputs.

Qualitative cues are explicit lexical annotations of the authored city brief.
They are design suggestions, never inferred climate, standards or prevalence.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('label', 'group', 'coverage', 'style_directions', 'detailing_goals')
CUES = {
    'recess': ('recess', 'deep reveal'),
    'screen': ('screen', 'louvre'),
    'horizontal': ('horizontal', 'banding'),
    'masonry': ('masonry', 'brick', 'stone'),
    'shelter': ('shelter', 'protected', 'covered'),
}


def compile_records(regions, briefs):
    rows = {}
    for line in briefs.splitlines():
        match = re.match(r'^\| `([^`]+)` \|', line)
        if not match:
            continue
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if len(cells) != 4 or match[1] in rows:
            raise ValueError('Invalid or duplicate city brief row')
        rows[match[1]] = cells[1:]
    if len(rows) != 64 or set(rows) != set(regions):
        raise ValueError('City brief IDs must match all 64 geographic identities')
    result = {}
    for key, source in regions.items():
        descriptive = {field: source[field] for field in FIELDS}
        geography, architecture, public_realm = rows[key]
        payload = dict(source=descriptive, geography=geography,
                       architecture=architecture, public_realm=public_realm)
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
        text = architecture.lower()
        result[key] = dict(**payload, source_digest=hashlib.sha256(encoded).hexdigest(),
                           cues=[cue for cue, words in CUES.items() if any(word in text for word in words)],
                           status='text_based_proposal', city_applicable=key != 'antarctic_stations')
    return dict(schema=1, version='city-text-briefs-v1', regions=result,
                source_fields=list(FIELDS),
                note='City text/geographic interpretations only; no existing regional style parameters.')


def main():
    catalog = ROOT/'server/buildgen/catalog'
    regions = json.loads((catalog/'environments.json').read_text(encoding='utf-8'))['regions']
    briefs = (ROOT/'docs/CITY_REGIONAL_DESIGN_BRIEFS.md').read_text(encoding='utf-8')
    result = compile_records(regions, briefs)
    (catalog/'city_regions.json').write_text(json.dumps(result, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    print('Compiled 64 city descriptions; numeric regional styles were not read.')


if __name__ == '__main__':
    main()
