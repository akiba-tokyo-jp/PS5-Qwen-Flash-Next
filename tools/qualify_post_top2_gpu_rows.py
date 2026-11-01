#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit both target-verification rows to backend sampling before context creation."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text()
 engine=once(engine,'    params.n_seq_max = 1;params.n_rs_seq=1;','    params.n_seq_max = 1;params.n_rs_seq=1;params.n_outputs_max_per_seq=2;')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,backend_sampling_per_sequence_output_capacity=2,prior_default_backend_sampling_capacity=1,complete_width_two_outputs_explicitly_admitted=True,prefill_CPU_sampling_unchanged=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope));r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine)),[Path(__file__)])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_GPU_width_two_admission']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),width_two_full_F32_finite_reference_and_GPU_checks_preserved=True,CPU_GPU_OS_memory_limits_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
