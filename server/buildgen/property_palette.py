"""A shared sign/trim palette derived from regional context and facade finish."""
from .property_programme import REGIONS,for_spec

REGIONAL = {
    'nz_australia': ((.16,.28,.24),(.87,.85,.75)),
    'britain_ireland': ((.20,.24,.28),(.82,.75,.62)),
    'japanese_urban': ((.22,.28,.36),(.93,.91,.85)),
    'tropical_contemporary': ((.10,.32,.31),(.86,.79,.63)),
    'generic': ((.21,.27,.29),(.85,.83,.76)),
}


def luminance(rgb):
    values=[v/255 for v in rgb]
    values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(a*b for a,b in zip(values,(.2126,.7152,.0722)))


def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def resolve(spec=None,regional_style='generic'):
    """RGB byte tuple (background, text, accent), with readable text contrast.

The regional palette supplies a restrained hue; the real facade tint/material
supplies the other half. No independently random sign or tenant colours.
"""
    import buildings as b
    if spec is not None:
        programme=for_spec(spec)
        if programme:regional_style=programme.regional_style
        elif spec.inference is not None:
            regional_style=REGIONS.get(spec.inference.selection.environment.region,'generic')
    dark,pale=REGIONAL.get(regional_style,REGIONAL['generic'])
    wall=(.65,.65,.61)
    if spec is not None and spec.facade:
        material,rgba=b._Looks(spec.seed)[spec.facade]
        mean=b.MAT_MEAN.get(b.MATERIALS[material],(.8,.8,.8))
        wall=tuple(v/255*m for v,m in zip(rgba,mean))
    shade=tuple(.58*d+.42*w for d,w in zip(dark,wall))
    # Darken the facade-derived hue so even light walls produce a legible board.
    maximum=max(shade)
    if maximum>.38:shade=tuple(v*.38/maximum for v in shade)
    background=tuple(round(v*255) for v in shade)
    accent=tuple(round(255*(.6*p+.4*w)) for p,w in zip(pale,wall))
    cream=(249,247,236);charcoal=(18,23,25)
    foreground=max((cream,charcoal),key=lambda colour:contrast(background,colour))
    return background,foreground,accent


def for_site(court,items):
    """Use the explicitly declared primary member, never an unrelated neighbour."""
    from .regional_geography import locate
    frame=court.plan.evidence.frame.frame.as_geographic_frame()
    style=REGIONS.get(locate(frame.latitude,frame.longitude).theme,'generic')
    members=[m for m in court.plan.evidence.memberships if m.member.kind=='building']
    priority={'owner':0,'anchor':1,'member':2,'tenant':3}
    members.sort(key=lambda m:(priority.get(m.role,4),m.member.identity.namespace,m.member.identity.feature_id))
    if members:
        primary=members[0].member.identity.feature_id
        match=next((s for s,_,_ in items if str(getattr(getattr(s,'evidence',None),'source_id',''))==primary),None)
        if match is not None:return resolve(match,style)
    return resolve(regional_style=style)
