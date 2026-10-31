#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep recurrent clearing on supported GPU operations with F16 S storage."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import command_for,update_sources,ROOT
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 gc=command_for(n,'graph.private.cpp');graph=Path(gc[gc.index('-c')+1]).read_text()
 graph=once(graph,'    ggml_build_forward_expand(gf, ggml_scale_inplace(ctx0, state_zero, 0));',
  '    // F16 SCALE is unsupported by both linked Vulkan and CPU providers.\n'
  '    ggml_build_forward_expand(gf, state_zero->type==GGML_TYPE_F16 ?\n'
  '        ggml_fill_inplace(ctx0,state_zero,0.0f) : ggml_scale_inplace(ctx0,state_zero,0));')
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope']
 scope=dict(old,supported_F16_zero_fill=True,recurrent_compute_get_rows_type='F32',failed_SCOPE_preserved=21900)
 entry=once(entry,literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),graph=(gc,graph)),[Path(__file__)])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='F16_recurrent_supported_zero_clear',candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
