#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Continue only uncreated bundle parts after a known, positively closed writer."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','terminal','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.parent.read_text());raw=a.terminal.read_text();ends=[x for x in raw.splitlines()if x.startswith('END ')]
 require(len(ends)==1 and'END success=0 'in ends[0]and'nonce='+old['nonce']in ends[0]and'DIRECT known_completion_cleanup_returned=1 fully_released=1'in raw and'REFUSED reason=Bundle part write was short'in raw,'Known ended writer with positive Direct release required')
 seals=[dict(re.findall(r'(\w+)=([^ ]+)',x))for x in raw.splitlines()if x.startswith('SEALED ')];first=len(seals)
 require(first==61 and[int(x['part'])for x in seals]==list(range(first)),'Only the known 61-part completed prefix may be reused')
 remaining=old['new_output_bytes']-sum(int(x['bytes'])for x in seals);require(remaining==5156241408,'Exact ten-part continuation required')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);base=a.parent.parent;remote='/data/ai/moss-qwen-bundle-tail-'+nonce;directory='/data/ai/native-moss-image-sft/PPSA99190/qwen-full-bundles-'+nonce
 header=a.out/'full_bundle_plan.private.h';text=(base/header.name).read_text().replace(old['nonce'],nonce);header.write_text(text,newline='\n')
 source=ROOT/'native/qwen_flash_next/expert_q2_full_bundle_pack.cpp';text='#include <cerrno>\n'+source.read_text();text=once(text,'for(unsigned part=0;part<full_bundle_parts;++part)','for(unsigned part=61;part<full_bundle_parts;++part)');text=once(text,'full_bundle_total_bytes+(256ull<<20)',str(remaining)+'ULL+(256ull<<20)')
 text=once(text,'for(unsigned i=0;i<count;++i){boundary();need(split_context(3),"Idle CPU source owner changed");','for(unsigned i=0;i<count;++i){boundary();if(i%32==0)need(split_context(3),"Idle CPU source owner changed");')
 before='expected[i]=digest(bundle,L::stride);need(pwrite(output,bundle,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride),"Bundle part write was short");'
 after='''expected[i]=digest(bundle,L::stride);std::size_t written=0;
            while(written<L::stride){boundary();const auto left=L::stride-written;const auto got=pwrite(output,bundle+written,left,uint64_t(i)*L::stride+written);const int error=errno;
                if(got<=0||std::uint64_t(got)>left||std::uint64_t(got)%16384){line("WRITE_REFUSED part="+std::to_string(part)+" Expert="+std::to_string(i)+" known_bytes="+std::to_string(written)+" returned="+std::to_string(got)+" errno="+std::to_string(error));need(false,"Finite aligned bundle write refused");}
                written+=std::size_t(got);
            }'''
 text=once(text,before,after);cpp=a.out/'continuation.private.cpp';cpp.write_text(text,newline='\n')
 for name in('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((base/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[[v.replace(str(base),str(a.out))for v in command]for command in old['commands']];commands[1][commands[1].index('-c')+1]=str(cpp)
 for i,c in enumerate(commands):
  run=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()};require(names<=old['runtime_imports'].keys(),'Only existing qualified runtime imports permitted')
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-full-bundle-continuation-v1',completed_build=True,artifact=record(artifact),commands=commands,nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',new_directory=directory,first_part=61,new_parts=10,remaining_Experts=3348,new_output_bytes=remaining,per_part=348,CPU_only=True,owned_Direct_bytes=8<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,known_positive_partial_writes_advance_offset_only=True,all_original_memory_and_context_predicates_preserved=True,whole_native_SHA256_after_immutable_seal=True,parent=record(a.parent),prior_terminal=record(a.terminal),inputs=[record(x)for x in(Path(__file__),source,a.parent,a.terminal,header,cpp,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')],runtime_imports={k:old['runtime_imports'][k]for k in names}))
 print(json.dumps(dict(continued_parts=10,existing_sealed_parts_not_rewritten=61,bytes=remaining,CPU_Direct_bytes=8<<20,GPU_calls=0)))
if __name__=='__main__':main()
