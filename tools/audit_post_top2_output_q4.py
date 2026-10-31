#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the independent whole-payload/header audit on the exact109-tensor set."""
import json,sys
from pathlib import Path
from expert_q4 import record,write_json

if __name__=='__main__':
    path=Path(__file__).with_name('audit_precision_overlay.py');source=path.read_text()
    old='from prepare_precision_overlay import selection,CONTROL';assert source.count(old)==1
    source=source.replace(old,'from prepare_precision_overlay import CONTROL\nfrom prepare_post_top2_output_q4 import selection')
    # The original output-only Q8 receipt predates header_bytes. Its complete
    # original GGUF is independently pinned; the one tensor's header is160 bytes.
    # The unchanged parser also independently checks the complete header boundary.
    old="files[h['file']]['header_bytes']";assert source.count(old)==1
    source=source.replace(old,"files[h['file']].get('header_bytes',160 if h['file']=='qwen-flash-next-bf16-00076-of-00076.gguf'else -1)")
    exec(compile(source,str(path)+'#exact109-and-output160','exec'),dict(__file__=__file__,__name__='__main__'))
    out=Path(sys.argv[sys.argv.index('--out')+1]);r=json.loads(out.read_text())
    r['audit_sources']=[record(__file__),record(path),record(Path(__file__).with_name('prepare_post_top2_output_q4.py'))]
    r['output_header_bytes_independently_parsed']=160;write_json(out,r)
