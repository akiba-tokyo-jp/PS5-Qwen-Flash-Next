#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect already completed variable-capacity evidence without native replay."""
import argparse,importlib.util,inspect,json
from pathlib import Path
from expert_q4 import require,record
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args();path=ROOT/f'.local/resident_cohort_operator_{a.case}.py';spec=importlib.util.spec_from_file_location('next_capacity_collector',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 scope=m.base.load(m.CASE/'private-policy/development.json')['native_next_five'];require(scope['active_cache_slots']==[3072,3712] and scope['physical_cache_planes']==3713,'Exact priced3712 scope required')
 terminal=m.base.load(m.CASE/'native-model-terminal.private.json');require(terminal['completed']and len(terminal['requests'])==14,'Already completed native terminal required')
 for i,row in enumerate(terminal['requests']):require(row['active_cache_slots']==(3712 if i>=10 or 4<=i<=7 else 3072),'Actual request geometry differs from declared schedule')
 text=inspect.getsource(m.collect);old="reset['slots']==3072";require(text.count(old)==1,'One stale collector geometry predicate required');text=text.replace(old,"reset['slots']==report['requests'][ordinal]['active_cache_slots']");exec(compile(text,__file__+'#actual-geometry','exec'),m.__dict__)
 original_save=m.base.save
 def save_exact(path,value):
  path=Path(path)
  if path.name in ('quality-content-and-format.private.json','candidate-contents-decision.private.json')and path.exists():require(m.base.load(path)==value,'Previously completed quality evidence differs');return
  original_save(path,value)
 m.base.save=save_exact
 with m.base.writer_lease(m.C/'model-data-continuation.writer.lock'):
  m.frozen();m.base.current();tool=record(__file__);m.base.save(m.CASE/('capacity-collector-adaptation-'+tool['sha256'][:12]+'.private.json'),dict(completed=True,actual_geometry_validated_against_scope=True,frozen_collector=record(path),tool=tool,native_launches=0,GPU_calls=0));m.collect()
 print('Completed3712 evidence collected; original resource and close gates preserved; no native replay.')
if __name__=='__main__':main()
