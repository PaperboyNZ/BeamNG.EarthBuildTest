"""Projected optional facade detail for the existing geotile scheduler.

No visibility/collision ownership. Full products retain native camera LOD; this
only avoids generating subpixel close detail before it is demanded.
"""
import math

FEATURE_M=.12
ENTER_PX=.35
KEEP_PX=.25


def pixels(distance,feature=FEATURE_M,fov=65.,height=1440.):
    values=(distance,feature,fov,height)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
        raise ValueError('projected detail requires finite numeric inputs')
    if distance<0 or feature<0 or not 1<=fov<=179 or not 64<=height<=16384:
        raise ValueError('projected detail outside supported range')
    return feature*height/(2*math.tan(math.radians(fov)*.5)*max(1.,distance))


def wanted(distance,previous=False,*,fov=65.,height=1440.,reach=350.,fast=False,free_camera=False,feature=FEATURE_M):
    """Hysteresis applies to subpixel features and the user's distance reach."""
    if fast and not free_camera:return False
    if distance>reach*(1.15 if previous else 1.):return False
    return pixels(distance,feature=feature,fov=fov,height=height)>=(KEEP_PX if previous else ENTER_PX)


def camera(value,aid,cam_aid):
    if not isinstance(value,dict) or aid!=cam_aid:return None
    try:
        x,y,z,fov,height=(value.get(k,default) for k,default in
                         (('x',None),('y',None),('z',0.),('fovDeg',65.),('h',1440.)))
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (x,y,z,fov,height)):return None
        pixels(1.,fov=fov,height=height)
        if max(abs(x),abs(y),abs(z))>1e8:return None
        return x,y,z,fov,height
    except (ValueError,TypeError):return None
