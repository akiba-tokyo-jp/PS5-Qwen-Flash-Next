#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rank uncovered actual misses and preserve every existing supplemental key."""
import argparse,collections,json,re
from pathlib import Path
from expert_q4 import require,record,write_json

def keys(path,prefix):
 text=Path(path).read_text();match=re.search(prefix+r'_keys\[\]\s*=\s*\{(.*?)\};',text,re.S)
 require(match is not None,'Explicit sealed placement key table required')
 return [tuple(map(int,m))for m in re.findall(r'\{(\d+),(\d+)\}',match[1])]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('analysis','base','extra','current','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();r=json.loads(a.analysis.read_text());require(r['completed']and r['actual_1253_counts_reproduced'],'Actual policy reproduction required')
 rows=next(x for x in r['rows']if x['mode']=='qualified');old=keys(a.current,'Q2_current');existing=set(keys(a.base,'Q2_bundle')+keys(a.extra,'Q2_extra')+old)
 require(len(existing)==448 and len(old)==28,'Retain exact448 original keys')
 counts=collections.Counter()
 for misses in rows['misses_by_layer_Expert']:
  counts.update({tuple(map(int,k.split(':'))):v for k,v in misses.items()if tuple(map(int,k.split(':')))not in existing})
 new=sorted([k for k,_ in counts.most_common(84)]);selection=old+new
 require(len(selection)==112 and len(set(selection))==112,'Unique112 supplemental complete triplets required')
 coverage=[sum(v for k,v in misses.items()if tuple(map(int,k.split(':')))in set(new))for misses in rows['misses_by_layer_Expert']]
 a.out.mkdir(parents=True,exist_ok=False)
 write_json(a.out/'selection.private.json',dict(completed=True,no_Experts_omitted=True,bundles=112,Experts=[dict(layer=l,expert=e)for l,e in selection],new_keys=84,previous_keys_retained=28,routing_frozen_screen_only=True))
 write_json(a.out/'analysis.private.json',dict(completed=True,actual_1253_policy_counts_reproduced=True,existing_keys=448,new_keys=84,covered_new_misses=coverage,upper_role_call_reduction=[2*v for v in coverage],additional_bytes_per_covered_triplet=4096,hardware_speedup_established=False,inputs=[record(x)for x in (a.analysis,a.base,a.extra,a.current)]))
 print(json.dumps(dict(new_keys=84,covered_actual_misses=coverage,native_comparison_justified=any(coverage))))
if __name__=='__main__':main()
