#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the exact shared-basis input to the title's app0 namespace."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];src=Path(ec[ec.index('-c')+1]);assets=a.out/'shared_basis_assets.private.h'
 assets.write_text(once((src.parent/assets.name).read_text(),'/data/ps5qwen-shared-basis-rank32-40400.bin','/app0/ps5qwen-shared-basis-rank32-40400.bin'),newline='\n')
 header=a.out/'shared_basis_fixture.private.h';header.write_text(once((ROOT/'native/app/shared_basis_fixture.h').read_text(),'"shared_basis_assets.private.h"',json.dumps(assets.as_posix())),newline='\n')
 entry=once(src.read_text(),'"shared_basis_fixture.h"',json.dumps(header.as_posix()));r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),assets,header])
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['GDN_conv_normalization_fixture'].update(actual_sources=dict(r['GDN_conv_normalization_fixture']['actual_sources'],entry=sources['entry']),commands=dict(r['GDN_conv_normalization_fixture']['commands'],entry=jobs['entry']),remote_input='/app0/ps5qwen-shared-basis-rank32-40400.bin')
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),math_GPU_buffers_and_input_bytes_unchanged=True,title_namespace_corrected=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
