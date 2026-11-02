#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove exact unselected predecessor objects and already retired BMP copies."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import current_files

PREDECESSORS=('19dcb5e290dbb9b4-entry.o','4b19b2a98385f4a1-early-SELF.o',
    '89fa1f1408866c60-native-bootstrap-boot-qualified.o','ad508f9e6952380f-entry.o')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','retired-images','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    native_retirement=load(a.retired_images)
    need(native_retirement['completed'] and native_retirement['retired_images']==2 and
         native_retirement['both_namespaces_absent'] and native_retirement['current_seven_unchanged_and_native_hashed'],
         'Both native image retirements must already have completed')
    image_plan=load(a.retired_images.parent/'plan.private.json');current=a.current.resolve()
    package=load(current/'provenance/current-package.private.json')
    need(package['production_adopted'] and package['SELF']==record(current/'eboot.bin'),'One qualified selected production package required')
    retained=load(current/'provenance/retained-relink-inputs.private.json');native=load(current/'provenance/native-link.receipt.private.json')
    protected_rows=current_files(current)+retained+native['formatter_stubs']+[package['formatter']]
    protected={Path(r['path']).resolve():record(r['path']) for r in protected_rows}
    for row in protected_rows:need(all(protected[Path(row['path']).resolve()][k]==row[k] for k in ('bytes','sha256')),'A selected compiler/package input changed')
    targets=[];objects=(current/'linked-inputs').resolve();campaign=a.retired_images.parent.parent.resolve()
    for name in PREDECESSORS:
        path=(objects/name).resolve()
        need(path.parent==objects and path not in protected and path.is_file() and not path.is_symlink(),
             'Only the four exact unselected predecessor objects may be retired')
        targets.append(dict(record(path),kind='unselected_predecessor_object'))
    for row in image_plan['targets']:
        path=Path(row['path']).resolve()
        need(path.is_relative_to(campaign) and path.name in ('native.arm1.display.bmp.private.bin','native.arm2.display.bmp.private.bin') and
             path not in protected and not path.is_symlink(),'Only the two already retired exact BMP copies may be removed')
        value=record(path);need(all(value[k]==row[k] for k in ('path','bytes','sha256')),'The independently matched BMP copy changed')
        targets.append(dict(value,kind='retired_native_BMP_copy'))
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'intent.private.json',dict(targets=targets,protected=list(protected.values()),
        native_image_retirement=record(a.retired_images),PS5_requests=0,recursive_operations=0))
    if not a.execute:return
    for row in targets:
        path=Path(row['path']);need(record(path)=={k:row[k] for k in ('path','bytes','sha256')},'A target changed before its unlink')
        path.unlink()
    need(all(record(path)==value for path,value in protected.items()),'A selected input changed during cleanup')
    need(all(not Path(row['path']).exists() for row in targets),'An exact retired target remains')
    result=dict(completed=True,retired_files=len(targets),retired_bytes=sum(r['bytes'] for r in targets),
        selected_files_protected=len(protected),all_selected_whole_SHA256_values_unchanged=True,
        native_image_retirement=record(a.retired_images),PS5_requests=0,recursive_operations=0)
    save(a.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()
