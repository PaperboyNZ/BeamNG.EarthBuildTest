"""Reproducible original seamless reed colour/normal textures; no external assets."""
from pathlib import Path
import json
import uuid
import numpy as np
from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1]
    dest = root / 'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
    rng = np.random.default_rng(251102)
    n = 512
    y, x = np.mgrid[:n, :n]
    straw = np.zeros((n, n))
    for k in range(1, 70):
        straw += np.sin(2 * np.pi * (x * k / n + .004 * np.sin(2 * np.pi * y / n)) + rng.uniform(0, 6.28)) / k**.35
    straw /= max(abs(straw.min()), straw.max())
    bundles = .08 * np.cos(y * 2 * np.pi / (n / 4.))
    height = .5 + .28 * straw + bundles
    shade = np.clip(.70 + .22 * straw + bundles + rng.normal(0, .025, (n, n)), 0, 1)
    rgb = np.stack((shade, shade * .88, shade * .64), axis=-1)
    Image.fromarray((rgb * 255).astype('uint8')).save(dest / 'bne_thatch.color.png')
    dx = (np.roll(height, 1, 1) - np.roll(height, -1, 1)) * 1.4
    dy = (np.roll(height, 1, 0) - np.roll(height, -1, 0)) * 1.4
    normal = np.stack((dx, dy, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    Image.fromarray(((normal * .5 + .5) * 255).astype('uint8')).save(dest / 'bne_thatch.normal.png')
    name = 'bne_bld_roof_thatch'
    data = {name: dict(name=name, mapTo=name, **{'class': 'Material'}, version=1.5,
                      persistentId=str(uuid.uuid5(uuid.NAMESPACE_URL, 'beamng-earth/' + name)),
                      Stages=[dict(baseColorMap='/levels/beamng_earth/art/shapes/beamngEarth/bne_thatch.color.png',
                                   normalMap='/levels/beamng_earth/art/shapes/beamngEarth/bne_thatch.normal.png',
                                   normalMapStrength=1.35,
                                   roughnessMap='/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering_roughness.data.dds',
                                   roughnessMapUseUV=1, roughnessFactor=1.,
                                   detailMap='/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering.dds',
                                   detailMapUseUV=1, detailScale=[1,1], detailBaseColorMapStrength=.48,
                                   metallicFactor=0., baseColorFactor=[1,1,1,1], vertColor=True)],
                      translucent=False, doubleSided=False)}
    (dest / 'architectural_details.materials.json').write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__': main()
