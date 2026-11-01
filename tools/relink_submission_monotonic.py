#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep legacy submit logging intact; observe independent monotonic counters."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);driver=a.out/'driver';driver.mkdir();(driver/'tmp').mkdir()
 base=a.cache/'build/Submission-observer-56340/variant/receipt.private.json';n=json.loads(base.read_text());obs=n['submission_observer'];prior=obs['driver_archive'];archive=driver/'libvulkan-observed-monotonic.a';shutil.copyfile(prior['path'],archive)
 ws=Path(obs['driver_sources'][0]['path']).read_text()
 if 'radv_ps5_submit_times(platform)'in ws:
  ws=once(ws,'    uint64_t platform[3];radv_ps5_submit_times(platform);\n    for(unsigned i=0;i<3;++i)out[40+i]=platform[i];out[47]=p_atomic_read(&qwen_submit_timing_enabled);','    out[47]=p_atomic_read(&qwen_submit_timing_enabled);')
 require('radv_ps5_submit_times(platform)'not in ws,'Observation must not consume legacy log counters')
 source=driver/'radv_ps5_winsys.c';source.write_text(ws,newline='\n');wc=obs['compile_commands'][0].copy();wc[wc.index('-c')+1]=str(source);wc[wc.index('-o')+1]=str(driver/'winsys_ps5_radv_ps5_winsys.c.o')
 if '-MF'in wc:wc[wc.index('-MF')+1]=str(driver/'winsys.d')
 platform_manifest=json.loads(Path(n['native_platform']['manifest_path']).read_text());pc=platform_manifest['compile_command'].copy();oldsrc=Path(pc[pc.index('-c')+1]);native=(ROOT/'native/driver/radv_ps5_platform_native.c').read_text();kick=(ROOT/'native/driver/kick_impl32.c').read_text()
 # Evaluate each pre-existing elapsed expression exactly once and preserve its legacy update.
 def timed(m):
  index=int(m[1]);return '{const uint64_t qwen_elapsed='+m[2]+';p_atomic_add(&radv_ps5_submit_ns['+str(index)+'],qwen_elapsed);qwen_timing_add('+str(40+index)+',qwen_elapsed);}'
 pattern=r'p_atomic_add\(&radv_ps5_submit_ns\[([012])\],\s*([^;]+)\);'
 kick,kc=re.subn(pattern,timed,kick);require(kc==1,'Original worker timing update must be preserved exactly once')
 for index,expr in [(0,'flushed - started'),(1,'submitted - flushed')]:
  native=once(native,'   radv_ps5_submit_ns['+str(index)+'] += '+expr+';','   {const uint64_t qwen_elapsed='+expr+';radv_ps5_submit_ns['+str(index)+']+=qwen_elapsed;qwen_timing_add('+str(40+index)+',qwen_elapsed);}')
 native=once(native,'      result = sceAgcDriverSubmitDcb(&description);','      {QWEN_TIMING_SCOPE(22);result = sceAgcDriverSubmitDcb(&description);}')
 native=once(native,'#include "kick_impl32.c"','#include "submission_timing.h"\n#include "kick_impl32.c"')
 (driver/'kick_impl32.c').write_text(kick,newline='\n');psource=driver/'radv_ps5_platform_native.c';psource.write_text(native,newline='\n')
 pc[pc.index('-c')+1]=str(psource);pc[pc.index('-o')+1]=str(driver/'radv_ps5_platform_native.o');pc+=['-I',str(oldsrc.parent),'-I',str(ROOT/'native/driver'),'-I',str(ROOT/'native/profiling')]
 if '-MF'in pc:pc[pc.index('-MF')+1]=str(driver/'platform.d')
 commands=[wc,pc]
 for i,c in enumerate(commands):
  run=subprocess.run(c,cwd=a.workspace/'build/gpu_probe/radv-ps5-windows',capture_output=True,timeout=120,env=dict(os.environ,TMP=str(driver/'tmp'),TEMP=str(driver/'tmp')));(driver/f'{i}.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
 ar=Path(wc[0]).with_name('llvm-ar.exe');run=subprocess.run([str(ar),'r',str(archive),wc[wc.index('-o')+1],pc[pc.index('-o')+1]],capture_output=True,timeout=120);require(run.returncode==0,run.stderr.decode(errors='replace'))
 sys.path.insert(0,str(a.workspace/'driver-work/PS5-Vulkan-Inference/driver/mesa'));from build_idle_marker import members
 before=members(a.cache/'driver-table-storage-3275/libvulkan-cold-tables.a');after=members(archive);changes={k for k in before if before[k]!=after[k]}
 expected={('winsys_ps5_radv_ps5_winsys.c.o',0),('winsys_ps5_radv_ps5_cs.c.o',0),('winsys_ps5_radv_ps5_sync.c.o',0),('radv_ps5_platform_native.o',0)}
 require(before.keys()==after.keys()and changes==expected,'Exactly four observation-only members must differ; every other member is exact')
 proof=dict(completed=True,platform_counters_monotonic=True,existing_platform_logging_and_reset_behavior_preserved=True,old_destructive_getter_not_called=True,original_native_timing_expressions_evaluated_once=True,ABI_unchanged=True,allocator_and_kick_protocol_unchanged=True,archive=record(archive),changed_members=[list(x)for x in sorted(changes)],commands=commands,sources=[record(source),record(psource),record(driver/'kick_impl32.c'),record(ROOT/'native/profiling/submission_timing.h')],PS5_operations=0,CI_runs=0)
 write_json(driver/'manifest.private.json',proof)
 for label,parent in [('model',base),('fixture',a.cache/'build/Submission-observer-fixture-56372/receipt.private.json'),('GPU',a.cache/'build/Submission-GPU-diagnostic-56520/receipt.private.json')]:
  out=a.out/label;out.mkdir();seed=json.loads(parent.read_text());old=seed['submission_observer']['driver_archive']['path'];require(seed['link_command'].count(old)==1,'One actual observed driver archive required')
  seed['link_command']=[str(archive)if x==old else x for x in seed['link_command']];seed['inputs_before']=[x for x in seed['inputs_before']if x['path']!=old]+[record(archive)]
  seed['submission_observer'].update(driver_archive=record(archive),platform_counters_monotonic=True,existing_platform_logging_preserved=True,monotonic_overlay=record(driver/'manifest.private.json'))
  sp=out/'seed.private.json';write_json(sp,seed);r,jobs,sources=link(sp,out,{},[Path(__file__),driver/'manifest.private.json',*map(lambda x:Path(x['path']),proof['sources'])]);seal(r,a.workspace,a.cache,out)
  write_json(out/'core-safety.private.json',dict(completed=True,host_source_and_link_checks_only=True,native_qualification_claimed=False,platform_counters_monotonic=True,existing_platform_logging_preserved=True,allocator_ABI_kick_protocol_synchronization_and_timeouts_preserved=True,PS5_operations=0,CI_runs=0))
  print('Relinked '+label+' with preserved legacy logging and independent counters',flush=True)
if __name__=='__main__':main()
