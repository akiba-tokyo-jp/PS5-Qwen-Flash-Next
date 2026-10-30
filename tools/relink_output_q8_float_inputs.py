#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the Q8 entry with explicit floating-input backend selection."""
import argparse,json
from pathlib import Path
from build_output_q8_screen import SCOPE,force_float_inputs
from build_speculative_batch_probe import once
from scoped_native_variant import link,seal
from expert_q4 import record,require
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());old=prior['output_Q8_screen'];require(old['scope']['maximum_requests']==11,'Exact unconsumed Q8 screen required')
    cmd=prior['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
    text=once(text,json.dumps(json.dumps(old['scope'],separators=(',',':'))),json.dumps(json.dumps(SCOPE,separators=(',',':'))))
    text=force_float_inputs(text);a.out.mkdir(parents=True,exist_ok=False)
    result,commands,sources=link(a.parent,a.out,{'entry':(cmd,text)},[Path(__file__),ROOT/'tools/build_output_q8_screen.py'])
    result['routing_sharing']['scope']=SCOPE;result['all_Q2_bundle_comparison']=dict(scope=SCOPE)
    result['output_Q8_screen']['scope']=SCOPE;result['output_Q8_screen']['actual_sources']['entry']=sources['entry']
    result['output_Q8_screen']['commands']['entry']=commands['entry'];result['output_Q8_screen']['float_input_relink']=record(Path(__file__))
    seal(result,a.workspace,a.cache,a.out);print('Q8 entry relinked; integer activation quantization disabled before device initialization.')
if __name__=='__main__':main()
