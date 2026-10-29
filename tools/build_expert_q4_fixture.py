#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the existing unloaded fixture with actual Expert Q4_0 comparisons."""
import argparse
import json
from pathlib import Path
import sys
from expert_q4 import record,require
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-expert-q4-fixture-v1',model_loads=0,component_not_model_speed=True,
    widths=[1,2,4],formats=['BF16','Q4_0'],original_matrices=27,selected_experts=10,
    cases=27,maximum_GPU_graphs=400,CPU_deadline_seconds=240,reference='F64_of_each_format',
    quantized_activations=False,non_expert_quantization=False,
    BF16_control_F32_indexed_vector=True,automatic_retries=0)


def provider_source(text):
    marker='static bool ggml_vk_should_use_mmvq(const vk_device& device, uint32_t m, uint32_t n, uint32_t k, ggml_type src0_type) {'
    require(text.count(marker)==1,'The pinned input-quantization dispatch entry changed')
    text=text.replace(marker,marker+'''
    // The Expert-only Q4 experiment retains the original F32 activations.
    if(src0_type==GGML_TYPE_Q4_0)return false;
''',1)
    marker='    if (qwen_app_bf16_indexed_vector_enabled() && (qwen_app::bf16_indexed_vector_layout(dst) || qwen_app_padded_index_layout(dst))) return true;'
    require(text.count(marker)==1,'The exact BF16 indexed dispatch guard changed')
    # The unloaded fixture has ten contiguous slots. Production's existing
    # guard selects the same shader for its larger padded banks. Keep F32 B
    # in both comparison arms instead of the generic BF16 matrix B conversion.
    guard='''    if(src0->type==GGML_TYPE_BF16 && src0->ne[2]==10 && src0->ne[3]==1 &&
       ((src0->ne[0]==2560&&src0->ne[1]==640)||(src0->ne[0]==640&&src0->ne[1]==2560)) &&
       src0->nb[0]==2 && src0->nb[1]==std::uint64_t(src0->ne[0])*2 &&
       src0->nb[2]==3276800 && dst->src[1]->type==GGML_TYPE_F32 &&
       dst->src[1]->ne[0]==src0->ne[0] && (dst->src[1]->ne[1]==1||dst->src[1]->ne[1]==10) &&
       ids->type==GGML_TYPE_I32 && ids->ne[0]==10 &&
       (ids->ne[1]==1||ids->ne[1]==2||ids->ne[1]==4))return true;
'''
    return text.replace(marker,guard+marker,1)


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--samples',type=Path,required=True)
    own,rest=parser.parse_known_args();sys.argv=[sys.argv[0],*rest]
    output=Path(rest[rest.index('--out')+1]);header=output/'expert_q4_fixture_assets.h'
    samples=json.loads(own.samples.read_text())
    require(samples['completed']and samples['format']=='Q4_0'and len(samples['matrices'])==27,'Complete original Expert sample pack required')
    require(record(samples['pack']['path'])==samples['pack'],'Q4 sample pack changed')
    template=ROOT/'tools/build_portable_kernel_fixture.py'
    text=template.read_text().replace('portable_kernel','expert_q4').replace('portable-kernel','expert-q4').replace('portable kernel','Expert Q4')
    namespace={'__file__':str(Path(__file__)),'__name__':'expert_q4_fixture_builder_reference'}
    exec(compile(text,str(template)+'#isolated-expert-only-Q4','exec'),namespace)
    namespace['SCOPE']=SCOPE;namespace['workgroup_source']=provider_source
    original_entry=namespace['entry_source']
    def entry_source(source):
        h='// Generated private actual-weight asset manifest; never commit.\n#pragma once\n#include <cstdint>\n'
        h+='inline constexpr const char*q4_fixture_pack_path="/app0/qwen-runtime/expert-q4-samples-7501.bin";\n'
        h+='inline constexpr std::uint64_t q4_fixture_pack_bytes='+str(samples['pack']['bytes'])+'ULL;\n'
        h+='inline constexpr const char*q4_fixture_pack_sha256='+json.dumps(samples['pack']['sha256'])+';\n'
        h+='struct Q4FixtureMatrix{std::uint64_t bf16_offset,q4_offset;unsigned columns,rows;const char*bf16_sha256,*q4_sha256;};\n'
        h+='inline constexpr Q4FixtureMatrix q4_fixture_matrices[]={\n'
        for row in samples['matrices']:
            h+='{'+str(row['bf16_offset'])+'ULL,'+str(row['q4_offset'])+'ULL,'+str(row['columns'])+','+str(row['rows'])+','+json.dumps(row['original']['sha256'])+','+json.dumps(row['q4_payload_sha256'])+'},\n'
        h+='};\ninline constexpr unsigned q4_fixture_groups[9][3]={\n'
        for layer in (0,23,47):
            for role in ('gate','up','down'):
                indices=[next(i for i,r in enumerate(samples['matrices'])if(r['layer'],r['role'],r['expert'])==(layer,role,expert))for expert in (0,257,511)]
                h+='{'+','.join(map(str,indices))+'},\n'
        h+='};\n';header.write_text(h,newline='\n')
        result=original_entry(source)
        # The result protocol belongs to this component comparison; do not reuse
        # the unrelated nine-candidate portable-kernel result label.
        result=result.replace('".expert-q4s"','".expert-q4"').replace('expert_q4s_completed_model_not_loaded_waiting_for_ordinary_close','expert_q4_completed_model_not_loaded_waiting_for_ordinary_close')
        return result
    namespace['entry_source']=entry_source
    namespace['main']()
    path=output/'receipt.private.json';receipt=json.loads(path.read_text())
    receipt['inputs_before']+=[record(header),record(own.samples),record(template),record(ROOT/'tools/expert_q4.py')]
    receipt['expert_q4_fixture'].update(samples=record(own.samples),private_asset_header=record(header),
        sample_pack=samples['pack'],preserve_F32_activation_input=True,quantization_is_lossy=True,
        full_model_quality_qualified=False,production_adoption=False)
    path.write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
