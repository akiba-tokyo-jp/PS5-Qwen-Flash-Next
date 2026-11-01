#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep external disk observations and allocation-free failure-message evidence."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

APP_STATFS='''        {struct statfs storage{};char line[256];
        const int status=statfs("/app0/qwen-runtime",&storage);
        std::snprintf(line,sizeof(line),"post_top2_disk_observation status=%d block_bytes=%llu available_blocks=%lld",status,
            static_cast<unsigned long long>(storage.f_bsize),static_cast<long long>(storage.f_bavail));qwen_native_stage(line);
        if(status||storage.f_bsize<=0||storage.f_bavail<=0)throw std::runtime_error("Current application filesystem has no observed writable blocks");}
'''

def transform(entry):
    # Root CPU-helper qualification does not qualify this call in a native title.
    # Case31100 exited at this added boundary, before model loading. Preserve its
    # image and use the previously qualified external CPU observation instead.
    if APP_STATFS in entry:entry=once(entry,APP_STATFS,'')
    entry=entry.replace('#include <sys/mount.h>\n','')
    if '#include <cstdio>\n'not in entry:entry='#include <cstdio>\n'+entry
    marker='        qwen_native_stage("resident_additional_exception_work_stopped");'
    if 'returned_model_exception message='not in entry:
        entry=once(entry,marker,'''        {char emergency[768];std::snprintf(emergency,sizeof(emergency),"returned_model_exception message=%.680s",e.what());qwen_native_stage(emergency);}
'''+marker)
    return entry

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    ec=n['compile_commands'][0];entry=transform(Path(ec[ec.index('-c')+1]).read_text())
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__)])
    update_sources(r,jobs,sources)
    for key in ('next_five_comparison','post_top2_selection','post_top2_causal','post_top2_gate_up_model'):
        if key in r:r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
    r['post_top2_reporting']=dict(pre_GPU_application_statfs=False,external_CPU_disk_observation_only=True,
        extra_software_disk_margin_bytes=0,fixed_stack_emergency_error_bytes=768,
        original_full_failure_report_retained=True,interrupted30800_and_exited31100_preserved=True)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='post_top2_external_disk_and_emergency_reporting',
        candidate=record(a.out/'receipt.private.json'),scope=r['GDN_model_comparison']['scope'],
        actual_GPU_engine_and_model_unchanged=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
