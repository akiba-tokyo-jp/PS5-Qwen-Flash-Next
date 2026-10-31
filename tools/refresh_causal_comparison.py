#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the comparison entry after restoring the original routing snapshot."""
import argparse,json
from pathlib import Path
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];source=Path(ec[ec.index('-c')+1]);r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,source.read_text())),[Path(__file__),ROOT/'native/app/causal_rollback_engine.h'])
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['GDN_model_comparison']['actual_sources']['entry']=sources['entry'];r['GDN_model_comparison']['commands']['entry']=jobs['entry']
 for key in ('four_next_rollback','four_next_two_model'):
  if key in r:r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry'];r[key]['original_cache_ranking_snapshot_before_each_verification_or_ordinary_token']=True
 seal(r,a.workspace,a.cache,a.out);s=json.loads((a.parent.parent/'core-safety.private.json').read_text());s.update(candidate=record(a.out/'receipt.private.json'),original_cache_ranking_snapshot_preserved=True,parent=record(a.parent));write_json(a.out/'core-safety.private.json',s)
if __name__=='__main__':main()
