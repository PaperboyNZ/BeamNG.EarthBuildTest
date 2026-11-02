"""Generate a mod-local PBR hook from installed engine source, never patch the game."""
import hashlib
import json
import os
from pathlib import Path

HOOK='shaders/common/material/shadergen/defaultMat.hlsl'
READY='shaders/beamngEarth/weatheringBlend.ready'
GENERATED=frozenset((HOOK,READY))
ANCHOR='baseColorDetailMapSample = (half3)sampleMaterialTex(texIdx, defaultSampler2D, uv).rgb;'
INCLUDE='#include "shaders/beamngEarth/weatheringBlend.hlsl"'


def render(game):
    source=(Path(game)/HOOK).read_text(encoding='utf-8')
    required=('MaterialLayer processLayers(VtxOut vtx, bool isFrontFacing)',
              'vtx.color.xyz', 'float4(ld.detailScale, ld.detailScale)')
    if source.count(ANCHOR)!=1 or any(token not in source for token in required) or INCLUDE in source:
        raise ValueError('PBR weathering shader contract changed')
    return {HOOK:source.replace(ANCHOR,INCLUDE),
            READY:json.dumps({'version':1,'engine_source':hashlib.sha256(source.encode()).hexdigest()},sort_keys=True)+'\n'}


def install(mod,game):
    outputs=render(game)
    changed=False
    for name,content in outputs.items():
        path=Path(mod)/name
        if path.is_file() and path.read_text(encoding='utf-8')==content:continue
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(path.suffix+'.tmp')
        temp.write_text(content,encoding='utf-8');os.replace(temp,path)
        changed=True
    return changed


def remove(mod):
    for name in GENERATED:(Path(mod)/name).unlink(missing_ok=True)
