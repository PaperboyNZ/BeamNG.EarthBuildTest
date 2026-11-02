"""Build mod-local shader hooks from the installed game's current sources.

Never edits game files or distributes copies of the engine shaders. Fail closed
when the shader contract changes. Generated paths are excluded from mod hashes;
their contents are checked independently on every install/launcher invocation.
"""
import hashlib
import json
import os
from pathlib import Path

HOOKS = {
    'shaders/common/material/shadergen/permutations.h.hlsl': 'processVisibility',
    'shaders/common/material/shadergen/v0/permutationsV0.h.hlsl': 'processVisibilityV0',
}
READY = 'shaders/beamngEarth/buildingFade.ready'
GENERATED = frozenset((*HOOKS, READY))
INCLUDE = '\n#include "shaders/beamngEarth/buildingFade.hlsl"\n'


def render(game):
    game = Path(game)
    outputs = {}
    hashes = {}
    support = game / 'shaders/common/material/shadergen/shadergen.h.hlsl'
    if 'uint4 getInstanceBaseColors(uint instanceIdx)' not in support.read_text(encoding='utf-8'):
        raise ValueError('instance palette shader contract changed')
    for name, function in HOOKS.items():
        source = (game / name).read_text(encoding='utf-8')
        signature = f'void {function}(inout Material material, float2 vPos) {{'
        if source.count(signature) != 1 or 'getInstanceVisibility(material.instanceId)' not in source:
            raise ValueError(f'visibility shader contract changed: {name}')
        if 'buildingFade.hlsl' in source:
            raise ValueError(f'game shader already contains an Earth hook: {name}')
        outputs[name] = source.replace(signature, signature + INCLUDE)
        hashes[name] = hashlib.sha256(source.encode()).hexdigest()
    outputs[READY] = json.dumps({'version': 1, 'engine_sources': hashes}, sort_keys=True) + '\n'
    return outputs


def install(mod, game):
    """Refresh generated files; return whether contents changed. No partial hook."""
    mod = Path(mod)
    outputs = render(game)  # Validate everything before writing anything.
    changed = False
    for name, content in outputs.items():
        path = mod / name
        if path.is_file() and path.read_text(encoding='utf-8') == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(content, encoding='utf-8')
        os.replace(temporary, path)
        changed = True
    return changed


def remove(mod):
    for name in GENERATED:
        (Path(mod) / name).unlink(missing_ok=True)
