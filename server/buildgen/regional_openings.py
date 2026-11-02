"""Bounded arched aperture masks, reveals and frames for rectangular glazing."""
import math

def draw_arch(mesh, opening, at, wall_material, trim_material, depth, frame, shape='arched', lite=False, wall_uv=None,
              retain_depth=False):
    """Draw a corner mask and arch around a pre-existing rectangular pane.

    at(s,z,d) maps facade coordinates to world coordinates; negative d is
    inside the wall. Flattened lite glazing uses a +.025 mask. Deep middle-tier
    openings retain the wall-plane mask and returns with the cheaper arch curve.
    """
    if shape not in ('arched', 'segmental'):
        raise ValueError('unsupported arch shape')
    l,r,b,t = map(float,(opening.left,opening.right,opening.bottom,opening.top))
    w,h=r-l,t-b
    if not all(math.isfinite(v) for v in (l,r,b,t,depth,frame)) or w<=0 or h<=0 or depth<0 or frame<=0:
        raise ValueError('invalid opening dimensions')
    rise=min(w/2,h*(.45 if shape=='arched' else .20))
    spring=t-rise; centre=(l+r)/2; n=6 if lite else 8
    front=.025 if lite and not retain_depth else 0.; tf=front+.002
    uv4=((0.,0.),(1.,0.),(1.,1.),(0.,1.)); uv3=uv4[:3]
    def quad(ps,mat): mesh.quad(*(at(*p) for p in ps),*(tuple(wall_uv(p[0],p[1]) for p in ps) if wall_uv and mat==wall_material else uv4),mat)
    def tri(ps,mat): mesh.tri(*(at(*p) for p in ps),*(tuple(wall_uv(p[0],p[1]) for p in ps) if wall_uv and mat==wall_material else uv3),mat)
    inner=[]; outer=[]
    for i in range(n+1):
        a=math.pi-i*math.pi/n
        inner.append((centre+w/2*math.cos(a),spring+rise*math.sin(a)))
        outer.append((centre+(w/2+frame)*math.cos(a),spring+(rise+frame)*math.sin(a)))
    for i in range(n):
        x,z=inner[i]; X,Z=inner[i+1]; ox,oz=outer[i]; OX,OZ=outer[i+1]
        if abs(z-t)<1e-9:
            tri(((x,z,front),(X,Z,front),(X,t,front)),wall_material)
        elif abs(Z-t)<1e-9:
            tri(((x,z,front),(X,Z,front),(x,t,front)),wall_material)
        else:
            quad(((x,z,front),(X,Z,front),(X,t,front),(x,t,front)),wall_material)
        quad(((x,z,tf),(X,Z,tf),(OX,OZ,tf),(ox,oz,tf)),trim_material)
        if (not lite or retain_depth) and depth:
            quad(((X,Z,0.),(x,z,0.),(x,z,-depth),(X,Z,-depth)),wall_material)
    for x,X in ((l-frame,l),(r,r+frame)):
        quad(((x,b,tf),(X,b,tf),(X,spring,tf),(x,spring,tf)),trim_material)
    quad(((l-frame,b-frame,tf),(r+frame,b-frame,tf),(r+frame,b,tf),(l-frame,b,tf)),trim_material)
    if (not lite or retain_depth) and depth:
        for x in (l,r):
            points=((x,b,0.),(x,spring,0.),(x,spring,-depth),(x,b,-depth))
            quad(points[::-1] if x==l else points,wall_material)
        quad(((l,b,0.),(r,b,0.),(r,b,-depth),(l,b,-depth)),wall_material)
