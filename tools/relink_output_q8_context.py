#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the Q8 engine's context admission to its exact enlarged cache budget."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());cmd=prior['routing_sharing']['commands'][2];path=Path(cmd[cmd.index('-c')+1]);text=path.read_text()
 old='(prefill_tokens > 1 && expert_cache_bytes != selected_padded_cache_geometry().cache_bytes())'
 replacement='(prefill_tokens > 1 && expert_cache_bytes != resident_output_Q8_cache_budget)'
 require(text.count(old)==1,'The original exact cache admission must remain present')
 text='#include "resident_output_q8_profile.h"\n'+once(text,old,replacement)
 a.out.mkdir(parents=True,exist_ok=False)
 result,commands,sources=link(a.parent,a.out,{'engine':(cmd,text)},[Path(__file__),ROOT/'native/app/resident_output_q8_profile.h'])
 result['output_Q8_screen']['actual_sources']['engine']=sources['engine'];result['output_Q8_screen']['commands']['engine']=commands['engine']
 result['output_Q8_screen']['context_budget_binding']=dict(previous_exact_bytes=1333739520,selected_exact_bytes=1533419520,
  only_exact_budget_operand_changed=True,context_and_F32_KV_fields_unchanged=True,actual_engine_source=record(path))
 seal(result,a.workspace,a.cache,a.out);print('Q8 engine bound to exactly1533419520 cache bytes; original context/F32 KV guards retained.')

if __name__=='__main__':main()
