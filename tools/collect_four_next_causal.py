#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read a completed causal comparison using the frozen ordinary collector."""
import argparse,ast,importlib.util,inspect,json
from pathlib import Path
from expert_q4 import record,require
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--kind',choices=['rollback','two-token'],required=True);a=p.parse_args()
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';spec=importlib.util.spec_from_file_location('four_next_causal_collector',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 source=inspect.getsource(m.collect);old="r['speculation']['attempts']==0";require(source.count(old)==1,'One ordinary-only inherited predicate required');source=source.replace(old,"r['speculation']['attempts']>0")
 if a.kind=='rollback':
  old="else r['GDN_candidate_pipeline_selections']>0";require(source.count(old)==1,'One inherited unrelated GDN coverage predicate required')
  source=source.replace(old,"else (r['compact_rollback']['enabled'] and r['compact_rollback']['n_rs_seq']==1 and r['compact_rollback']['complete_captures_elided']>0)")
 ast.parse(source);exec(compile(source,str(Path(__file__).resolve())+'::causal_collector','exec'),m.__dict__)
 with m.base.writer_lease(m.C/'model-data-continuation.writer.lock'):
  m.frozen();m.base.current();tool=record(__file__);adaptation=m.CASE/('causal-collector-adaptation-'+tool['sha256'][:12]+'.private.json')
  if not adaptation.exists():m.base.save(adaptation,dict(schema='ps5-qwen-causal-collector-adaptation-v1',completed=True,tool=tool,frozen_ordinary_collector=record(path),ordinary_zero_attempt_predicate_replaced_with_positive_actual_attempts=True,rollback_uses_its_own_coverage_counters=a.kind=='rollback',unchanged_launch_policy_native_evidence_and_other_checks=True,PS5_launches=0,GPU_calls=0))
  m.collect();result=json.loads((m.CASE/'native-model-terminal.private.json').read_text());require(result['completed']and len(result['requests'])==14,'Complete14-request causal result required')
  rows=result['requests'];require(all(r['speculation']['attempts']>0 and r['speculation']['accepted']+r['speculation']['rejected']==r['speculation']['attempts']for r in rows),'Every causal decision must complete')
  require(all(r['speculation']['rejected']>0 for r in rows[10:]),'All four quality tasks must actually exercise rejection')
  if a.kind=='rollback':
   require(all(r['compact_rollback']['n_rs_seq']==1 for r in rows),'One native recurrent snapshot required')
   require(rows[-1]['compact_rollback']['all_memory_rollbacks']==sum(r['speculation']['rejected']for r in rows if r['candidate_arm']==1),'Every candidate rejection must rewind all memory modules')
   require(rows[-1]['compact_rollback']['complete_captures_elided']==sum(r['speculation']['attempts']for r in rows if r['candidate_arm']==1),'Each candidate attempt must elide a complete state capture')
   require(all(not any(r['complete_model_checkpoint']['counter_delta'])for r in rows if r['candidate_arm']==1),'Candidate must perform zero explicit checkpoint copies')
  else:
   require(all((r['two_token_pipeline_selections']>0 if r['candidate_arm']==1 else r['two_token_pipeline_selections']==0)for r in rows),'Actual two-token selected-path coverage required')
 print(json.dumps(dict(completed=True,case=a.case,kind=a.kind,actual_causal_requests=14,forced_rejection_tasks=4,native_reexecution=0)))
if __name__=='__main__':main()
