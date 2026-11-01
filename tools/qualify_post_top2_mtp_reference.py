#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep exact independent MTP repeats without equating different verification sequences."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,unlike_MTP_evaluation_sequences_not_bit_compared=True,complete_finite_target_and_MTP_rows_required=True,independent_matched_MTP_full_row_SHA256_and_routes_required=True,no_target_width_or_memory_quota_increase=False)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'        std::vector<float>io_current(resident_reference_rows*columns);','''        std::array<std::array<std::array<std::uint8_t,32>,resident_reference_rows>,2>mtp_hashes{};
        std::array<std::size_t,2>mtp_rows{};std::array<std::vector<llama_token>,2>mtp_ids;
        std::array<std::vector<unsigned char>,2>mtp_bytes;std::array<Json,2>mtp_routes;
        std::vector<float>io_current(resident_reference_rows*columns);''')
 before='std::copy_n(v,count,io_current.data()+rows*columns);auto&ref=io_reference[hash_arm];if(compare&&std::memcmp(v,ref.data()+rows*columns,count*sizeof(float)))bitwise_error=true;for(std::size_t i=0;i<count;++i){if(!compare)ref[rows*columns+i]=v[i];else io_max_error=std::max(io_max_error,std::abs(double(v[i])-ref[rows*columns+i]));}++rows;'
 after='''std::copy_n(v,count,io_current.data()+rows*columns);
                // Hash every complete target row in both arms. This adds no tensor
                // transfer or full reference plane. Compare only matched sequences.
                const auto digest=qwen_app::model_logit_fingerprint(v,count);
                if(arm==1){if(phase==2)mtp_hashes[hash_arm][rows]=digest;else if(phase==3&&digest!=mtp_hashes[hash_arm][rows])bitwise_error=true;}
                else{auto&ref=io_reference[hash_arm];if(compare&&std::memcmp(v,ref.data()+rows*columns,count*sizeof(float)))bitwise_error=true;for(std::size_t i=0;i<count;++i){if(!compare)ref[rows*columns+i]=v[i];else io_max_error=std::max(io_max_error,std::abs(double(v[i])-ref[rows*columns+i]));}}++rows;'''
 entry=once(entry,before,after)
 for before,after in [('(compare&&rows!=io_rows[hash_arm])','(compare&&arm==0&&rows!=io_rows[hash_arm])'),('if(compare&&(io_max_error!=0||bitwise_error))','if(compare&&arm==0&&(io_max_error!=0||bitwise_error))'),('if(!compare)io_rows[hash_arm]=rows;','if(!compare&&arm==0)io_rows[hash_arm]=rows;'),('if(!compare){speed_ids','if(!compare&&arm==0){speed_ids'),('else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])','else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))'),('if(compare&&!same_routes)','if(compare&&arm==0&&!same_routes)'),('row["actual_submission_node_cap"]=arm?256:16;','row["actual_submission_node_cap"]=256;')]:entry=once(entry,before,after)
 marker='            // Cache-aware ranking can select different routes after weight retention.'
 entry=once(entry,marker,'''            if(arm==1&&task==0){const auto records=completed_route_report(routes.at(ordinal)).at("records");
                if(phase==2){mtp_rows[hash_arm]=rows;mtp_ids[hash_arm]=result.token_ids;mtp_bytes[hash_arm]=result.output_bytes;mtp_routes[hash_arm]=records;}
                else if(phase==3&&(rows!=mtp_rows[hash_arm]||bitwise_error||result.token_ids!=mtp_ids[hash_arm]||result.output_bytes!=mtp_bytes[hash_arm]||records!=mtp_routes[hash_arm]))
                    throw std::runtime_error("Independent matched MTP full rows, tokens, bytes or routes differ");}
'''+marker)
 marker='            row["phase"]=phase;'
 entry=once(entry,marker,'''            row["F32_comparison_scope"]=arm?"Every target row finite; independent same-cache MTP SHA256/tokens/routes exact; unlike proposal sequences unaligned":"Independent unchanged history-only full vocabulary F32 exact";
            row["full_F32_logit_rows_compared"]=arm?(phase==3?rows:0):(compare?rows:0);
            row["MTP_independent_full_rows_and_routes_exact"]=arm&&phase==3;
            if(arm)row["maximum_absolute_logit_error"]=nullptr;
'''+marker)
 # The common row writer below sets the maximum again; keep unlike positions
 # explicitly unmeasured rather than manufacture a zero numerical difference.
 entry=once(entry,'row["maximum_absolute_logit_error"]=io_max_error;','row["maximum_absolute_logit_error"]=arm?Json(nullptr):Json(io_max_error);')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__)]);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_reference']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),no_extra_full_reference_plane=True,all_complete_target_rows_still_checked=True,unchanged_control_exact_and_independent_candidate_exact=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
