// Included inside processVisibility[ V0 ], including depth/shadow passes.
// The marker uses an otherwise unused instance palette channel. No material
// flags, alpha blending, textures, geometry, or collision are changed.
// Also clip the depth-equal color pass: coplanar revisions can have identical
// depth, so the prepass alone cannot identify which version owns this pixel.
{
    float4 bneFade = unpackColor(getInstanceBaseColors(material.instanceId)[2]);
    uint4 bneBytes = (uint4)round(bneFade * 255.0);
    if (bneBytes.b == 173u && bneBytes.a == 91u) {
        // Ordered 8x8 mask, identical for both versions, with strictly
        // complementary tests. Midpoint thresholds avoid equal-boundary holes.
        uint2 p = (uint2)vPos & 7u;
        uint rank = 0u;
        [unroll] for (uint bit = 0u; bit < 3u; ++bit) {
            uint x = (p.x >> bit) & 1u;
            uint y = (p.y >> bit) & 1u;
            rank |= ((x ^ y) * 2u + y) << (4u - bit * 2u);
        }
        float threshold = (float(rank) + 0.5) / 64.0;
        bool incoming = threshold < bneFade.r;
        bool keep = bneBytes.g == 255u ? !incoming : incoming;
        clip(keep ? 1.0 : -1.0);
    }
}
