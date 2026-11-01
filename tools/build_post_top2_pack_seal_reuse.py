#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse a complete immutable native pack seal with fresh inode/EOF checks."""
import argparse,json,re
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text())
 require(pack['completed']and pack['CPU_Direct_positively_retired']and len(pack['bundles'])==1024,'Complete native1024-triplet whole-SHA seal required')
 a.out.mkdir(parents=True,exist_ok=False);oc=n['all_Q2_optimized_monitor']['commands'][1];op=Path(oc[oc.index('-c')+1]);h=op.parent/'limit-winner-bundle.private.h';header=h.read_text()
 expected_sha=re.search(r'Q2_current_SHA256="([0-9a-f]{64})"',header)[1]
 identity=list(map(int,re.search(r'Q2_current_expected_identity\[\]=\{([^}]+)\}',header)[1].split(',')))
 path=re.search(r'Q2_current_path="([^"]+)"',header)[1]
 require(expected_sha==pack['output']['sha256']and identity==pack['output']['identity']and
  path=='/app0/'+pack['output']['path'].split('/PPSA99190/',1)[1]and identity[2]==0o100444,'Exact read-only native-sealed pack identity and whole SHA required')
 owner=op.read_text();owner='namespace {unsigned long long post_pack_seals_reused=0;}\nextern "C" unsigned long long qwen_post_pack_seals_reused(){return post_pack_seals_reused;}\n'+owner
 start=owner.index('void admit_Q2_current(void*scratch){');pos=owner.index('    require_named();\n    sha256_t whole;',start)
 original='    require_named();\n    sha256_t whole;'
 replacement='''    require_named();
    // The build binds the earlier native whole-SHA/EOF seal. This lifetime
    // rechecks the exact read-only named inode, descriptor and unchanged EOF.
    if(ops.read_at(Q2_current_fd,scratch,16384,current[5])!=0||ops.identity(Q2_current_fd)!=current)
        throw std::runtime_error("Previously sealed pack EOF or descriptor identity changed");
    require_named();Q2_current_identity=current;Q2_current_verified=true;++post_pack_seals_reused;return;
    sha256_t whole;'''
 owner=owner[:pos]+owner[pos:].replace(original,replacement,1)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='extern "C" unsigned long long qwen_post_pack_seals_reused();\n'+entry
 old=n['next_five_normal']['scope'];scope=dict(old,current_pack_integrity='prior_native_whole_SHA_seal_with_fresh_readonly_inode_descriptor_and_EOF',
  prior_sealed_pack_SHA256=expected_sha,prior_sealed_pack_bytes=identity[5],fresh_whole_pack_hash_not_claimed=True)
 require(entry.count(literal(old))>=1,'Actual normal scope literal required');entry=entry.replace(literal(old),literal(scope))
 marker='{"device_ledger_live_bytes",ledger.live}'
 # The ordinary terminal retains the actual reuse count; no old whole-read
 # completion is relabelled as a fresh payload read.
 require(marker in entry,'Normal positive-retirement terminal marker required')
 entry=entry.replace(marker,'{"prior_native_pack_seals_reused",qwen_post_pack_seals_reused()},'+marker)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc,owner)),[Path(__file__),a.pack,h])
 for value in r.values():
  if isinstance(value,dict)and isinstance(value.get('actual_sources'),dict):
   for k in ('entry','owner'):
    if k in value['actual_sources']:
     value['actual_sources'][k]=sources[k]
     if isinstance(value.get('commands'),dict)and k in value['commands']:value['commands'][k]=jobs[k]
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];r['all_Q2_optimized_monitor']['commands'][:2]=[jobs['entry'],jobs['owner']]
 r['routing_winners_normal']['actual_entry']=sources['entry'];r['next_five_normal'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
 r['post_top2_pack_seal_reuse']=dict(scope=scope,actual_sources=sources,commands=jobs,prior_native_pack_seal=record(a.pack),exact_original_header=record(h),native_pending=True)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='immutable_prior_native_pack_seal_reuse',candidate=record(a.out/'receipt.private.json'),
  fresh_whole_SHA_not_claimed=True,readonly_named_inode_descriptor_EOF_checks_preserved=True,original_GPU_math_and_memory_thresholds_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
