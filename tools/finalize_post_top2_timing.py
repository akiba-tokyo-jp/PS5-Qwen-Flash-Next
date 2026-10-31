#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the actual timestamp GPU object before packaging the diagnostic."""
import argparse,json,subprocess,sys
from pathlib import Path
from expert_q4 import require,record,write_json
from scoped_native_variant import seal
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('linked','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.linked.read_text());g=n['GPU_kernel_timing'];c=g['commands']['GPU']
    obj=c[c.index('-o')+1];require(n['link_command'].count(obj)==1,'Actual linked diagnostic GPU object required')
    require(record(c[c.index('-c')+1])==g['actual_sources']['GPU'],'Actual diagnostic GPU source changed')
    a.out.mkdir(parents=True,exist_ok=False)
    n['io_gpu_comparison'].update(GPU_command=c,GPU_source=g['actual_sources']['GPU'])
    seed=a.out/'linked-seed.private.json';write_json(seed,n)
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),
        '--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
    n=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text())
    require(n['lossless_shader_storage']['vulkan_object']==record(obj),'Selected GPU provenance must match the actual linked diagnostic')
    n['post_top2_timestamp_binding']=dict(generator=record(__file__),linked=record(a.linked),actual_GPU_object=record(obj),
        native_pending=True,ordinary_speed_comparison_valid=False)
    seal(n,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='actual_current_bounded_GPU_timestamp_diagnostic',
        candidate=record(a.out/'receipt.private.json'),actual_GPU_object=record(obj),
        original_driver_and_shader_math_preserved=True,ordinary_speed_comparison_valid=False,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
