"""Reconcile completed original checklist rows with their retained evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'build/world-architecture-programme'


def main():
    path=FOLDER/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    evidence={
        'Separate resolved building/site plans, physical surfaces/collision and':['real-plan-products-fixed/results.json','plan-lifetime-tests'],
        'Define product dependency identities covering source revisions, terrain,':['real-plan-products-fixed/results.json','plan-lifetime-tests'],
        'Cache and schedule visual refinements independently, coalesce equivalent':['plan-lifetime-tests','p2-early-tests'],
        'Verify identical appearance/physics for equivalent inputs, reduced repeated':['real-plan-products-fixed/results.json','plan-lifetime-tests'],
        'Build on the existing component-template caches: batch transforms and':['typed-geometry/final.json'],
        'Preserve dimensions and output semantics without quantization. Compare':['typed-geometry/final.json'],
        'Measure complete worker cost and peak memory on houses, towers, fallbacks':['typed-geometry/final.json'],
        'Add versioned dependency cache with atomic/checksummed writes, quota,':['plan-lifetime-tests'],
        'Introduce sector manifests and client capability negotiation; preserve':['m2-transaction-checkpoint-patches/manifest.json'],
        'Give generic and unsupported-style fallbacks bounded-cost representations.':['representation-boundaries-closed/results.json','closed-fallback-tests'],
        'Derive close, middle and distant representations from the same resolved':['p3-sky-plan-checkpoint/manifest.json'],
        'Use projected feature size, camera FOV/resolution and travel demand with':['projected-demand-tests-fixed'],
        'Prioritize missing nearby coverage and approaching-camera demand over':['projected-demand-tests-fixed','mod/tests/test_building_progress.lua'],
        'Supplement vertex limits with measured import time, bytes and material':['p6-priced-import-checkpoint/manifest.json'],
        'Evaluate native or idle-cache exact vertex deduplication after final normals':['exact-vertices/results.json','exact-vertex-tests'],
    }
    doc=ROOT/'docs/GENERATION_IMPLEMENTATION_CHECKLIST.md';text=doc.read_text(encoding='utf-8')
    for row in programme['baseline_tasks']:
        if row['task'] not in evidence:continue
        row['status']='complete';row['evidence']=evidence[row['task']]
        text=text.replace('- [ ] '+row['task'],'- [x] '+row['task'],1)
    programme['completed_tasks']=sum(r['status']=='complete' for r in programme['baseline_tasks'])
    programme['roof_status']='Polygon eaves, imagery wall inset, fascia and soffits implemented; ten real-source outline fixtures; native appearance pending.'
    programme['residential_status']='26 geographic structural families across 64 regions; immutable selections, enclosed recess/screens/galleries and roof forms; native appearance pending.'
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    doc.write_text(text,encoding='utf-8')
    print(programme['completed_tasks'],'/',programme['target_completed_tasks'],'target tasks complete')


if __name__=='__main__':main()
