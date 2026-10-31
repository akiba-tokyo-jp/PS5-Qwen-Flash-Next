#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare fresh finite normal/API/display scripts; never contact the console."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);a=p.parse_args()
 if a.case<15600 or a.case%100:raise ValueError('Fresh hundred-aligned normal namespace required')
 def shift(text):return re.sub(r'(?<![0-9])131\d{2}(?![0-9])',lambda m:str(int(m[0])-13100+a.case),text)
 names=['prepared_phase_model_13100.private.py','resident_cohort_operator_13100.py','first_operator_13100_base.py','close_resident_cohort_13104.py','restore_resident_cohort_13105.py','build_resident_owner_13103.py','collect_Q2_monitor_13100.py']
 for name in names:
  text=shift((ROOT/'.local'/name).read_text());dest=ROOT/'.local'/shift(name)
  text=text.replace('Limit-winner-SELF-13064',a.package_name).replace('Limit-winner-13060',a.build_name)
  if name.startswith('prepared_'):
   marker="policy['native_limit_defaults']=actual_native['limit_defaults']['scope']"
   if text.count(marker)!=1:raise ValueError('One normal measured-default policy required')
   text=text.replace(marker,marker+";policy['native_strata_followup_normal']=actual_native['strata_followup_normal']['scope']")
   start=text.index("scope='544 additional");end=text.index("',\n",start)
   text=text[:start]+"scope='Normal three-request/API/display qualification with original decode-priority3072 retained slots,2MiB checkpoint allocation/metadata reuse, independent same-operation positive-completed GPU copy batches, and any separately measured GDN winner declared in the exact native scope; original model, BF16 PLE, driver, physical/OS minimum, workspace and unknown-owner retention unchanged; no injected checkpoint benchmark work'"+text[end+1:]
  elif name.startswith('resident_'):
   pass
  elif name.startswith('first_'):
   text=text.replace('lan.web("/fs" + row["remote"], 1 << 20, 8)','lan.web("/fs" + row["remote"], 8 << 20, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["old"]','lan.web("/fs" + row["target"], row["old"]["bytes"]+1, 8)).hexdigest() == row["old"]')
   text=text.replace('lan.web("/fs" + row["backup"], 1 << 20, 8)','lan.web("/fs" + row["backup"], row["old"]["bytes"]+1, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["new"]','lan.web("/fs" + row["target"], row["new"]["bytes"]+1, 8)).hexdigest() == row["new"]')
  elif name.startswith('restore_'):text=text.replace("op.lan.web('/fs'+path,1<<20,12)","op.lan.web('/fs'+path,capture['bytes']+1,12)")
  ast.parse(text)
  if dest.exists():raise FileExistsError(dest)
  if re.search(r'(?<![0-9])131\d{2}(?![0-9])',text):raise ValueError('Stale normal namespace')
  dest.write_text(text,newline='\n')
 print('Fresh finite normal/API/display scripts prepared; no console action.')
if __name__=='__main__':main()
