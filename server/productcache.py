"""Versioned, bounded plan/product storage with checked numeric payloads.

No pickle decoding. Dataclass constructors come only from the project's known
geometry packages; arrays are size-checked raw streams, never object arrays.
Missing, corrupt, incompatible and unavailable storage are separate outcomes.
"""
from collections import Counter
from dataclasses import dataclass,fields,is_dataclass
import hashlib,importlib,json,math,os,re,threading,time,uuid,zipfile
from pathlib import Path
import numpy as np

VERSION=1
MAX_BYTES=64<<20
MAX_META=8<<20
MAX_NODES=250000
MAX_ARRAYS=4096
MAX_DEPTH=64
MAX_ENTRIES=4096
DEFAULT_QUOTA=512<<20
_GATE=threading.Lock()
_PRUNED={}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def identity(dependencies):
    return hashlib.sha256(canonical(dependencies).encode()).hexdigest()


@dataclass(frozen=True)
class Lookup:
    status:str
    value:object=None
    revision:str=''
    reason:str=''


def _class(name):
    module,sep,cls=name.rpartition(':')
    if not sep or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',cls):raise ValueError('invalid record class')
    if not (module.startswith(('buildgen.','sitegen.')) or module in ('roads','geodesy')):
        raise ValueError('unsupported record package')
    result=getattr(importlib.import_module(module),cls)
    if not (is_dataclass(result) or issubclass(result,tuple) and hasattr(result,'_fields')):
        raise ValueError('unsupported record constructor')
    return result


class Codec:
    def __init__(self):self.blobs={};self.nodes=0;self.bytes=0

    def encode(self,value,depth=0):
        self.nodes+=1
        if depth>MAX_DEPTH or self.nodes>MAX_NODES:raise ValueError('plan tree budget')
        child=lambda v:self.encode(v,depth+1)
        if isinstance(value,np.generic):value=value.item()
        if value is None or type(value) in (str,bool,int,float):
            if type(value) is float and not math.isfinite(value):raise ValueError('nonfinite plan scalar')
            return value
        if isinstance(value,np.ndarray):
            if value.dtype.hasobject or value.ndim>4 or value.dtype.kind not in 'biufUS':raise ValueError('unsupported array')
            if len(self.blobs)>=MAX_ARRAYS or self.bytes+value.nbytes>MAX_BYTES:raise ValueError('plan array budget')
            name=f'a{len(self.blobs)}.bin';data=np.ascontiguousarray(value).tobytes()
            self.blobs[name]=data;self.bytes+=len(data)
            return {'array':name,'dtype':value.dtype.str,'shape':value.shape}
        if isinstance(value,bytes):
            if len(self.blobs)>=MAX_ARRAYS or self.bytes+len(value)>MAX_BYTES:raise ValueError('binary product budget')
            name=f'a{len(self.blobs)}.bin';self.blobs[name]=value;self.bytes+=len(value)
            return {'bytes':name}
        if is_dataclass(value):
            name=type(value).__module__+':'+type(value).__name__;_class(name)
            return {'record':name,'fields':{f.name:child(getattr(value,f.name)) for f in fields(value)}}
        if isinstance(value,tuple) and hasattr(value,'_fields'):
            name=type(value).__module__+':'+type(value).__name__;_class(name)
            return {'namedtuple':name,'values':[child(v) for v in value]}
        if isinstance(value,(tuple,list)):
            return {'tuple' if isinstance(value,tuple) else 'list':[child(v) for v in value]}
        if isinstance(value,dict):return {'map':[[child(k),child(v)] for k,v in value.items()]}
        if isinstance(value,(set,frozenset)):
            return {'set':[child(v) for v in sorted(value,key=repr)],'frozen':isinstance(value,frozenset)}
        raise ValueError('unsupported plan value: '+type(value).__name__)

    def decode(self,value,depth=0):
        self.nodes+=1
        if depth>MAX_DEPTH or self.nodes>MAX_NODES:raise ValueError('decoded plan tree budget')
        child=lambda v:self.decode(v,depth+1)
        if not isinstance(value,dict):
            if value is None or type(value) in (str,bool,int,float):return value
            raise ValueError('invalid scalar node')
        if set(value)=={'array','dtype','shape'}:
            data=self.blobs[value['array']];dtype=np.dtype(value['dtype']);shape=value['shape']
            if (dtype.hasobject or dtype.kind not in 'biufUS' or len(shape)>4 or
                    any(type(n) is not int or n<0 for n in shape) or math.prod(shape)*dtype.itemsize!=len(data)):
                raise ValueError('array layout/size mismatch')
            return np.frombuffer(data,dtype).reshape(shape)
        if set(value)=={'bytes'}:return self.blobs[value['bytes']]
        if set(value)=={'record','fields'}:
            cls=_class(value['record']);body=value['fields']
            if not is_dataclass(cls) or set(body)!={f.name for f in fields(cls)}:raise ValueError('record schema mismatch')
            return cls(**{k:child(v) for k,v in body.items()})
        if set(value)=={'namedtuple','values'}:
            cls=_class(value['namedtuple'])
            if len(value['values'])!=len(cls._fields):raise ValueError('named record schema mismatch')
            return cls(*(child(v) for v in value['values']))
        if set(value)=={'tuple'}:return tuple(child(v) for v in value['tuple'])
        if set(value)=={'list'}:return [child(v) for v in value['list']]
        if set(value)=={'map'}:return {child(k):child(v) for k,v in value['map']}
        if set(value)=={'set','frozen'}:
            values=(child(v) for v in value['set'])
            return frozenset(values) if value['frozen'] else set(values)
        raise ValueError('unknown plan node')


