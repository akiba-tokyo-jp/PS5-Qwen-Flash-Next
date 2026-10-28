#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the measured production 128-slot reader into the adaptive experiment."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','qualified','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());qualified=json.loads(a.qualified.read_text())
    original=[x for x in prior['link_command']if 'mapped-source'in Path(x).name and x.endswith('.o')]
    selected=[x for x in qualified['link_command']if 'mapped-source'in Path(x).name and x.endswith('.o')]
    if len(original)!=1 or len(selected)!=1 or original==selected:raise ValueError('One distinct actual qualified source-reader object is required')
    frozen=list({r['path']:r for r in prior['inputs_before']+qualified['inputs_before']+[prior['artifact'],qualified['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen qualification input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();link=[selected[0]if x==original[0]else x for x in prior['link_command']]
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    r=subprocess.run(link,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
    (a.out/'link.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3500:])
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,source_parent=record(a.parent),
        inputs_before=frozen+[record(a.parent),record(a.qualified),record(Path(__file__)),record(selected[0])],
        qualified_reader_relink=dict(removed=record(original[0]),selected=record(selected[0]),production_receipt=record(a.qualified),actual_128_slot_six_demand_guard_reused=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Relink audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(qualified_reader_relinked=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
