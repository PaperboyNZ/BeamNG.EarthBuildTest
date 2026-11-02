// Included at the PBR detail-color sample. Only Earth materials opt in through
// the exact detailScale marker; ordinary game materials keep their stock sample.
// RGB holds the organic map, alpha the earlier streak map's luminance.
{
    const bool bneWeathering = ld.detailScale.x == -1.03125
        && ld.detailScale.y == 1.0
        && (layerFlags & MATERIAL_LAYER_FLAG_detailMapUV1)
        && (layerFlags & MATERIAL_LAYER_FLAG_vtxColorToBaseColor);
    const float2 bneUV = bneWeathering ? float2(uv.x / -1.03125, uv.y) : uv;
    const float4 bneSample = sampleMaterialTex(texIdx, defaultSampler2D, bneUV);
    baseColorDetailMapSample = (half3)bneSample.rgb;
    if (bneWeathering) {
        // Reuse the one texture fetch for irregular runoff length. No noise
        // evaluation, extra samples, trigonometry, or per-frame CPU updates.
        float bnePatch = saturate((0.50 - bneSample.g) / 0.16);
        float bneRun = saturate((0.51 - bneSample.a) / 0.30);
        float bneBlend = saturate(((float)vtx.color.a - 0.80 + 0.17 * bnePatch + 0.06 * bneRun) * 4.5);
        bneBlend = bneBlend * bneBlend * (3.0 - 2.0 * bneBlend);
        bneBlend *= 0.78 + 0.16 * bnePatch;
        // Soften the older map a little; it is concentrated at the roof now.
        float3 bneStreak = lerp(0.5.xxx, bneSample.aaa * float3(1.025, 1.0, 0.97), 0.88);
        baseColorDetailMapSample = (half3)lerp(bneSample.rgb, bneStreak, bneBlend);
    }
}
