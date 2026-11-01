#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Instrument exact pinned PS5 submit members without changing their policy or ABI."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from build_throughput_current import command
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
WS='src/amd/vulkan/winsys/ps5/'
NAMES=['sequence_wait_calls','sequence_wait_ns','marker_poll_calls','known_complete_returns','marker_flush_polls','snapshot_races',
       'spin_iterations','sleep_calls','sleep_ns','requested_sleep_us','submit_calls','submit_ns','submit_lock_calls','submit_lock_ns',
       'submit_lock_hold_ns','claim_calls','claim_ns','dedicated_claims','overlap_waits','record_capacity_waits','copy_calls','copy_ns',
       'unused22','unused23','unused24','unused25','command_words','unused27','unused28','sync_wait_calls','sync_wait_ns',
       'unused31','unused32','unused33','unused34','unused35','unused36','unused37','unused38','unused39',
       'platform_flush_ns','platform_AGC_ns','platform_suspend_ns','unused43','unused44','unused45','unused46','enabled']

def region(text,signature):
    a=text.index(signature);begin=text.index('{',a);depth=1;i=begin+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return a,begin,i

def transform(name,text):
    # Put declarations after all original includes so Mesa atomics and clock are available.
    lines=text.splitlines(True);at=max(i for i,l in enumerate(lines)if l.startswith('#include '))+1
    lines.insert(at,'\n#include "submission_timing.h"\n');text=''.join(lines)
    if name=='radv_ps5_winsys.c':
        text += '''\nuint64_t qwen_submit_timing[48];
unsigned qwen_submit_timing_enabled;
void qwen_ps5_timing_select(unsigned enabled) {p_atomic_set(&qwen_submit_timing_enabled, !!enabled);}
void qwen_ps5_timing_snapshot(uint64_t *out) {
    for(unsigned i=0;i<48;++i)out[i]=p_atomic_read(&qwen_submit_timing[i]);
    uint64_t platform[3];radv_ps5_submit_times(platform);
    for(unsigned i=0;i<3;++i)out[40+i]=platform[i];out[47]=p_atomic_read(&qwen_submit_timing_enabled);
}
'''
        text=once(text,'   const uint64_t submitted = p_atomic_read(&queue->submitted_seq);','   qwen_timing_add(2,1);\n   const uint64_t submitted = p_atomic_read(&queue->submitted_seq);')
        text=once(text,'   if (known == submitted)\n      return known;','   if (known == submitted) {qwen_timing_add(3,1);return known;}')
        text=once(text,'   radv_ps5_cpu_flush((const void *)queue->marker, sizeof(*queue->marker));\n   const uint32_t marker','   qwen_timing_add(4,1);radv_ps5_cpu_flush((const void *)queue->marker, sizeof(*queue->marker));\n   const uint32_t marker')
        text=once(text,'   if (p_atomic_read(&queue->submitted_seq) != submitted)\n      return p_atomic_read(&queue->completed_seq);','   if (p_atomic_read(&queue->submitted_seq) != submitted) {qwen_timing_add(5,1);return p_atomic_read(&queue->completed_seq);}')
        a,b,e=region(text,'radv_ps5_queue_wait_seq(');section=text[a:e];section=section.replace('{','{\n   QWEN_TIMING_SCOPE(0);',1)
        section=once(section,'      if (now < spin_until)\n         __builtin_ia32_pause();\n      else\n         radv_ps5_sleep_us(1000);','      if (now < spin_until) {qwen_timing_add(6,1);__builtin_ia32_pause();}\n      else {QWEN_TIMING_SCOPE(7);qwen_timing_add(9,1000);radv_ps5_sleep_us(1000);}')
        text=text[:a]+section+text[e:]
    elif name=='radv_ps5_cs.c':
        a,b,e=region(text,'radv_ps5_queue_claim(');s=text[a:e];s=s.replace('{','{\n   QWEN_TIMING_SCOPE(15);',1)
        s=once(s,'   if (count > RADV_PS5_RING_WORDS / 2) {','   if (count > RADV_PS5_RING_WORDS / 2) {qwen_timing_add(17,1);')
        s=once(s,'      if (!radv_ps5_queue_wait_seq(queue, oldest, OS_TIMEOUT_INFINITE))','      qwen_timing_add(19,1);if (!radv_ps5_queue_wait_seq(queue, oldest, OS_TIMEOUT_INFINITE))')
        s=once(s,'      if (!radv_ps5_queue_wait_seq(queue, record->seq, OS_TIMEOUT_INFINITE))','      qwen_timing_add(18,1);if (!radv_ps5_queue_wait_seq(queue, record->seq, OS_TIMEOUT_INFINITE))');text=text[:a]+s+text[e:]
        a,b,e=region(text,'radv_ps5_cs_submit(');s=text[a:e];s=s.replace('{','{\n   QWEN_TIMING_SCOPE(10);',1)
        s=once(s,'   simple_mtx_lock(&queue->submit_lock);','   uint64_t qwen_lock_start=p_atomic_read(&qwen_submit_timing_enabled)?os_time_get_nano():0;\n   simple_mtx_lock(&queue->submit_lock);\n   uint64_t qwen_lock_owned=qwen_lock_start?os_time_get_nano():0;\n   if(qwen_lock_start){qwen_timing_add(12,1);qwen_timing_add(13,qwen_lock_owned-qwen_lock_start);}')
        s=s.replace('simple_mtx_unlock(&queue->submit_lock);','if(qwen_lock_owned)qwen_timing_add(14,os_time_get_nano()-qwen_lock_owned);simple_mtx_unlock(&queue->submit_lock);')
        s=once(s,'   const uint64_t copy_end = os_time_get_nano();','   const uint64_t copy_end = os_time_get_nano();\n   qwen_timing_add(20,1);qwen_timing_add(21,copy_end-copy_start);qwen_timing_add(26,count);');text=text[:a]+s+text[e:]
    elif name=='radv_ps5_sync.c':
        a,b,e=region(text,'radv_ps5_sync_wait_many(');s=text[a:e];s=s.replace('{','{\n   QWEN_TIMING_SCOPE(29);',1);text=text[:a]+s+text[e:]
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    driver=a.workspace/'driver-work/PS5-Vulkan-Inference';profile=driver/'.local/qwen-cumulative-872cc126-001';m=json.loads((profile/'manifest.private.json').read_text());mesa=a.workspace/'vendor/PS5_Mesa'
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=mesa,text=True).strip()==m['mesa_commit'],'Pinned Mesa source required')
    sys.path.insert(0,str(driver/'driver/mesa'));from build_idle_marker import members
    base=Path(next(x for x in n['link_command']if x.endswith('libvulkan-cold-tables.a')));before=members(base)
    common=m['commands'][1].copy();replacements={};commands=[];sources=[]
    build_dir=a.workspace/'build/gpu_probe/radv-ps5-windows'
    require((build_dir/'compile_commands.json').is_file(),'Exact generated Mesa include tree required')
    for name in ('radv_ps5_winsys.c','radv_ps5_cs.c','radv_ps5_sync.c'):
        original=profile/'source'/WS/name if name=='radv_ps5_winsys.c'else mesa/WS/name
        source=a.out/name;source.write_text(transform(name,original.read_text()),newline='\n');obj=a.out/('winsys_ps5_'+name+'.o');cmd=common.copy()
        cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(name+'.d'))
        fixed=[]
        for x in cmd:
            if x.startswith('-I')and not Path(x[2:]).is_absolute():
                rel=x[2:].replace('\\','/');rel='/'.join(t for t in rel.split('/')if t)
                x='-I'+str((build_dir/rel).resolve())
            fixed.append(x)
        fixed+=['-I'+str(ROOT/'native/driver')]
        run=subprocess.run(fixed,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/(name+'.log')).write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
        replacements[('winsys_ps5_'+name+'.o',0)]=obj;commands.append(fixed);sources.append(record(source));print('Compiled '+name,flush=True)
    archive=a.out/'libvulkan-observed.a';ar=Path(common[0]).with_name('llvm-ar.exe')
    # Let LLVM preserve required member-data alignment, including embedded CL objects.
    shutil.copyfile(base,archive)
    result=subprocess.run([str(ar),'r',str(archive),*map(str,replacements.values())],capture_output=True,timeout=120)
    require(result.returncode==0,result.stderr.decode(errors='replace'));after=members(archive)
    require(before.keys()==after.keys()and {k for k in before if before[k]!=after[k]}==set(replacements),'Exactly three observation-only winsys members may change')
    seed=json.loads(json.dumps(n));seed['link_command']=[str(archive)if x==str(base)else x for x in n['link_command']];seed['inputs_before']=[x for x in seed['inputs_before']if x['path']!=str(base)]+[record(archive)]
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='''#include <cstdint>
extern "C" void qwen_ps5_timing_select(unsigned);
extern "C" void qwen_ps5_timing_snapshot(std::uint64_t*);
'''+entry
    # Keep both arms at actual production throughput mode; the only arm delta is observation.
    entry=once(entry,'qwen_throughput::mode=arm?5:0;','qwen_throughput::mode=5u;qwen_ps5_timing_select(arm);')
    marker='            const auto cpu_before=qwen_load::snapshot();';entry=once(entry,marker,'            std::uint64_t driver_before[48]{};qwen_ps5_timing_snapshot(driver_before);\n'+marker)
    marker='            row["phase"]=phase;';entry=once(entry,marker,'            std::uint64_t driver_after[48]{};qwen_ps5_timing_snapshot(driver_after);Json driver_delta=Json::array();for(unsigned j=0;j<47;++j)driver_delta.push_back(driver_after[j]-driver_before[j]);row["driver_timing_delta"]=driver_delta;row["driver_timing_enabled"]=bool(arm);\n'+marker)
    scope=dict(n['GDN_model_comparison']['scope'],control_throughput_mode=5,candidate_throughput_mode=5,driver_observation_only=True,observation_candidate_only=True,diagnostic_not_speed_candidate=True)
    from build_cache_capacity_1125 import literal
    entry=once(entry,literal(n['GDN_model_comparison']['scope']),literal(scope))
    seed['GDN_model_comparison']['scope']=scope;seed['next_five_comparison']['scope']=scope
    seedpath=a.out/'driver-seed.private.json';write_json(seedpath,seed);out=a.out/'variant';out.mkdir();r,jobs,actual=link(seedpath,out,dict(entry=(ec,entry)),[Path(__file__),ROOT/'native/driver/submission_timing.h',*map(lambda x:Path(x['path']),sources)])
    r['submission_observer']=dict(scope=scope,counter_names=NAMES,driver_archive=record(archive),driver_sources=sources,compile_commands=commands,changed_members=[list(x)for x in replacements],unrelated_members_identical=True,ABI_unchanged=True,actual_sources=actual,commands=jobs)
    seal(r,a.workspace,a.cache,out);write_json(a.out/'observer.private.json',r['submission_observer']);print(json.dumps(dict(completed=True,receipt=str(out/'receipt.private.json'),counters=len(NAMES))))
if __name__=='__main__':main()
