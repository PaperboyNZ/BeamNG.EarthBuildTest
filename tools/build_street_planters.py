"""Build three shared planter meshes; no mesh generation is needed at runtime."""
from pathlib import Path
import sys, json, uuid
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import cdae
OUT=ROOT/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'


def mesh(kind):
    if kind=='square':
        ring=np.array([[-.42,-.36],[-.36,-.42],[.36,-.42],[.42,-.36],[.42,.36],[.36,.42],[-.36,.42],[-.42,.36]])
    elif kind=='octagon':
        a=np.arange(8)*np.pi/4;ring=np.column_stack((np.cos(a),np.sin(a)))*.60
    else:
        ring=np.array([[-.55,-.20],[-.48,-.30],[.48,-.30],[.55,-.20],[.55,.20],[.48,.30],[-.48,.30],[-.55,.20]])
    P=[];T=[];M=[]
    def face(points,material):
        first=len(P);P.extend(points)
        for i in range(1,len(points)-1):T.append((first,first+i,first+i+1));M.append(material)
    def band(a,b,z0,z1,mat):
        for j in range(len(ring)):
            k=(j+1)%len(ring)
            face([(*a[j],z0),(*a[k],z0),(*b[k],z1),(*b[j],z1)],mat)
    # Recessed foot, tapered body, narrow contrasting lip and visible inner wall.
    band(ring*.86,ring*.86,0,.06,1)
    band(ring*.86,ring*.97,.06,.55,0)
    band(ring*.97,ring,.55,.59,1)
    band(ring,ring,.59,.65,1)
    band(ring,ring*.80,.65,.65,1)
    band(ring*.80,ring*.80,.65,.48,0)
    face([(*p,.48) for p in ring*.80],2)
    face([(*p,0.) for p in (ring*.86)[::-1]],1)
    # Simple closed convex collision hull; no per-face hollow collision cost.
    C=np.array([(*p,z) for z in (0.,.65) for p in ring]);CT=[];n=len(ring)
    for j in range(n):
        k=(j+1)%n;CT.extend(((j,k,k+n),(j,k+n,j+n)))
    for j in range(1,n-1):CT.extend(((0,j+1,j),(n,n+j,n+j+1)))
    return np.array(P),np.array(T),np.array(M),C,np.array(CT)


def main():
    materials={}
    palettes={'square':((.64,.61,.55),(.77,.74,.67),.0,.88),
              'octagon':((.10,.15,.16),(.19,.25,.25),.65,.48),
              'trough':((.49,.44,.36),(.66,.60,.49),.0,.9)}
    report=[]
    for kind,(body,lip,metal,rough) in palettes.items():
        names=['bne_planter_'+kind,'bne_planter_'+kind+'_lip','bne_planter_soil']
        for name,color,m,r in zip(names,(body,lip,(.10,.075,.045)),(metal,metal,0),(rough,rough,1)):
            materials[name]=dict(name=name,mapTo=name,**{'class':'Material'},version=1.5,
                persistentId=str(uuid.uuid5(uuid.NAMESPACE_URL,name)),Stages=[dict(baseColorFactor=[*color,1],metallicFactor=m,roughnessFactor=r),{},{},{}])
        P,T,M,C,CT=mesh(kind)
        path=OUT/('planter_'+kind+'.cdae')
        cdae.write(str(path),P,T,uvs=P[:,:2],material=names,tri_materials=M,collisions=[(C,CT,np.zeros(len(CT),dtype=np.int64))],object_name='planter')
        report.append(dict(kind=kind,triangles=len(T),collision_triangles=len(CT),bytes=path.stat().st_size))
    (OUT/'planters.materials.json').write_text(json.dumps(materials,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
