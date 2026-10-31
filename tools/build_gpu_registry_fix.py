#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Handle repeated and distinct logical-device shader initialization safely."""
import argparse,json
from pathlib import Path
from build_io_gpu_comparison import registry_fix
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
from build_model_io import validate_overrides
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);gc=n['io_gpu_comparison']['GPU_command'];text=Path(gc[gc.index('-c')+1]).read_text()
 r,jobs,sources=link(a.parent,a.out,dict(GPU=(gc,registry_fix(text))),[Path(__file__),Path(__file__).with_name('build_io_gpu_comparison.py')])
 r['io_gpu_comparison'].update(GPU_source=sources['GPU'],GPU_command=jobs['GPU'],bounded_logical_device_registry=8,repeated_device_pipeline_reuse=True)
 m=json.loads(Path(n['bounded_model_source_manifest']['path']).read_text());row=next(x for x in m['objects']if x['source'].endswith('ggml-vulkan.cpp'));row.update(object=record(a.out/'GPU.o'),command=jobs['GPU'],actual_source=sources['GPU']);m['sources'][row['source']]['patched_sha256']=sources['GPU']['sha256'];mp=a.out/'model-io.private.json';write_json(mp,m)
 r['bounded_model_source_manifest']=record(mp);r['bounded_model_source_overrides']=validate_overrides(mp,Path(r['engine_receipt']['path']));r['lossless_shader_storage']['vulkan_object']=row['object'];r['inputs_before'].append(record(mp));seal(r,a.workspace,a.cache,a.out)
if __name__=='__main__':main()
