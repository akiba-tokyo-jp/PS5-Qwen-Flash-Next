#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the explicit output exception to the unmodified all-Q2 parent bytes."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('preparation','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prepared=json.loads(a.preparation.read_text());require(prepared['completed']and prepared['host_model_inference']is False,'Completed data-only Q8 preparation required')
 parent=prepared['parent'];require(record(parent['path'])==parent and parent['sha256']=='efd101c3661e6eb81f17306c43fc41b361f94aa58495f2025401659228163191','Exact closed parent required')
 original=prepared['candidate_receipt'];require(record(original['path'])==original,'Unpublished candidate changed');candidate=json.loads(Path(original['path']).read_text());candidate['parent_all_Q2_receipt_ref']={k:parent[k]for k in ('bytes','sha256')}
 a.out.mkdir(parents=True,exist_ok=False);target=a.out/'model-receipt.json';target.write_text(json.dumps(candidate,separators=(',',':'))+'\n',encoding='utf-8',newline='\n');require(target.stat().st_size<=1<<20,'Candidate metadata exceeds the unchanged bounded reader')
 write_json(a.out/'receipt.private.json',dict(completed=True,preparation=record(a.preparation),parent=parent,candidate=record(target),parts=prepared['parts'],generator=record(__file__),production_adopted=False,PS5_operations=0))
 print(json.dumps(dict(output_Q8_explicit_parent_bound=True,receipt_bytes=target.stat().st_size,PS5_operations=0)))
if __name__=='__main__':main()
