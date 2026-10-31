#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price the existing four program-file slots using the actual prepared SELFs."""
import json,sys
from pathlib import Path
from expert_q4 import require,record,write_json

def main():
    i=sys.argv.index('--program-price');price_path=Path(sys.argv[i+1]);del sys.argv[i:i+2]
    captured=record(price_path);price=json.loads(price_path.read_text())
    require(price['schema']=='ps5-qwen-actual-program-transfer-price-v1'and price['program_slots']==4 and price['journal_block_bytes']==65536,'Explicit existing four-slot program price required')
    programs=price['prepared_programs'];require(len(programs)>=4,'Original and all prepared program records required')
    for r in programs:require(record(r['path'])==r,'Prepared program changed')
    reserve=4*max(r['bytes']for r in programs)+65536
    require(price['program_transfer_reserve_bytes']==reserve and 0<reserve<256<<20,'Actual program price must replace the generic64MiB-per-slot assumption')
    path=Path(__file__).with_name('build_precision_publication.py');source=path.read_text()
    old="prep['selected_tensors']in(48,96,108)";require(source.count(old)==1,'Exact109-tensor publisher derivation required')
    source=source.replace(old,"prep['selected_tensors']==109")
    marker="    actual=a.out/'publication.private.cpp';actual.write_text(source,newline='\\n')"
    replacement="    source=once(source,'(256ull<<20)',"+repr(str(reserve)+'ull')+")\n"+marker
    instruction='    once('+repr(marker)+','+repr(replacement)+')\n'
    marker="    namespace={'__file__':__file__,'__name__':'__main__'}";require(source.count(marker)==1,'Exact publisher execution boundary required')
    source=source.replace(marker,instruction+marker)
    exec(compile(source,str(path)+'#actual-four-program-price','exec'),dict(__file__=__file__,__name__='__main__'))
    out=Path(sys.argv[sys.argv.index('--out')+1]);target=out/'manifest.private.json';r=json.loads(target.read_text())
    require(record(price_path)==captured,'Program price changed during build')
    r['inputs'] +=[captured,record(path),*programs]
    r['program_storage_price']=dict(plan=captured,program_slots=4,actual_maximum_SELF_bytes=max(x['bytes']for x in programs),
        journal_block_bytes=65536,program_transfer_reserve_bytes=reserve,
        prior_generic_reserve_bytes=256<<20,hardware_minimum_claimed=False,original_sources_retained=True)
    write_json(target,r)

if __name__=='__main__':main()
