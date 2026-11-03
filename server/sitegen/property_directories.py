"""Bounded, explicit source identity data for shared property directories.

The site graph, not resident buildings or nearby POIs, supplies membership.
"""
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import os
import re
import unicodedata

MAX_BYTES = 1 << 20
MAX_SITES = 128
MAX_MEMBERS = 32
MAX_ROWS = 8
VERSION = 1


def _text(value, limit=160):
    if not isinstance(value, str): raise ValueError('directory text must be a string')
    value = unicodedata.normalize('NFC', value)
    if any(unicodedata.category(c) in ('Cc', 'Cs') for c in value):
        raise ValueError('directory text contains control characters')
    value = ' '.join(value.split())
    if len(value) > limit: raise ValueError('directory text exceeds input budget')
    return value


def _natural(value):
    return tuple((0, int(v)) if v.isdigit() else (1, v.casefold())
                 for v in re.split(r'(\d+)', value) if v)

def _identity(value):
    # Identity tokens are opaque source values, never case-folded or normalized.
    if (not isinstance(value, str) or not value or len(value) > 160 or
            any(unicodedata.category(c) in ('Cc', 'Cs') for c in value)):
        raise ValueError('invalid source identity')
    return value


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def member_key(ref):
    return f'{ref.identity.namespace}:{ref.identity.feature_id}'


@dataclass(frozen=True, slots=True)
class Tenant:
    identity: str
    member: str
    name: str
    unit: str = ''
    descriptor: str = ''
    typography_role: str = 'clinical'


@dataclass(frozen=True, slots=True)
class Directory:
    site_id: str
    number: str
    street: str
    property_name: str
    tenants: tuple
    style: str
    digest: str

    @property
    def boards(self):
        return tuple(self.tenants[i:i + MAX_ROWS] for i in range(0, len(self.tenants), MAX_ROWS))


def plan(site_plan, data):
    """Resolve a directory from one complete association and its explicit identity record."""
    if not isinstance(data, dict): raise ValueError('directory record must be an object')
    site_id = member_key(site_plan.evidence.ref)
    if data.get('site_id') != site_id: raise ValueError('directory site identity mismatch')
    memberships = site_plan.evidence.memberships
    if not memberships or len(memberships) > MAX_MEMBERS: raise ValueError('directory membership budget')
    members = {member_key(m.member) for m in memberships if m.member.kind in ('building', 'lot')}
    raw = data.get('tenants', [])
    if not isinstance(raw, list) or len(raw) > MAX_MEMBERS: raise ValueError('directory occupant budget')
    unique = {}
    for row in raw:
        if not isinstance(row, dict): raise ValueError('directory occupant must be an object')
        if row.get('association') not in ('verified', 'supported') or row.get('operating_status') == 'permanently_closed': continue
        typography = row.get('typography_role','clinical')
        from buildgen.property_fonts import valid_role
        if not isinstance(typography,str) or not valid_role(typography): raise ValueError('unsupported tenant typography role')
        tenant = Tenant(_identity(row.get('identity')), _identity(row.get('member')),
                        *(_text(row.get(k, '')) for k in ('name', 'unit', 'descriptor')), typography)
        if tenant.member not in members: raise ValueError('occupant is not a declared site member')
        if not tenant.identity: raise ValueError('occupant requires an identity')
        if not tenant.name: continue
        if tenant.identity in unique and unique[tenant.identity] != tenant: raise ValueError('conflicting duplicate occupant identity')
        unique[tenant.identity] = tenant
    tenants = tuple(sorted(unique.values(), key=lambda t: (not bool(t.unit), _natural(t.unit), t.name.casefold(), t.identity)))
    if not tenants: raise ValueError('no resolved named occupants')
    address = data.get('address', {})
    if not isinstance(address, dict): raise ValueError('directory address must be an object')
    number, street = _text(address.get('number', ''), 40), _text(address.get('street', ''))
    if not number or not street: raise ValueError('directory requires a real number and street')
    name = _text(data.get('property_name', ''))
    style = data.get('style', 'metal')
    if style not in ('metal', 'timber', 'light'): raise ValueError('unsupported directory style')
    record = dict(version=VERSION, site_id=site_id, number=number, street=street, property_name=name,
                  style=style, tenants=[asdict(t) for t in tenants])
    digest = hashlib.sha256(_canonical(record).encode('utf-8')).hexdigest()
    return Directory(site_id, number, street, name, tenants, style, digest)


@lru_cache(maxsize=1)
def catalogue():
    path = os.environ.get('BNE_PROPERTY_IDENTITIES')
    if not path: return 'none', {}
    with Path(path).open('rb') as stream: raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES: raise ValueError('property identity catalogue exceeds byte budget')
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('version') != VERSION or not isinstance(value.get('sites'), list) or len(value['sites']) > MAX_SITES:
        raise ValueError('property identity catalogue requires bounded version 1 sites')
    sites = {}
    for record in value['sites']:
        if not isinstance(record, dict): raise ValueError('directory site must be an object')
        key = _identity(record.get('site_id'))
        if not key or key in sites: raise ValueError('missing or duplicate directory site identity')
        sites[key] = record
    return hashlib.sha256(raw).hexdigest(), sites


def watch():
    """Register the pinned source for product invalidation and reject changes until restart."""
    path = os.environ.get('BNE_PROPERTY_IDENTITIES')
    if not path: return
    import inputwatch
    inputwatch.paths((path,))
    digest, _ = catalogue()
    with Path(path).open('rb') as stream: raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != digest:
        raise RuntimeError('Property identity catalogue changed; restart the server before rebuilding')


def for_plan(site_plan):
    _, records = catalogue()
    data = records.get(member_key(site_plan.evidence.ref))
    return None if data is None else plan(site_plan, data)
