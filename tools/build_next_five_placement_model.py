#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare768/1444 placement keys in one native-sealed1024-triplet file."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired']and len(pack['bundles'])==1024,'Whole native1024-triplet seal required');require(record(pack['selection']['path'])==pack['selection'],'Exact causal trace selection required');selection=json.loads(Path(pack['selection']['path']).read_text())['Experts'];a.out.mkdir(parents=True,exist_ok=False)
 row=pack['output'];path='/app0/'+row['path'].split('/PPSA99190/',1)[1];pairs=sorted((x['layer'],x['expert'],i)for i,x in enumerate(selection));old=sorted((x['layer'],x['expert'])for x in selection[:348]);header=a.out/'limit-winner-bundle.private.h'
 header.write_text('#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr const char*Q2_current_path='+json.dumps(path)+';\ninline constexpr const char*Q2_current_SHA256='+json.dumps(row['sha256'])+';\ninline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\ninline constexpr std::array<unsigned,2>Q2_current_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e,i in pairs)+'};\ninline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\ninline constexpr std::array<unsigned,2>Q2_original_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e in old)+'};\ninline bool Q2_current_mode=false,Q2_trial_mode=false;\n',newline='\n')
 oldscope=n['GDN_model_comparison']['scope'];scope=dict(oldscope,candidate='768-to1444-placement',candidate_id=0,control_placement_keys=768,candidate_placement_keys=1444,common_file_triplets=1024,common_file_bytes=row['bytes'],original348_prefix_payload_positions_preserved=True,candidate_F32_and_token_equality_required=True,extra_Expert_cache_slots=0,extra_source_scratch_bytes=0)
 ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(oldscope),literal(scope));entry=once(entry,'qwen_next_select(arm?1:0);','qwen_next_select(0);');entry=once(entry,'qwen_app_io_trial_select(true);','qwen_app_io_trial_select(arm==1);')
 entry=once(entry,'arm==0?"installed-control":"routing4";','arm==0?"placement768":"placement1444";');entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 owner=Path(oc[oc.index('-c')+1]).read_text();r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc,owner)),[Path(__file__),a.pack,header]);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['next_five_placement']=dict(scope=scope,pack=record(a.pack),header=record(header),actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='native_sealed1024_triplet_placement',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
