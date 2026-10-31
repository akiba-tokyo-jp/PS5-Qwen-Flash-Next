#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Put a bounded fixture into the actual selected application's startup path."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('control','fixture','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.control.read_text());f=json.loads(a.fixture.read_text())
    require(n['driver']==f['driver'],'Fixture and selected driver must match')
    a.out.mkdir(parents=True,exist_ok=False)
    fc=f['compile_commands'][0];fs=Path(fc[fc.index('-c')+1]).read_text()
    start=fs.index('        {if(policy.at("native_GDN_conv_normalization_fixture")')
    end=fs.index('        screen.state="loading original BF16 model";',start)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    header=Path(f['post_top2_gate_up']['complete_fixtures'][0]['path'])
    entry='#include '+json.dumps(header.resolve().as_posix())+'\nextern "C" void qwen_app_gate_up_trial_release();\n'+entry
    entry=once(entry,'        screen.state="loading original BF16 model";',fs[start:end]+'        screen.state="loading original BF16 model";')
    seed=copy.deepcopy(n);old=n['lossless_shader_storage']['vulkan_object']['path'];gc=f['io_gpu_comparison']['GPU_command'];obj=gc[gc.index('-o')+1]
    require(seed['link_command'].count(old)==1,'One qualified GPU provider required')
    seed['link_command'][seed['link_command'].index(old)]=obj
    seed['inputs_before']+=active_link_inputs(f)
    for key in ('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):
        seed[key]=copy.deepcopy(f[key])
    seed['io_gpu_comparison'].update(GPU_command=gc,GPU_source=f['io_gpu_comparison']['GPU_source'])
    seed['GDN_conv_normalization_fixture']=copy.deepcopy(f['GDN_conv_normalization_fixture'])
    seed['post_top2_gate_up']=copy.deepcopy(f['post_top2_gate_up'])
    seedpath=a.out/'selected-seed.private.json';write_json(seedpath,seed)
    r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry)),[Path(__file__),a.control,a.fixture,header])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
        r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
    r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    r['routing_winners_normal']['actual_entry']=sources['entry']
    unsealed=a.out/'unsealed.private.json';write_json(unsealed,r)
    run=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),
        '--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
    (a.out/'provenance.private.log').write_bytes(run.stdout+run.stderr)
    require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='selected_parent_top2_gate_up_fixture',
        candidate=record(a.out/'receipt.private.json'),scope=r['GDN_conv_normalization_fixture']['scope'],
        actual_current_model_receipt_and_startup=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