class Store:
    def __init__(self,cache_dir,quota=DEFAULT_QUOTA):
        self.root=Path(cache_dir)/'products'/f'v{VERSION}'
        self.quota=max(0,int(quota));self.stats=Counter()

    def path(self,kind,key):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',kind) or not re.fullmatch(r'[a-f0-9]{64}',key):
            raise ValueError('invalid product address')
        return self.root/kind/(key+'.zip')

    def load(self,kind,key):
        path=self.path(kind,key)
        try:
            if path.stat().st_size>MAX_BYTES+MAX_META:return Lookup('corrupt',reason='archive budget')
            with zipfile.ZipFile(path) as archive:
                records=archive.infolist()
                if len(records)>MAX_ARRAYS+1 or sum(r.file_size for r in records)>MAX_BYTES+MAX_META:
                    raise ValueError('expanded product budget')
                if any(r.filename!='meta.json' and not re.fullmatch(r'a[0-9]+\.bin',r.filename) for r in records):
                    raise ValueError('unexpected product member')
                if archive.getinfo('meta.json').file_size>MAX_META:raise ValueError('metadata budget')
                meta=json.loads(archive.read('meta.json'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
                if meta.get('version')!=VERSION or meta.get('key')!=key:return Lookup('incompatible')
                body=meta['body'];revision=identity(body)
                if revision!=meta['revision']:raise ValueError('metadata checksum')
                if set(archive.namelist())!=set(body['blobs'])|{'meta.json'} or len(archive.namelist())!=len(set(archive.namelist())):
                    raise ValueError('product member mismatch')
                codec=Codec()
                for name,digest in body['blobs'].items():
                    data=archive.read(name)
                    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('array checksum')
                    codec.blobs[name]=data
                value=codec.decode(body['tree'])
            try:os.utime(path,None)
            except OSError:pass
            self.stats['hits']+=1
            return Lookup('ready',value,revision)
        except FileNotFoundError:self.stats['misses']+=1;return Lookup('absent')
        except OSError as exc:self.stats['unavailable']+=1;return Lookup('unavailable',reason=str(exc))
        except (ValueError,TypeError,KeyError,AttributeError,ImportError,RecursionError,zipfile.BadZipFile) as exc:
            self.stats['corrupt']+=1;return Lookup('corrupt',reason=str(exc))

    def put(self,kind,key,value):
        path=self.path(kind,key);temporary=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        if not self.quota:return Lookup('disabled')
        try:
            codec=Codec();tree=codec.encode(value)
            body={'tree':tree,'blobs':{n:hashlib.sha256(v).hexdigest() for n,v in codec.blobs.items()}}
            revision=identity(body)
            meta=canonical(dict(version=VERSION,key=key,revision=revision,body=body)).encode()
            if len(meta)>MAX_META:raise ValueError('product metadata budget')
            if len(meta)+codec.bytes>min(MAX_BYTES+MAX_META,self.quota):return Lookup('oversized')
            path.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(temporary,'x',zipfile.ZIP_STORED) as archive:
                archive.writestr('meta.json',meta)
                for name,data in codec.blobs.items():archive.writestr(name,data)
            os.replace(temporary,path);self.stats['writes']+=1;self.prune(force=True)
            return Lookup('ready',value,revision)
        except (OSError,ValueError,TypeError) as exc:
            self.stats['write_failures']+=1
            return Lookup('unavailable',reason=str(exc))
        finally:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass

    def prune(self,force=False):
        now=time.monotonic();root=str(self.root)
        with _GATE:
            if not force and now-_PRUNED.get(root,-1e9)<30.:return
            _PRUNED[root]=now
            files=[]
            for path in self.root.glob('*/*.zip'):
                try:
                    stat=path.stat();files.append((stat.st_mtime_ns,path,stat.st_size))
                except OSError:continue
                if len(files)>MAX_ENTRIES:break
            total=sum(n for _,_,n in files)
            remaining=len(files)
            for _,path,size in sorted(files):
                if total<=self.quota and remaining<=MAX_ENTRIES:break
                try:path.unlink();total-=size;remaining-=1;self.stats['evictions']+=1
                except OSError:pass

    def get_or_build(self,kind,key,build,wait_s=2.,valid=lambda:True):
        import xproc
        path=self.path(kind,key);lock=str(path)+'.lock'
        def ready():
            result=self.load(kind,key)
            return result if result.status=='ready' else None
        got,held=xproc.once(lock,ready,wait_s)
        if got is not None:self.stats['coalesced']+=1;return got
        try:
            value=build()
            # Failure/cancellation may discard optional publication, never an
            # already accepted physical product or a producer's live resources.
            if not valid():return Lookup('unpublished',value)
            result=self.put(kind,key,value)
            return result if result.status=='ready' else Lookup('uncached',value,reason=result.reason)
        finally:
            if held:xproc.release(lock)
