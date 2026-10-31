#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Repair the failed reference indexing; reuse the identical compiled GPU object."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    old=Path(n['post_top2_gate_up']['complete_fixtures'][0]['path']);body=old.read_text()
    require(body.count('slot*240+row')==2,'Exactly two failed F64 reference offsets required')
    body=body.replace('slot*240+row','slot*640+row')
    body='#include <cstdio>\n'+body
    needle='need(std::isfinite(actual[i])&&error<=1e-5+2e-4*std::abs(reference[i]),"Fused Gate/Up differs from complete F64 reference");'
    code='''if(!(std::isfinite(actual[i])&&error<=1e-5+2e-4*std::abs(reference[i]))){char diagnostic[256];
                std::snprintf(diagnostic,sizeof(diagnostic),"Gate_Up_numerical_failure scenario=%u tokens=%u duplicate=%u arm=%u index=%zu actual=%.9g reference=%.17g error=%.9g",scenario,tokens,unsigned(duplicate),arm,i,double(actual[i]),reference[i],error);stage(diagnostic);
                throw std::runtime_error("Fused Gate/Up differs from complete F64 reference");}'''
    body=once(body,needle,code)
    header=a.out/'top2_fixture_reference.private.h';header.write_text(body,newline='\n')
    scope=dict(n['GDN_conv_normalization_fixture']['scope'],schema='ps5-qwen-top2-gate-up-fixture-v2',reference_Expert_row_stride=640,
               failed30500_preserved=True,GPU_kernel_and_buffer_geometry_unchanged=True)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();ec=ec+['-I',str(old.parent)]
    entry=once(entry,json.dumps(old.resolve().as_posix()),json.dumps(header.resolve().as_posix()))
    entry=once(entry,literal(n['GDN_conv_normalization_fixture']['scope']),literal(scope))
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),old,header])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
        if key in r:r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
    r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    r['routing_winners_normal']['actual_entry']=sources['entry']
    r['GDN_conv_normalization_fixture']['scope']=scope
    r['post_top2_gate_up']['scope']=scope;r['post_top2_gate_up']['complete_fixtures'][0]=record(header)
    r['reference_repair']=dict(failed_native_case=30500,prior_reference=record(old),corrected_reference=record(header),
        unchanged_GPU_object=n['lossless_shader_storage']['vulkan_object'],compiled_GPU_again=False)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='selected_parent_top2_gate_up_fixture_reference_repair',
        scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
