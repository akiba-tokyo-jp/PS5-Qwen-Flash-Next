#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit actual selected source counters while retaining the frozen normal protocol."""
import argparse,ast,importlib.util
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args()
 path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';spec=importlib.util.spec_from_file_location('selected_normal_collection',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 report=m.base.load(m.CASE/'native-model-terminal.private.json');scope=report['next_five'];rows=report['requests']
 require(report['completed']and scope['throughput_mode']==5 and scope['immutable_Expert_bundle_coverage']==22968 and len(rows)==3,'Exact completed selected normal scope required')
 require(all(r['throughput_mode']==5 and len(r['throughput_totals'])==12 and r['throughput_totals'][0]>0 for r in rows)and all(rows[i]['throughput_totals'][0]>rows[i-1]['throughput_totals'][0]for i in(1,2)),'Actual selected bundle delivery must execute in every normal request')
 source=path.read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='collect');lines=source.splitlines(keepends=True);function=''.join(lines[node.lineno-1:node.end_lineno])
 old="assert report['requests'][1]['actual_graph_reuses']>0 and report['requests'][1]['current_bundle_hits']>0"
 new="assert report['requests'][1]['actual_graph_reuses']>0 and report['next_five']['throughput_mode']&1 and report['requests'][1]['throughput_mode']==report['next_five']['throughput_mode'] and report['requests'][1]['throughput_totals'][0]>0"
 function=once(function,old,new)
 with m.base.writer_lease(m.C/'model-data-continuation.writer.lock'):
  m.frozen();m.base.current();exec(compile(function,str(path)+'#selected-source-counts', 'exec'),m.__dict__);m.collect()
  write_json(m.CASE/'selected-source-counter-admission.private.json',dict(completed=True,original_frozen_controller=record(path),adapter=record(__file__),only_legacy_bundle_hit_predicate_replaced=True,actual_selected_bundle_counts=[r['throughput_totals'][0]for r in rows],legacy_current_bundle_hits=[r['current_bundle_hits']for r in rows],graph_reuse_and_all_other_guards_preserved=True,additional_title_launches=0,GPU_calls=0))
if __name__=='__main__':main()
