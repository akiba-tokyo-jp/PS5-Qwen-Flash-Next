#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add an omitted identity audit to a new receipt without rebuilding valid bytes."""
import argparse
from pathlib import Path

from build_performance_quantizer import record
from package_retained_current import audit_identity_provider
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--package',type=Path,action='append',required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    selected=load(a.current/'provenance/current-package.private.json');identity=selected['required_bundle_identity_audit']['provider']
    need(record(identity['path'])==identity,'Selected identity provider receipt changed')
    results=[]
    for i,path in enumerate(a.package):
        package=load(path);need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and
            record(package['SELF']['path'])==package['SELF'] and record(package['relink']['path'])==package['relink'],
            'Only an unchanged completed SELF and actual relink are admitted')
        audit=audit_identity_provider(load(package['relink']['path']),identity['path'])
        package.update(required_bundle_identity_audit=audit,identity_audit_supplement_of=record(path),
            original_formatter_and_roundtrip_not_replayed=True)
        target=a.out/('package-'+str(i)+'.private.json');save(target,package);results.append(record(target))
    save(a.out/'result.private.json',dict(completed=True,packages=results,actual_linked_identity_definitions_verified=3*len(results),
        SELF_bytes_changed=False,builds=0,formatter_runs=0,PS5_operations=0))
    print(dict(completed=True,packages=len(results),SELF_bytes_changed=False,builds=0,PS5_operations=0))


if __name__=='__main__':main()
