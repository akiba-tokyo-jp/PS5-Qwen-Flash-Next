#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate fresh fixed-input model comparison scripts with exact current guards."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cache-slots',type=int,choices=[3072,3424],default=3424)
 p.add_argument('--case',type=int,required=True);p.add_argument('--kind',choices=['checkpoint','gdn'],required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);a=p.parse_args()
 if a.case<15000 or a.case%100:raise ValueError('Fresh hundred-aligned model namespace required')
 requests=16 if a.kind=='checkpoint' else 14
 policy_key='native_checkpoint_model_comparison'if a.kind=='checkpoint'else'native_GDN_model_comparison'
 receipt_key='checkpoint_model_comparison'if a.kind=='checkpoint'else'GDN_model_comparison'
 def shift(s):return re.sub(r'(?<![0-9])130\d{2}(?![0-9])',lambda m:str(int(m[0])-13000+a.case),s)
 names=['prepared_phase_model_13000.private.py','resident_cohort_operator_13000.py','first_operator_13000_base.py','close_resident_cohort_13004.py','restore_resident_cohort_13005.py','build_resident_owner_13003.py','collect_Q2_monitor_13000.py']
 for name in names:
  text=shift((ROOT/'.local'/name).read_text());dest=ROOT/'.local'/shift(name)
  text=text.replace('Limit-candidates-SELF-12968',a.package_name).replace('Limit-candidates-12964/core-safety.private.json',a.build_name+'/core-safety.private.json')
  if name.startswith('prepared_'):
   needle="policy['native_limit_margin_probe']=actual_native['limit_margin_probe']['scope']"
   text=text.replace(needle,needle+f";policy['{policy_key}']=actual_native['{receipt_key}']['scope']")
   text=text.replace('maximum_generation_requests=16','maximum_generation_requests='+str(requests)).replace('active_cache_slots=3072,non_Expert','active_cache_slots='+str(a.cache_slots)+',non_Expert')
   start=text.index("scope='544 additional");end=text.index("',\n",start)
   description=('One model load and16 counting requests at fixed3424 cache slots; two uninjected warmup references followed by7 exact complete capture/restores per request after sampled tokens; original versus pooled/batched A-B-B-A and pooled-only versus combined A-B-A; complete F32 bytes, ordered Expert routes, tokens and output exact; metrics include injected state work and are not ordinary production speed'
     if a.kind=='checkpoint'else'One model load and14 requests at fixed3424 cache slots; two warmup references and ordinary original/fused A-B-B-A cold-retained pairs; four semantic tasks with combined checkpoint roundtrips only in the untimed quality phase; complete finite F32 distributions and actual ordered routes recorded; original model bytes, physical/OS minimum, driver and every positive completion retained')
   description=description.replace('fixed3424','fixed'+str(a.cache_slots));text=text[:start]+'scope='+repr(description)+text[end+1:]
  elif name.startswith('resident_cohort_operator_'):
   text=text.replace('maximum_generation_requests=16','maximum_generation_requests='+str(requests)).replace("len(report['requests'])==16","len(report['requests'])=="+str(requests)).replace('for ordinal in range(16):','for ordinal in range('+str(requests)+'):')
   old="(r['maximum_absolute_logit_error']==0 if r['candidate_arm']!=2 else r['GDN_candidate_pipeline_selections']>0)"
   replacement="r['maximum_absolute_logit_error']==0 and r['complete_model_checkpoint']['exact_full_F32_bytes'] and r['complete_model_checkpoint']['ordered_routes_exact']"if a.kind=='checkpoint'else"(r['maximum_absolute_logit_error']==0 if r['candidate_arm']==0 else r['GDN_candidate_pipeline_selections']>0)"
   if old not in text:raise ValueError('Exact original numerical gate required')
   text=text.replace(old,'('+replacement+')')
   if a.kind=='checkpoint':
    anchor="        selected=base.load(base.load(C/"
    pos=text.index(anchor)
    extra="        assert all(len(r['complete_model_checkpoint']['samples'])==(7 if r['ordinal']>=2 else 0)for r in report['requests'])\n        assert all((r['complete_model_checkpoint']['counter_delta'][0]>0 or r['complete_model_checkpoint']['counter_delta'][1]>0)for r in report['requests']if r['candidate_arm']in(1,2))\n        assert all(r['complete_model_checkpoint']['counter_delta'][2]>0 for r in report['requests']if r['candidate_arm']==2)\n"
    text=text[:pos]+extra+text[pos:]
   if a.kind=='gdn':
    text=text.replace("reset['occupied_before'] if ordinal%2 else 0","reset['occupied_before'] if ordinal<10 and ordinal%2 else 0").replace("reset['weights_retained']==bool(ordinal%2)","reset['weights_retained']==bool(ordinal<10 and ordinal%2)")
   text=text.replace("reset['slots']==3072","reset['slots']=="+str(a.cache_slots))
  elif name.startswith('first_operator_'):
   text=text.replace('lan.web("/fs" + row["remote"], 1 << 20, 8)','lan.web("/fs" + row["remote"], 8 << 20, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["old"]','lan.web("/fs" + row["target"], row["old"]["bytes"]+1, 8)).hexdigest() == row["old"]')
   text=text.replace('lan.web("/fs" + row["backup"], 1 << 20, 8)','lan.web("/fs" + row["backup"], row["old"]["bytes"]+1, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["new"]','lan.web("/fs" + row["target"], row["new"]["bytes"]+1, 8)).hexdigest() == row["new"]')
  elif name.startswith('restore_'):text=text.replace("op.lan.web('/fs'+path,1<<20,12)","op.lan.web('/fs'+path,capture['bytes']+1,12)")
  ast.parse(text)
  if dest.exists():raise FileExistsError(dest)
  if re.search(r'(?<![0-9])130\d{2}(?![0-9])',text):raise ValueError('Stale operation namespace')
  dest.write_text(text,newline='\n')
 print('Fresh finite actual-model scripts generated; no console operation.')
if __name__=='__main__':main()
