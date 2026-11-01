#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read back every closed candidate token ledger against actual native output."""
import argparse,importlib.util,json,sys
from pathlib import Path
from expert_q4 import require,write_json,record
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();case=a.cache/f'hardware-first-generation-{a.case}';load=lambda p:json.loads(Path(p).read_text())
 report=load(case/'native-model-terminal.private.json');require(report['completed']and report['all_model_source_device_owners_positively_retired']and load(case/'restored-complete.private.json')['completed'],'Only positively retired, ordinarily closed/restored producers may be read')
 s=importlib.util.spec_from_file_location('op',ROOT/'.local/first_operator_038.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o);o.R=Path(o.load(o.ACTIVE)['context']).parent;o.current();o.no_native();remote=load(case/'prepared-launch.private.json')['management_admission_report'];evidence=[]
 for row in report['requests']:
  if not row.get('service_mode',0)&1:continue
  ordinal=row['ordinal'];raw=o.lan.web('/fs'+remote+'.arm'+str(ordinal)+'.token-ledger',128<<10,8);path=case/f'token-ledger-{ordinal}.private.jsonl';path.write_bytes(raw);require(raw.endswith(b'\n'),'Complete record delimiter required');records=[json.loads(line)for line in raw.splitlines()]
  require(len(records)==row['token_ledger_records']==row['metrics']['generated_tokens']and len(raw)==row['token_ledger_bytes'],'Every persisted token and actual byte count must agree')
  require([r['token_id']for r in records]==row['token_ids']and[b for r in records for b in r['piece_bytes']]==row['output_bytes'],'Actual ledger IDs and output bytes must equal the full native result')
  require([r['generated_tokens']for r in records]==list(range(1,len(records)+1))and all(records[i]['elapsed_ms']<=records[i+1]['elapsed_ms']for i in range(len(records)-1)),'Ordered complete token records required');evidence.append(record(path))
 require(evidence,'Actual candidate ledgers required');result=dict(completed=True,case=a.case,ledgers=len(evidence),all_records_ids_bytes_order_exact=True,positive_close_before_read=True,evidence=evidence,title_launches=0,GPU_calls=0);write_json(case/'token-ledger-readback-complete.private.json',result);print(json.dumps({k:v for k,v in result.items()if k!='evidence'}))
if __name__=='__main__':main()
