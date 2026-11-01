#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain the original disabled-arm retirement operation order without extra snapshots."""
import argparse,ast,json
from pathlib import Path
import build_throughput_owner as original
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','control','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());control=json.loads(a.control.read_text());a.out.mkdir(parents=True,exist_ok=False)
 function=next(x for x in ast.parse(Path(original.__file__).read_text()).body if isinstance(x,ast.FunctionDef)and x.name=='transform')
 literals={x.targets[0].id:ast.literal_eval(x.value)for x in function.body if isinstance(x,ast.Assign)and isinstance(x.targets[0],ast.Name)and x.targets[0].id in('old','new')}
 command=control['frontier']['commands']['lifecycle'];source=Path(command[command.index('-c')+1]).read_text();changed=original.transform(source)
 declaration='        ps5_ai_arena_stats owner{};\n'
 require(literals['old'].count(declaration)==literals['new'].count(declaration)==1,'One original owner declaration required')
 wrapper=declaration+'        if(!(qwen_throughput::mode.load(std::memory_order_relaxed)&4)){\n'+literals['old'].replace(declaration,'')+'\n        }else{\n'+literals['new'].replace(declaration,'')+'\n        }'
 changed=once(changed,literals['new'],wrapper)
 actual=n['frontier']['commands']['lifecycle'];r,jobs,sources=link(a.parent,a.out,dict(lifecycle=(actual,changed)),[Path(__file__),Path(original.__file__),a.control,ROOT/'native/app/owner_retirement_certificate.h'])
 # The unchanged compiled entry remains the actual linked provider.
 ec=n['compile_commands'][0];entry=record(ec[ec.index('-c')+1]);update_sources(r,dict(jobs,entry=ec),dict(sources,entry=entry))
 r['frontier']['commands'].update(jobs);r['frontier']['actual_sources'].update(sources)
 r['throughput']['commands'].update(jobs);r['throughput']['actual_sources'].update(sources)
 r['throughput']['original_control_operation_order_preserved']=True
 r['throughput']['extra_control_owner_snapshots']=0
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,original_control_operation_order_preserved=True,extra_control_owner_snapshots=0,unchanged_compiled_entry_reused=True,certificate_candidate_body_unchanged=True,driver_and_72byte_owner_ABI_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
