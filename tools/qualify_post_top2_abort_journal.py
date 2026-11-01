#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add durable library assertions without changing math or abort semantics."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];entry='#include "native_failure_journal.h"\n'+Path(ec[ec.index('-c')+1]).read_text()
 old=n['GDN_model_comparison']['scope'];scope=dict(old,durable_native_assertion_callback=True,default_library_abort_behavior_unchanged=True)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'        const auto policy = Json::parse(policy_file);','        qwen_app::install_native_assertion_journal();\n        const auto policy = Json::parse(policy_file);')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),ROOT/'native/app/native_failure_journal.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_assertion_journal']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),math_and_quotas_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
