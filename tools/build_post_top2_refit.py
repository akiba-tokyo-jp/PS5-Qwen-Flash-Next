#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use current decode misses to select more keys in an already sealed pack."""
import argparse,collections,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_post_top2_submission import gpu_source
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from ring_stream_source import transform as ring
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def selection(cache,pack):
 selection=json.loads(Path(pack['selection']['path']).read_text())['Experts'];available={(x['layer'],x['expert'])for x in selection};old={(x['layer'],x['expert'])for x in selection[:348]}
 screen=cache/'build/Post-top2-placement-screen-34440';fills=json.loads((screen/'fills.private.json').read_text());paths=[cache/f'hardware-first-generation-33300/native-arm{i}.routes.private.json'for i in(2,3,10,11,12,13)];traces=[json.loads(x.read_text())['records']for x in paths]
 counts=collections.Counter()
 for j in(0,1):
  require(len(traces[j])==len(fills[j]['rows']),'Exact event correspondence required')
  for event,row in zip(traces[j],fills[j]['rows']):
   require(event['layer']==row['layer']and event['tokens']==row['tokens']and event['experts']in(2,6),'Exact current route geometry required')
   if event['experts']==2:
    for expert in row['fills']:
     key=row['layer'],expert
     if key in available:counts[key]+=1
 selected=old|set(counts);require(old<=selected<=available,'Preserve every original key; reuse existing file only')
 before=[];after=[]
 for rows,events in zip(fills,traces):
  b=a=0
  for row,event in zip(rows['rows'],events):
   for expert in row['fills']:
    key=row['layer'],expert;b+=key in old;a+=key in(selected if event['experts']==2 else old)
  before.append(b);after.append(a)
 return selection,old,selected,dict(completed=True,fit_ordinals=[2,3],held_out_ordinals=[10,11,12,13],old_keys=348,new_decode_keys=len(selected),
  previous_supplement_covered_misses=before,new_phase_supplement_covered_misses=after,prior_keys_never_removed=True,
  new_weight_files=0,PS5_operations=0,inputs=[record(screen/'fills.private.json'),*[record(x)for x in paths]])

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--combination',action='store_true');a=p.parse_args();n=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text())
 require(pack['completed']and pack['CPU_Direct_positively_retired']and len(pack['bundles'])==1024,'Complete existing native1024-triplet seal required')
 require(record(pack['selection']['path'])==pack['selection'],'Exact sealed pack selection required');a.out.mkdir(parents=True,exist_ok=False)
 entries,old,selected,screen=selection(a.cache,pack);write_json(a.out/'screen.private.json',screen)
 row=pack['output'];pairs=sorted((x['layer'],x['expert'],i)for i,x in enumerate(entries));path='/app0/'+row['path'].split('/PPSA99190/',1)[1]
 arrays=lambda values:','.join('{'+f'{l},{e}'+'}'for l,e in sorted(values))
 header=a.out/'limit-winner-bundle.private.h';header.write_text('#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr const char*Q2_current_path='+json.dumps(path)+';\ninline constexpr const char*Q2_current_SHA256='+json.dumps(row['sha256'])+';\ninline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\ninline constexpr std::array<unsigned,2>Q2_current_keys[]={'+arrays((l,e)for l,e,i in pairs)+'};\ninline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\ninline constexpr std::array<unsigned,2>Q2_original_keys[]={'+arrays(old)+'};\ninline constexpr std::array<unsigned,2>Q2_decode_keys[]={'+arrays(selected)+'};\ninline bool Q2_current_mode=false,Q2_trial_mode=false;\n',newline='\n')
 oldscope=n['GDN_model_comparison']['scope'];scope=dict(oldscope,candidate='phase_refit_existing_pack',candidate_id=1,control_Experts=2,candidate_Experts=2,
  control_decode_supplement_keys=348,candidate_decode_supplement_keys=len(selected),all_original_keys_preserved=True,common_sealed_triplets=1024,
  common_file_bytes=row['bytes'],new_weight_files=0,extra_Expert_cache_slots=0,common_submission_node_cap=16)
 if a.combination:
  require(oldscope.get('adaptive_prefill')and oldscope['final_prefill_tokens']==16,'Qualified adaptive-window parent required')
  scope.update(candidate='adaptive_prefill_refit_owned_ring',candidate_prefill_all1024_triplets=True,extra_owned_CPU_source_bytes=2<<20,
   maximum_simultaneous_SSD_reads=4,maximum_source_slots=5,ring_mechanism_counters=True)
 ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1];gc=n['io_gpu_comparison']['GPU_command']
 entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(oldscope),literal(scope))
 if not a.combination:entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);')
 entry=once(entry,'qwen_app_io_trial_select(true);','qwen_app_io_trial_select(arm==1);')
 entry='#include <cstdint>\nextern "C" std::uint64_t qwen_post_refit_key_lookups();\n'+entry
 entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            const auto refit_before=qwen_post_refit_key_lookups();\n            const auto perf=performance_snapshot(*engine);')
 entry=once(entry,'            row["phase"]=phase;','            row["refit_new_key_lookups"]=qwen_post_refit_key_lookups()-refit_before;\n            row["phase"]=phase;')
 if not a.combination:
  for b,c in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:entry=once(entry,b,c)
 owner_path=Path(oc[oc.index('-c')+1]);owner=owner_path.read_text();owner=once(owner,'std::uint64_t(first%512)*1540096','std::uint64_t(first-(current?1024:(extra?512:0)))*1540096')
 expr='(Q2_trial_mode||std::binary_search(std::begin(Q2_original_keys),std::end(Q2_original_keys),key))'
 decode='(Q2_trial_mode&&qwen_app_route_is_decode()?std::binary_search(std::begin(Q2_decode_keys),std::end(Q2_decode_keys),key):std::binary_search(std::begin(Q2_original_keys),std::end(Q2_original_keys),key))'
 if a.combination:decode='(Q2_trial_mode&&!qwen_app_route_is_decode())||'+decode
 owner=once(owner,expr,'('+decode+')');ret='            return 1024+Q2_current_physical[std::size_t(current-std::begin(Q2_current_keys))];'
 owner=once(owner,ret,'            {if(Q2_trial_mode&&qwen_app_route_is_decode()&&!std::binary_search(std::begin(Q2_original_keys),std::end(Q2_original_keys),key))++post_refit_lookups;return 1024+Q2_current_physical[std::size_t(current-std::begin(Q2_current_keys))];}')
 owner='#include <cstdint>\nextern "C" bool qwen_app_route_is_decode();\nnamespace {std::uint64_t post_refit_lookups=0;}\n'+owner+'\nextern "C" std::uint64_t qwen_post_refit_key_lookups(){return post_refit_lookups;}\n'
 deps=owner_path.with_suffix('.d').read_text().splitlines()[1:];readers=[Path(x.strip().removesuffix('\\').strip())for x in deps if Path(x.strip().removesuffix('\\').strip()).name=='speed-resident-source.private.h'];require(len(readers)==1,'One actual source reader dependency required')
 original_reader=readers[0];reader=a.out/original_reader.name;body=original_reader.read_text();require(body.count('identity[5]>(512ull<<20)')==2,'Both original source bounds required');reader.write_text(body.replace('identity[5]>(512ull<<20)','(identity[5]>(512ull<<20)&&identity[5]!='+str(row['bytes'])+'ull)'),newline='\n')
 extras=[]
 if a.combination:
  stream=ring();stream=once(stream,'extern "C" bool qwen_post_ring_enabled();','extern "C" bool qwen_post_ring_enabled();\nextern "C" void qwen_post_ring_event(unsigned);')
  stream=once(stream,'queue(idle);break;','const auto prior_next=next;queue(idle);if(next>prior_next)qwen_post_ring_event(0);break;')
  stream=once(stream,'s.request.target=ring[lane];','s.request.target=ring[lane];if(lane==4)qwen_post_ring_event(1);')
  stream=once(stream,'const std::array<void*,5>ring=', 'qwen_post_ring_event(capacity==5?2:3);\n        const std::array<void*,5>ring=')
  sh=a.out/'streaming_read_pool.h';sh.write_text(stream,newline='\n');extras+=[sh,ROOT/'tools/ring_stream_source.py']
  owner+='\nnamespace {std::uint64_t post_ring_events[4]{};}\nextern "C" bool qwen_post_ring_enabled(){return Q2_trial_mode;}\nextern "C" void qwen_post_ring_event(unsigned i){if(i<4)++post_ring_events[i];}\nextern "C" void qwen_post_ring_stats(std::uint64_t*out){std::copy_n(post_ring_events,4,out);}\n'
  entry='#include <cstdint>\nextern "C" void qwen_post_ring_stats(std::uint64_t*);\n'+entry
  entry=once(entry,'            const auto refit_before=', '            std::uint64_t ring_before[4]{};qwen_post_ring_stats(ring_before);\n            const auto refit_before=')
  entry=once(entry,'            row["phase"]=phase;','            std::uint64_t ring_after[4]{};qwen_post_ring_stats(ring_after);for(unsigned i=0;i<4;++i)ring_after[i]-=ring_before[i];row["ring_early_queue_spare_read_and_mode_runs"]=std::vector<std::uint64_t>(ring_after,ring_after+4);\n            row["phase"]=phase;')
 gpu=gpu_source(Path(gc[gc.index('-c')+1]).read_text(),40,16,16)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,reporting(entry)),owner=(oc,owner),gpu=(gc,gpu)),[Path(__file__),a.pack,header,reader,original_reader,*extras])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['post_top2_refit']=dict(scope=scope,actual_sources=sources,commands=jobs,screen=record(a.out/'screen.private.json'),native_pack=record(a.pack))
 seed=a.out/'linked-seed.private.json';write_json(seed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='causal_decode_refit_existing_native_pack',candidate=record(a.out/'receipt.private.json'),new_weight_files=0,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
