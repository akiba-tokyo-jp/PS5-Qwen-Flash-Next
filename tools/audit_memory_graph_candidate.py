#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit explicit width-plan or shared-cache application transformations."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
from audit_expert_all_q2_safety import body
from build_width_graph_plans import context_source

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text())
 kind=next((k for k in ('expanded_miss_placement','memory_quality_cohort','shared_cache1381','width_graph_plans')if k in new),None);require(kind is not None,'Explicit candidate profile required');profile=new[kind]
 before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(profile['actual_sources']['entry']['path']).read_text()
 checks=('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context')
 for name in checks:
  source=body(before,name)
  if kind=='shared_cache1381' and name=='resident_reset_empty_context':source=source.replace('reset.slots!=1253','reset.slots!=1381')
  require(source==body(after,name),'Original physical/identity/reset guard changed: '+name)
 require(old['linked_driver']==new['linked_driver'] and new['native_dispatch_audit']['passed'] and not new['real_module_import_audit']['missing'],'Driver/import mismatch')
 for key in ('graph','routing'):require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Unrelated GPU provider changed')
 if kind=='width_graph_plans':
  original=profile['original_context'];require(record(original['path'])==original,'Pinned context source changed')
  require(Path(profile['actual_sources']['context']['path']).read_text()==context_source(Path(original['path']).read_text()),'Only explicit synchronized CPU topology retention allowed')
  for key in ('owner','engine','cache'):require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Allocation/source owner changed')
 elif kind=='shared_cache1381':
  require(profile['active_slots']==1381 and profile['cache_budget_bytes']==2123243520 and profile['total_postload_quota_transferred']==601284608,'Exact expanded cache and checkpoint accounting required')
  require(profile['total_postload_quota_transferred']+(16<<20)<profile['total_actual_resident_saving_bytes']==817152000,'Resident savings coupling failed')
  require(profile['CPU_heap_bytes']==512<<20 and profile['workspace_reservation_bytes']==64<<20 and profile['original_Direct_reserve_bytes']==512<<20,'Physical/CPU/workspace reserves changed')
  for key in ('owner','engine'):require(Path(old['normal_performance']['actual_sources'][key]['path']).read_text()==Path(profile['actual_sources'][key]['path']).read_text(),'Existing owner or engine code changed')
 elif kind=='memory_quality_cohort':
  require(profile['requests']in(2,8) and profile['independent_pairs']==profile['requests']//2 and profile['HTTP_requests']==profile['VideoOut_starts']==0,'Exact bounded headless cohort required')
  for key in ('owner','engine','cache'):require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Existing memory/source provider changed')
 else:
  require(profile['additional_Experts']==84 and profile['previous_Experts_retained']==448 and profile['scope']['total_bundled_Experts']==532,'Exact placement superset required')
  require(Path(old['normal_performance']['actual_sources']['owner']['path']).read_text()==Path(profile['actual_sources']['owner']['path']).read_text(),'Existing read/owner code changed')
  for key in ('engine','cache'):require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Existing engine/cache provider changed')
 write_json(a.out,dict(completed=True,kind=kind,unchanged_guard_functions=list(checks),driver_and_original_physical_reserves_preserved=True,candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
 print('Explicit candidate transformation and original physical/identity/completion guards passed.')
if __name__=='__main__':main()
