"""Shared immutable architecture programme, datums, runs and fitted grids.

Derived from an already resolved source envelope; no new source interpretation,
storeys, entrances, structural assemblies or era inference. Datums are relative
to the existing volume base, not mapped level labels. Caller-local XY is never
used as semantic seed identity or as a persistent cache key.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import math

from . import materials
from .topology import Footprint

VERSION = 1
MAX_FLOORS = 120
MAX_RUNS = 4096
MAX_BAYS = 256
CHANNELS = ('function','structure','era','vocabulary','condition')


def _finite(value,low,high,name):
    if isinstance(value,bool):raise ValueError(f'{name} requires a finite number')
    try:value=float(value)
    except (TypeError,ValueError,OverflowError) as exc:raise ValueError(f'invalid {name}') from exc
    if not math.isfinite(value) or not low<=value<=high:raise ValueError(f'{name} outside supported bounds')
    return value


@dataclass(frozen=True,slots=True)
class Provenance:
    field: str
    value: str | float | bool | None
    status: str
    source: str

    def __post_init__(self):
        if (not isinstance(self.field,str) or not 0<len(self.field)<=64 or
                self.status not in ('observed','resolved','inferred','fallback','style_prior','unknown','invalid','conflict') or
                not isinstance(self.source,str) or len(self.source)>512):
            raise ValueError('invalid bounded architecture provenance')
        if self.value is not None and type(self.value) not in (str,int,float,bool):
            raise ValueError('architecture provenance retains scalar values only')
        if isinstance(self.value,str) and len(self.value)>512:raise ValueError('architecture provenance text exceeds budget')
        if isinstance(self.value,float) and not math.isfinite(self.value):raise ValueError('architecture provenance must be finite')


@dataclass(frozen=True,slots=True)
class FloorDatum:
    index: int
    bottom: float
    top: float

    def __post_init__(self):
        if type(self.index) is not int or not 0<=self.index<MAX_FLOORS:
            raise ValueError('floor datum index exceeds budget')
        object.__setattr__(self,'bottom',_finite(self.bottom,0.,1000.,'floor bottom'))
        object.__setattr__(self,'top',_finite(self.top,0.,1000.,'floor top'))
        if not self.bottom<self.top:
            raise ValueError('floor datum must have positive height')

    @property
    def height(self):return self.top-self.bottom


@dataclass(frozen=True,slots=True)
class EdgeMember:
    edge: int
    start: float
    end: float


@dataclass(frozen=True,slots=True)
class ElevationRun:
    index: int
    boundary: int
    start: tuple
    end: tuple
    length: float
    members: tuple[EdgeMember,...]
    party_wall: bool = False

    def __post_init__(self):
        object.__setattr__(self,'start',tuple(self.start));object.__setattr__(self,'end',tuple(self.end))
        object.__setattr__(self,'members',tuple(self.members))
        if (len(self.start)!=2 or len(self.end)!=2 or len(self.members)>MAX_RUNS or not self.members
                or not all(isinstance(member,EdgeMember) for member in self.members)):
            raise ValueError('invalid bounded elevation run')

    @property
    def edge(self):return self.members[0].edge

    def member(self,edge):
        return next((member for member in self.members if member.edge==edge),None)

    def locate(self,along):
        """Source edge/local offset; internal boundaries belong to next edge."""
        along=_finite(along,-1e-8,self.length+1e-8,'run offset')
        along=max(0.,min(self.length,along))
        for member in self.members:
            if along<member.end or member is self.members[-1]:
                return member.edge,along-member.start
        raise ValueError('empty elevation run')


@dataclass(frozen=True,slots=True)
class Bay:
    index: int
    left: float
    right: float

    def __post_init__(self):
        if type(self.index) is not int or not 0<=self.index<MAX_RUNS:raise ValueError('bay ordinal exceeds budget')
        object.__setattr__(self,'left',_finite(self.left,-100000.,100000.,'bay start'))
        object.__setattr__(self,'right',_finite(self.right,-100000.,100000.,'bay end'))
        if self.left>=self.right:
            raise ValueError('bay requires a positive interval')

    @property
    def centre(self):return (self.left+self.right)/2


@dataclass(frozen=True,slots=True)
class BayGrid:
    length: float
    bays: tuple[Bay,...]
    diagnostics: tuple = ()

    def __post_init__(self):
        object.__setattr__(self,'bays',tuple(self.bays));object.__setattr__(self,'diagnostics',tuple(self.diagnostics))
        object.__setattr__(self,'length',_finite(self.length,0.,100000.,'grid length'))
        if len(self.bays)>MAX_BAYS or not all(isinstance(bay,Bay) for bay in self.bays):
            raise ValueError('bounded grid requires immutable bays')

    @property
    def start(self):return self.bays[0].left if self.bays else 0.

    @property
    def end(self):return self.bays[-1].right if self.bays else 0.

    @property
    def span(self):return self.end-self.start


@dataclass(frozen=True,slots=True)
class Programme:
    identity: tuple
    function: Provenance
    structure: Provenance
    era: Provenance
    vocabulary: Provenance
    condition: Provenance
    source_levels: tuple[Provenance,...]
    datums: tuple[FloorDatum,...]
    runs: tuple[ElevationRun,...]
    edge_to_run: tuple
    diagnostics: tuple = ()
    version: int = VERSION

    def __post_init__(self):
        for name in ('identity','source_levels','datums','runs','diagnostics'):
            object.__setattr__(self,name,tuple(getattr(self,name)))
        object.__setattr__(self,'edge_to_run',tuple(tuple(row) for row in self.edge_to_run))
        if len(self.datums)>MAX_FLOORS or len(self.runs)>MAX_RUNS:
            raise ValueError('programme record budget exceeded')

    def run(self,boundary,edge):
        if type(boundary) is not int or type(edge) is not int or boundary<0 or edge<0:
            raise ValueError('elevation address requires nonnegative integer indices')
        try:return self.runs[self.edge_to_run[boundary][edge]]
        except IndexError as exc:raise ValueError('elevation address outside source footprint') from exc

    def datum(self,index):
        if type(index) is not int or not 0<=index<len(self.datums):raise ValueError('floor datum outside resolved body')
        return self.datums[index]

    def seed(self,channel,subkey=''):return seed(self,channel,subkey)


def _identity(spec):
    value=_finite(spec.seed if spec.seed is not None else 0.,-1e100,1e100,'appearance seed')
    evidence=getattr(spec,'evidence',None)
    source=getattr(evidence,'source_id',None)
    if source is not None and not isinstance(source,str):source=None
    if source is not None and len(source)>512:
        source=('hashed_source_id',hashlib.sha256(source.encode('utf-8')).hexdigest())
    return source,value


def seed(spec_or_programme,channel,subkey=''):
    """Independent semantic channels; an era seed is not observed era evidence."""
    if channel not in CHANNELS:raise ValueError('unknown architecture semantic seed channel')
    if not _semantic_key(subkey) or len(repr(subkey))>1024:
        raise ValueError('architecture seed subkey exceeds bounded semantic key')
    identity=spec_or_programme.identity if isinstance(spec_or_programme,Programme) else _identity(spec_or_programme)
    return materials.unit(identity,('architecture-programme-v1',channel,subkey))


def legacy_seed(spec,channel,legacy_key):
    """Migration bridge preserving accepted pre-foundation appearance choices.

    The semantic channel documents the decision role; the historical key/hash
    remains exact so introducing records cannot reshuffle physical assemblies.
    New choices use seed(), not this compatibility bridge.
    """
    if channel not in CHANNELS:raise ValueError('unknown architecture semantic seed channel')
    if not _semantic_key(legacy_key) or len(repr(legacy_key))>1024:raise ValueError('legacy semantic seed key exceeds budget')
    return materials.unit(spec.seed,legacy_key)


def _semantic_key(value,depth=0):
    if depth>8:return False
    if isinstance(value,str):return len(value)<=512
    if type(value) is int:return abs(value)<=10**12
    if value is None:return True
    if isinstance(value,tuple) and len(value)<=16:return all(_semantic_key(item,depth+1) for item in value)
    return False


def _fact(field,value,status,source):
    if isinstance(value,str):value=value[:512]
    if isinstance(value,float) and not math.isfinite(value):value=None;status='unknown'
    return Provenance(field,value,status,str(source or 'not_retained')[:512])


def derive(spec,party_walls=()):
    """Derive bounded records without changing the source or serialized plan."""
    fp=getattr(spec,'footprint',None)
    if not isinstance(fp,Footprint) or fp.vertex_count>MAX_RUNS:
        raise ValueError('programme requires bounded validated source footprint')
    floors=spec.floors
    if type(floors) is not int or not 1<=floors<=MAX_FLOORS:raise ValueError('programme floor count outside budget')
    height=_finite(spec.height,.01,1000.,'resolved body height')
    floor_height=_finite(spec.floor_h,.01,1000.,'resolved floor height')
    church=getattr(spec,'church',None)
    if church is not None and church.accepted:
        function=_fact('function',church.current_use,'observed' if church.current_use!='unknown' else 'unknown','church_semantic_adapter')
        vocabulary=_fact('vocabulary',church.vocabulary,'resolved','accepted_church_material')
        party_walls=church.party_walls
    else:
        resolution=getattr(spec,'inference',None)
        use=getattr(resolution,'use',None);facade=getattr(resolution,'facade',None)
        function=_fact('function',getattr(use,'value',None),getattr(use,'status','unknown'),getattr(use,'source','not_retained'))
        vocabulary=_fact('vocabulary',getattr(facade,'value',None),getattr(facade,'status','unknown'),getattr(facade,'source','not_retained'))
    if not isinstance(party_walls,(tuple,list)) or len(party_walls)>MAX_RUNS:
        raise ValueError('party-wall labels exceed source budget')
    blocked=[]
    rings=(fp.outer,*fp.holes)
    for item in party_walls:
        if (not isinstance(item,(tuple,list)) or len(item)!=2 or any(type(v) is not int for v in item)
                or not 0<=item[0]<len(rings) or not 0<=item[1]<len(rings[item[0]])):
            raise ValueError('party-wall label outside source footprint')
        blocked.append(tuple(item))
    source_levels=[]
    evidence=getattr(spec,'evidence',None)
    for field in ('num_floors','min_floor','level','num_floors_underground'):
        observation=evidence.get(field) if evidence is not None else None
        source_levels.append(_fact(field,getattr(observation,'value',None),getattr(observation,'status','unknown'),
                                   getattr(observation,'source',None)))
    return _derive(fp,floors,height,floor_height,_identity(spec),function,vocabulary,tuple(source_levels),tuple(sorted(set(blocked))))


@lru_cache(maxsize=128)
def _derive(fp,floors,height,floor_height,identity,function,vocabulary,source_levels,blocked):
    datums=[];diagnostics=[]
    for index in range(floors):
        bottom=min(height,index*floor_height)
        top=min(height,(index+1)*floor_height)
        if top-bottom<=1e-8:break
        datums.append(FloorDatum(index,bottom,top))
    if len(datums)!=floors or not math.isclose(floors*floor_height,height,abs_tol=1e-7):
        diagnostics.append('resolved_floor_datums_clipped_to_actual_body')
    observed_floors=next((fact for fact in source_levels if fact.field=='num_floors'),None)
    if (observed_floors is not None and observed_floors.status=='observed'
            and type(observed_floors.value) in (int,float) and observed_floors.value!=floors):
        diagnostics.append('resolved_floor_count_differs_from_source_observation')
    runs=[];lookup=[]
    for boundary,ring in enumerate((fp.outer,*fp.holes)):
        n=len(ring);lengths=[math.dist(ring[i],ring[(i+1)%n]) for i in range(n)]
        def joins(a,c):
            if ((boundary,a) in blocked)!=((boundary,c) in blocked):return False
            pa,pb,pc=ring[a],ring[c],ring[(c+1)%n]
            u=(pb[0]-pa[0],pb[1]-pa[1]);v=(pc[0]-pb[0],pc[1]-pb[1])
            scale=max(1e-20,lengths[a]*lengths[c])
            return abs(u[0]*v[1]-u[1]*v[0])<=scale*1e-10 and u[0]*v[0]+u[1]*v[1]>0
        starts=[i for i in range(n) if not joins((i-1)%n,i)]
        if not starts:raise ValueError('source boundary has no valid elevation corners')
        starts.sort(key=lambda i:(ring[i],ring[(i+1)%n]))
        indices=[None]*n
        for first in starts:
            members=[];edge=first;offset=0.
            while True:
                members.append(EdgeMember(edge,offset,offset+lengths[edge]));offset+=lengths[edge]
                following=(edge+1)%n
                if not joins(edge,following):break
                edge=following
            run=ElevationRun(len(runs),boundary,ring[first],ring[(edge+1)%n],offset,tuple(members),(boundary,first) in blocked)
            runs.append(run)
            for member in members:indices[member.edge]=run.index
        lookup.append(tuple(indices))
    if len(runs)>MAX_RUNS:raise ValueError('elevation run budget exceeded')
    unknown=lambda field:Provenance(field,None,'unknown','source_'+field+'_not_retained')
    return Programme(identity,function,unknown('structure'),unknown('era'),vocabulary,unknown('condition'),source_levels,
                     tuple(datums),tuple(runs),tuple(lookup),tuple(diagnostics))


def fit_grid(length,bay,width,margin=.55,reserved=(),gap=.24,max_bays=16,mode='fill',
             allow_single=True,reserved_mode='reflow',reservation_gap=None):
    """Bounded fitted modules; omitted reservations keep the original lattice.

    ``fill`` distributes within available spans. ``centered`` keeps nominal bay
    spacing centered on each span. Reservations are one-dimensional wall ranges;
    callers select only vertically relevant opening envelopes before passing them.
    """
    length=_finite(length,0.,100000.,'run length');bay=_finite(bay,.1,10000.,'bay pitch')
    width=_finite(width,.01,10000.,'bay width');margin=_finite(margin,0.,10000.,'corner margin')
    gap=_finite(gap,0.,10000.,'opening gap')
    reservation_gap=gap if reservation_gap is None else _finite(reservation_gap,0.,10000.,'reservation gap')
    if type(max_bays) is not int or not 0<=max_bays<=MAX_BAYS:raise ValueError('bay count budget exceeded')
    if mode not in ('fill','centered') or reserved_mode not in ('reflow','omit'):raise ValueError('unknown fitted grid policy')
    if not isinstance(reserved,(tuple,list)) or len(reserved)>MAX_BAYS:raise ValueError('reservation budget exceeded')
    reservations=[]
    for interval in reserved:
        if not isinstance(interval,(tuple,list)) or len(interval)!=2:raise ValueError('reservation requires an interval')
        low=_finite(interval[0],-100000.,100000.,'reservation start');high=_finite(interval[1],-100000.,100000.,'reservation end')
        if high<low:raise ValueError('reversed opening reservation')
        reservations.append((low-reservation_gap,high+reservation_gap))
    lo,hi=margin,length-margin
    if hi<=lo or max_bays==0:return BayGrid(length,(),('no_complete_bay_fits',))
    spans=[];start=lo
    if reserved_mode=='reflow':
        for a,c in sorted(reservations):
            if c<=start:continue
            if a>=hi:break
            if a>start:spans.append((start,min(hi,a)))
            start=max(start,c)
        if start<hi:spans.append((start,hi))
    else:spans=[(lo,hi)]
    result=[];ordinal=0
    for a,c in spans:
        if len(result)>=max_bays:break
        count=min(max_bays-len(result),max(0,int((c-a)/bay)))
        if count==0 and len(result)<max_bays and allow_single and c-a>=width+gap:count=1
        if count<=0:continue
        span=c-a if mode=='fill' else min(c-a,count*bay)
        start=a+(c-a-span)/2
        fitted=min(width,span/count-gap)
        if fitted<=0:continue
        for i in range(count):
            centre=start+span*(i+.5)/count
            candidate=Bay(ordinal,centre-fitted/2,centre+fitted/2);ordinal+=1
            if reserved_mode=='omit' and any(candidate.left<b and candidate.right>a for a,b in reservations):continue
            result.append(candidate)
    return BayGrid(length,tuple(result),() if result else ('no_complete_bay_fits',))


def project_grid(grid,run,edge):
    """Clip global run bays to one original edge without restarting the lattice."""
    member=run.member(edge)
    if member is None:raise ValueError('edge is not a member of the elevation run')
    result=[];clipped=False
    for bay in grid.bays:
        left=max(bay.left,member.start);right=min(bay.right,member.end)
        if right-left<=1e-8:continue
        clipped|=left!=bay.left or right!=bay.right
        result.append(Bay(bay.index,left-member.start,right-member.start))
    return BayGrid(member.end-member.start,tuple(result),('collinear_bay_projected_to_source_edge',) if clipped else ())


def translate_grid(grid,offset,length=None):
    """Translate an already accepted grid without refitting its modules."""
    offset=_finite(offset,-100000.,100000.,'grid offset')
    target=grid.length if length is None else _finite(length,0.,100000.,'grid length')
    return BayGrid(target,tuple(Bay(b.index,b.left+offset,b.right+offset) for b in grid.bays),grid.diagnostics)
