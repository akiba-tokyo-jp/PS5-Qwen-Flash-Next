#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare676/768 placement keys on one fully sealed common348-triplet file."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();r=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired']and len(pack['bundles'])==348,'Native sealed348 pack required');require(record(pack['selection']['path'])==pack['selection'],'Exact selection required');selection=json.loads(Path(pack['selection']['path']).read_text())['Experts'];a.out.mkdir(parents=True,exist_ok=False)
 row=pack['output'];path='/app0/'+row['path'].split('/PPSA99190/',1)[1];pairs=sorted((x['layer'],x['expert'],i)for i,x in enumerate(selection));old=sorted((x['layer'],x['expert'])for x in selection[:256]);header=a.out/'limit-winner-bundle.private.h'
 header.write_text('#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr const char*Q2_current_path='+json.dumps(path)+';\ninline constexpr const char*Q2_current_SHA256='+json.dumps(row['sha256'])+';\ninline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\ninline constexpr std::array<unsigned,2>Q2_current_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e,i in pairs)+'};\ninline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\ninline constexpr std::array<unsigned,2>Q2_original_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e in old)+'};\ninline bool Q2_current_mode=false,Q2_trial_mode=false;\n',newline='\n')
 oldscope=r['GDN_model_comparison']['scope'];scope=dict(oldscope,schema='ps5-qwen-next-placement-model-v1',candidate='676_to768_sealed_placement',control_coverage_keys=676,candidate_coverage_keys=768,common_file_triplets=348,common_file_layout_reordered=True,full_F32_bytes_and_routes_required_for_both_arms=True,unchanged_single_token_fusion_enabled_in_both_arms=True)
 ec=r['compile_commands'][0];oc=r['all_Q2_optimized_monitor']['commands'][1];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(oldscope),literal(scope));entry=once(entry,'qwen_app_conv_norm_trial_select(arm==1);','qwen_app_conv_norm_trial_select(true);');entry=once(entry,'qwen_app_io_trial_select(true);','qwen_app_io_trial_select(arm==1);')
 entry=entry.replace('if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))').replace('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 owner=Path(oc[oc.index('-c')+1]).read_text();out,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc,owner)),[Path(__file__),a.pack,header])
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  out[key]['actual_sources'].update(sources);out[key]['commands'].update(jobs)
 out['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];out['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];out['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];out['all_Q2_optimized_monitor']['commands'][1]=jobs['owner'];out['routing_winners_normal']['actual_entry']=sources['entry']
 out['GDN_model_comparison']['scope']=scope;out['GDN_model_comparison']['actual_sources'].update(sources);out['GDN_model_comparison']['commands'].update(jobs)
 out['four_next_placement']=dict(scope=scope,pack=record(a.pack),header=record(header),actual_sources=sources,commands=jobs,model_comparison_pending=True)
 seal(out,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),kind='676_to768_common_file_placement',original_precision_driver_memory_and_completion=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
