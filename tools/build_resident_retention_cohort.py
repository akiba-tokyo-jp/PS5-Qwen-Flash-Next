#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare four cold controls, four cache-carry tasks and four cold controls."""
import json
import sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from finite_route_capacity import bind_route_capacity
from expert_q4 import require, write_json, record

ORIGINAL_LINK = quality.link


def bounded_link(parent, out, variants, inputs):
    cmd, text = variants['entry']
    # Generate the existing eight-request quality implementation, then bind all
    # evidence storage and scope declarations to the actual twelve requests.
    text = once(text, 'const unsigned request_count=8;', 'const unsigned request_count=12;')
    text = text.replace('\\"maximum_requests\\":8', '\\"maximum_requests\\":12')
    text = bind_route_capacity(text, 12)
    text = ('extern "C" void qwen_app_select_output_Q8_slots(unsigned);\n'
            'extern "C" void qwen_app_select_weight_retention(bool);\n') + text
    # A complete-vocabulary SHA256 per row retains exact cold-control evidence
    # without four simultaneous 33-row float arrays on the bounded CPU heap.
    # Preserve the existing token-ID type by deriving it from reference_ids.
    text = once(text, 'std::vector<float> reference_logits(resident_reference_rows*columns);',
        'std::array<std::vector<std::string>,4> reference_hashes;')
    at = text.index('        constexpr unsigned request_count=12;')
    text = text[:at] + ('        std::array<decltype(reference_ids),4> saved_ids;\n'
                       '        std::array<decltype(reference_bytes),4> saved_bytes;\n'
                       '        std::array<std::size_t,4> saved_rows{};\n') + text[at:]
    text = once(text,
        'const bool second=false;const bool repeat=ordinal%2;const unsigned task=ordinal/2;if(!repeat)reference_rows=0;',
        'const bool second=false;const bool repeat=ordinal>=8;const unsigned task=ordinal%4;'
        'const unsigned retention_phase=ordinal/4;const bool keep_weights=retention_phase==1&&task>0;'
        'reference_rows=repeat?saved_rows[task]:0;')
    text = once(text, '                resident_reset_empty_context(context,model,startup.admission_report);',
        '                qwen_app_select_weight_retention(keep_weights);\n'
        '                qwen_app_select_output_Q8_slots(retention_phase==1?3072:1381);\n'
        '                resident_reset_empty_context(context,model,startup.admission_report);')
    begin = text.index('            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{')
    end = text.index('            qwen_app::CausalExpertSharingEngine causal', begin)
    text = text[:begin] + '''            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))value_error=true;
                try{
                    const auto hash=qwen_app::sha256_metadata_bytes(std::string(reinterpret_cast<const char*>(v),count*sizeof(float)));
                    if(retention_phase==0)reference_hashes[task].push_back(hash);
                    else if(repeat&&(rows>=reference_hashes[task].size()||reference_hashes[task][rows]!=hash))value_error=true;
                }catch(...){geometry_error=true;}
                ++rows;if(retention_phase==0)++reference_rows;
            });
''' + text[end:]
    text = once(text, 'if(!repeat){reference_ids=result.token_ids;reference_bytes=result.output_bytes;}',
        'if(retention_phase==0){saved_ids[task]=result.token_ids;saved_bytes[task]=result.output_bytes;saved_rows[task]=rows;}')
    text = once(text, 'else if(repeat&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))',
        'else if(repeat&&(result.token_ids!=saved_ids[task]||result.output_bytes!=saved_bytes[task]))')
    text = once(text, 'const auto&a=routes.at(ordinal-1),&b=routes.at(ordinal);',
                      'const auto&a=routes.at(ordinal-8),&b=routes.at(ordinal);')
    require(text.count('{"cache_initially_empty",!second}') == 2,
            'Both intent and result must declare actual cache state')
    text = text.replace('{"cache_initially_empty",!second}', '{"cache_initially_empty",!keep_weights}')
    text = once(text, 'row["quality_task"]=task;',
        'row["retention_phase"]=retention_phase;row["weights_retained"]=keep_weights;'
        'row["active_cache_slots"]=retention_phase==1?3072:1381;'
        'row["logit_comparison"]=repeat?"exact_SHA256_each_full_F32_row":"finite_full_F32_rows";'
        'row["quality_task"]=task;')
    text = once(text, 'row["same_tokens_as_independent"]=result.token_ids==reference_ids&&result.output_bytes==reference_bytes;',
        'row["same_tokens_as_independent"]=result.token_ids==saved_ids[task]&&result.output_bytes==saved_bytes[task];')
    text = text.replace('Same-policy independent full F32 and ordered routes',
                        'Complete finite rows; final cold control exact full-row SHA256 and ordered routes')
    # Rebind the unchecked accesses introduced after finite_route_capacity.
    for expr in ('ordinal-8', 'ordinal'):
        text = text.replace('routes['+expr+']', 'routes.at('+expr+')')
    require('routes[' not in text, 'Every actual route index must remain checked')
    variants['entry'] = cmd, text
    return ORIGINAL_LINK(parent, out, variants, [*inputs, Path(__file__)])


def main():
    require('--only-task' not in sys.argv, 'All four tasks required')
    quality.link = bounded_link
    # The original builder performs the expensive relink once. The resulting
    # receipt scopes are adjusted to the identical twelve-request source here.
    quality.main()
    out = Path(sys.argv[sys.argv.index('--out')+1])
    path = out/'receipt.private.json'
    result = json.loads(path.read_text())
    def scopes(value):
        if isinstance(value, dict):
            if value.get('headless_fixed_quality') and value.get('maximum_requests')==8:
                value['maximum_requests']=12
            for child in value.values(): scopes(child)
        elif isinstance(value, list):
            for child in value: scopes(child)
    scopes(result)
    q = result['memory_quality_cohort']
    q.update(requests=12, independent_pairs=4)
    for key in ('cold_request', 'resident_all_Q8', 'resident_cache3072'):
        result[key]['actual_sources'].update(q['actual_sources'])
        result[key]['commands'].update(q['commands'])
    result['resident_retention_cohort']=dict(requests=12,fixed_tasks=4,
        phases=['cold1381','cold3072_then_different_input_retained3072','cold1381'],
        complete_control_F32_SHA256_required=True, candidate_full_F32_finite_required=True,
        cross_cache_route_equality_required=False, prefix_or_KV_reuse=False,
        raw_format_failures_recorded_without_aborting=True,
        source=record(Path(__file__)),native_verification_pending=True)
    write_json(path,result)


if __name__=='__main__': main()
