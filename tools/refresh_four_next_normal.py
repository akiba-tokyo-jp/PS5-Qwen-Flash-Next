#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the corrected final consumer, retaining original loading checks."""
import argparse,copy,json,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_four_next_normal import reconcile_compact_guard
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('base','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();base=json.loads(a.base.read_text());require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact source before relink')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for item in active_link_inputs(base):require(record(item['path'])==item,'Selected provider changed')
 a.out.mkdir(parents=True,exist_ok=False);old=base['four_next_normal']['scope'];require('loading_application_padding'not in old,'Original loading predicate provider required')
 scope=dict(old,loading_application_padding='original256',loading_expected_OS_minimum_pages=898,loading_expected_OS_reserved_pages=206,loading_legacy_padding_pages=256,loading_scope_once=True)
 command=base['four_next_normal']['commands']['entry'];entry=Path(base['four_next_normal']['actual_sources']['entry']['path']).read_text();require(entry.count(literal(old))==2,'Both exact scope sites required');entry=entry.replace(literal(old),literal(scope))
 entry=once(entry,'        qwen_native_stage("model_load_started_after_memory_admission");','        qwen_limit_probe_stage(1);\n        qwen_native_stage("model_load_started_after_memory_admission");')
 entry=once(entry,'        qwen_native_stage("model_load_completed");','        qwen_limit_probe_stage(2);\n        qwen_native_stage("model_load_completed");');entry=reconcile_compact_guard(entry)
 r,jobs,sources=link(a.base,a.out,dict(entry=(command,entry)),[Path(__file__),ROOT/'tools/build_four_next_normal.py'])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['compile_commands'][0]=jobs['entry']
 r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry'];r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision)
 r['four_next_normal']['actual_sources'].update(sources);r['four_next_normal']['commands'].update(jobs);r['four_next_normal'].update(scope=scope,source_revision=revision,normal_qualification_pending=True,production_adopted=False,only_consumer_counter_reconciliation_and_loading_phase_observation_changed=True)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='native_compact_counter_reconciliation',candidate=record(a.out/'receipt.private.json'),source_revision=revision,scope=scope,original_loading_padding_pages=256,unchanged_GPU_cache_engine_and_budget_providers=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
