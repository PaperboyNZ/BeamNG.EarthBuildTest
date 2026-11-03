"""Validate source-linked property evidence offline, including metric ports."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))


def validate(catalogue, *, records_out=None, site_namespace=None, owner_namespace=None):
    """Validate legacy evidence and optionally export detached M1 diagnostics.

    The export preserves the original projection; it is not a new runtime input
    format or a migration to canonical site geometry. No input file is changed.
    """
    catalogue = Path(catalogue).resolve()
    destination = Path(records_out).resolve() if records_out is not None else None
    if destination is not None:
        if not site_namespace or not owner_namespace:
            raise ValueError('records export requires explicit site_namespace and owner_namespace')
        if destination == catalogue or (destination.exists() and catalogue.exists()
                                         and destination.samefile(catalogue)):
            raise ValueError('records output must not overwrite the input catalogue')

    from buildgen import site_data
    from geodesy import EnuFrame

    previous = os.environ.get('BNE_BUILDING_SITES')
    os.environ['BNE_BUILDING_SITES'] = str(catalogue)
    site_data.catalogue.cache_clear()
    try:
        digest, rows = site_data.catalogue()
        projected = []
        for owner, feature in rows.items():
            lon, lat = feature['geometry']['coordinates'][0][0]
            site = site_data.project(owner, EnuFrame(lat, lon, 0.))
            if destination is not None:
                projected.append((owner, lon, lat, site))

        summary = dict(valid=True, properties=len(rows), sha256=digest,
                       note='Geometry/evidence validation only; runtime terrain and building fit still apply.')
        if destination is not None:
            # Only adapt after every legacy catalogue/project validator succeeds.
            from sitegen.adapters import adapt_validated_legacy_site
            from sitegen.identity import GeographicFrame, SourceIdentity
            from sitegen.plan import EntityRef, FrameContext, SiteGraph

            # Validate namespaces even for an empty catalogue.
            SourceIdentity(site_namespace, 'namespace-validation')
            SourceIdentity(owner_namespace, 'namespace-validation')
            plans = []
            for owner, lon, lat, site in projected:
                adapter = adapt_validated_legacy_site(
                    site, owner=EntityRef(SourceIdentity(owner_namespace, owner), 'building'),
                    frame=FrameContext('legacy_projected_xy', GeographicFrame(lon, lat, 0.), 0., 0.),
                    source_namespace=site_namespace)
                if adapter.to_legacy_site() != site:
                    raise ValueError('shared-record adapter changed legacy site output: ' + str(owner))
                plans.append(adapter.plan)
            graph = SiteGraph(plans)
            payload = graph.to_json()
            # Rerun the versioned decoder before publishing the offline artifact.
            if SiteGraph.from_json(payload) != graph:
                raise ValueError('shared site record serialization round trip changed the graph')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((payload + '\n').encode('utf-8'))
            summary.update(records_out=str(destination), records_schema_version=graph.to_dict()['schema_version'],
                           record_sites=len(graph.sites), physical_surface_validation='pending',
                           canonical_migration='pending')
        return summary
    finally:
        if previous is None:
            os.environ.pop('BNE_BUILDING_SITES', None)
        else:
            os.environ['BNE_BUILDING_SITES'] = previous
        site_data.catalogue.cache_clear()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalogue',type=Path)
    parser.add_argument('--records-out', type=Path, help='export versioned M1 records with legacy projected coordinates')
    parser.add_argument('--site-namespace', help='explicit source identity domain for catalogue site IDs')
    parser.add_argument('--owner-namespace', help='explicit source identity domain for building owner IDs')
    args=parser.parse_args(argv)
    if args.records_out is not None and (not args.site_namespace or not args.owner_namespace):
        parser.error('--records-out requires --site-namespace and --owner-namespace')
    print(json.dumps(validate(args.catalogue, records_out=args.records_out, site_namespace=args.site_namespace,
                              owner_namespace=args.owner_namespace), indent=2))


if __name__=='__main__':main()
