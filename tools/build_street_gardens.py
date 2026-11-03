"""Precompile compact fenced tree gardens: shared soil, edging and low rails."""
from pathlib import Path
import sys,json,uuid
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import cdae,streetplanters
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'


def mesh(kind):
    ring=streetplanters.garden_ring(kind);P=[];T=[];M=[];C=[];CT=[]
    def face(points,mat):
        i=len(P);P.extend(points)
        for k in range(1,len(points)-1):T.append((i,i+k,i+k+1));M.append(mat)
    def box(a,b,width,z0,z1,collision=False):
        a,b=np.asarray(a),np.asarray(b);d=b-a;n=np.array([-d[1],d[0]])/max(np.linalg.norm(d),1e-9)*width/2
        corners=np.array([a-n,b-n,b+n,a+n]);v=np.array([(*p,z) for z in (z0,z1) for p in corners])
        faces=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
        if not collision:
            for f in faces:face(v[list(f)],0)
        else:
            i=len(C);C.extend(v)
            for a,b,c,d in faces:CT.extend(((i+a,i+b,i+c),(i+a,i+c,i+d)))
    # Soil is genuinely below the opening, not a decal over intact concrete.
    face([(*p,-.04) for p in ring],1)
    for j,a in enumerate(ring):
        b=ring[(j+1)%len(ring)]
        face([(*a,0),(*b,0),(*b,-.04),(*a,-.04)],2)
        A,B=a*.94,b*.94
        box(A,B,.035,.46,.51)
        if kind!='garden_trough':box(A,B,.025,.12,.15)
        count=max(1,int(np.ceil(np.linalg.norm(B-A)/(.26 if kind=='garden_square' else .38))))
        for k in range(count):
            point=A+(B-A)*k/count
            box(point+[-.017,0],point+[.017,0],.034,0,.51)
        # One simple contact wall per side; the tree retains stock collision.
        box(A,B,.05,-.04,.51,collision=True)
    i=len(C);C.extend([(*p,-.04) for p in ring])
    for k in range(1,len(ring)-1):CT.append((i,i+k,i+k+1))
    return np.array(P),np.array(T),np.array(M),np.array(C),np.array(CT)


def main():
    materials={};report=[]
    colors=((.12,.19,.16),(.14,.16,.17),(.28,.23,.16))
    for kind,color in zip(streetplanters.GARDENS,colors):
        name='bne_'+kind+'_fence'
        materials[name]=dict(name=name,mapTo=name,**{'class':'Material'},version=1.5,
          persistentId=str(uuid.uuid5(uuid.NAMESPACE_URL,name)),Stages=[dict(baseColorFactor=[*color,1],metallicFactor=.6,roughnessFactor=.65),{},{},{}])
        P,T,M,C,CT=mesh(kind);path=OUT/(kind+'.cdae')
        cdae.write(str(path),P,T,uvs=P[:,:2],material=[name,'bne_planter_soil','bne_planter_square'],tri_materials=M,
            collisions=[(C,CT,np.zeros(len(CT),dtype=np.int64))],object_name='tree_garden')
        report.append(dict(kind=kind,triangles=len(T),collision_triangles=len(CT),bytes=path.stat().st_size))
    (OUT/'gardens.materials.json').write_text(json.dumps(materials,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
