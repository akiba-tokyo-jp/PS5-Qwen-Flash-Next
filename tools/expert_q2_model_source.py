#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive a separate Q2 model comparison from the qualified retained-context app."""
import json
from build_speculative_batch_probe import once

SCOPE=dict(schema='ps5-qwen-expert-q2-model-comparison-v1',enabled=True,model_loads=1,maximum_requests=3,warmup_requests=1,
    timed_requests=2,context_tokens=256,prefill_tokens=4,maximum_output_tokens=32,Expert_format='Gate_Up_Q2_K_Down_Q4_0',
    Expert_tensors_retained=147,Experts_per_layer=512,selected_Experts=10,non_Expert_precision_preserved=True,
    Expert_input_type='F32',KV_type='F32',activation_quantization=False,CPU_matrix_fallback=False,
    cache_budget_bytes=1333739520,expected_active_Q2_slots=581,compressed_GPU_cache=True,
    full_same_Q2_F32_rows_and_routes_required=True,BF16_logit_equality_required=False,
    counting_quality_required_before_adoption=True,HTTP_requests=0,VideoOut_starts=0,
    original_source_mutations=0,production_permission_changes=0,persistent_caches_enabled=False,automatic_retries=0)

def cache_source(text):
    text='#include "expert_q2_cache_reset.h"\n'+text
    text=once(text,'groups[0].n_slots!=int(qwen_app::selected_padded_cache_geometry().active_slots)',
        'groups[0].n_slots!=(groups[0].ref[0]->type==GGML_TYPE_Q2_K?581:int(qwen_app::selected_padded_cache_geometry().active_slots))')
    text=once(text,'while (g.n_slots < max_slots && alloc_size(g, g.n_slots + 1) <= budget)',
        'while (g.n_slots < max_slots && g.n_slots < 581 && alloc_size(g, g.n_slots + 1) <= budget)')
    return once(text,'qwen_app::reset_resident_cache_metadata(g.slru,unsigned(g.layers.size()))',
        '(g.ref[0]->type==GGML_TYPE_Q2_K?qwen_app::reset_expert_q2_cache_metadata(g.slru,unsigned(g.layers.size())):'
        'qwen_app::reset_resident_cache_metadata(g.slru,unsigned(g.layers.size())))')

def entry_source(text):
    text='#include "expert_q2_source_integrity.h"\n'+text
    text=once(text,'        isolated_large_cache_layout(startup,policy,native_resources_started);\n'
        '        throw std::runtime_error("The isolated 134-slot fixture cannot enter model initialization");',
        '        qwen_native_stage("Q2_full_model_integrity_and_source_admission_next_GPU_not_started");')
    text=once(text,'using Json = nlohmann::json;',
        'using Json = nlohmann::json;\nstatic std::optional<Json> Expert_Q2_receipt;\nstatic std::optional<qwen_app::ExpertQ2Receipt> Expert_Q2_manifest;\nstatic std::string Expert_Q2_root;')
    marker='static std::string model_file(const std::string & receipt, const std::string & name) {'
    text=once(text,marker,marker+'\n    if(Expert_Q2_receipt)return qwen_app::expert_q2_logical_path(*Expert_Q2_receipt,Expert_Q2_root,name);')
    text=once(text,'        qwen_app::require_large_cache_layout_phase_scope(policy,startup.first_generation_validation,false,1);',
        '        if(policy.at("native_Expert_Q2_model")!=Json::parse('+json.dumps(json.dumps(SCOPE,separators=(',',':')))+'))\n'
        '            throw std::runtime_error("Exact separate Expert Q2 model comparison scope required");\n'
        '        for(const char*key:{"native_cache_layout_phase_memory","native_large_cache_scope","native_padded_bank_layout_probe","native_padded_expert_cache",\n'
        '            "native_predictive_cache","native_model_free_speculation","native_prefix_validation"})\n'
        '            if(policy.contains(key))throw std::runtime_error("BF16-only or unrelated experiment in the Q2 model scope");')
    text=once(text,'This unloaded fixture qualifies exactly 134 slots','The separately qualified 134-slot BF16 budget seed is required')
    # The displaced BF16 layout-policy parser also selected this budget seed.
    # Select it explicitly before retaining the original exact-value guard.
    text=once(text,'        if(qwen_app::additional_cache_slots()!=134)',
        '        qwen_app::request_additional_cache_slots(134);\n        if(qwen_app::additional_cache_slots()!=134)')
    text=once(text,'        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);',
        '''        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);
        Expert_Q2_manifest.emplace(receipt);Expert_Q2_receipt=receipt;
        Expert_Q2_root=startup.model_receipt.substr(0,startup.model_receipt.find_last_of('/'));
        if(!qwen_app::expert_q2_source_root(Expert_Q2_root))throw std::runtime_error("Isolated Q2 task data directory required");''')
    text=once(text,'const auto expected_mapped_files=qwen_app::validate_model_receipt(receipt);',
        'const auto expected_mapped_files=Expert_Q2_manifest->mapped_bytes;')
    text=once(text,'qwen_app::split_model_integrity(policy.at("native_first_generation_validation"),receipt,expected_mapped_files)',
        'std::optional<qwen_app::SplitModelIntegrity>(qwen_app::expert_q2_source_integrity(policy.at("native_first_generation_validation"),receipt,Expert_Q2_root,expected_mapped_files))')
    text=once(text,'        qwen_app::validate_original_footprint(footprint,expected_mapped_files);',
        '        qwen_app::validate_expert_q2_footprint(footprint,expected_mapped_files);')
    text=text.replace('model_directory+"/"+part.path','part.path').replace('file.path=model_directory+"/"+file.path','file.path=file.path')
    # All sources now live below the existing title nullfs. Preserve its exact
    # one-device translation and all nine other sealed inode identity fields.
    text=once(text,'const bool allow_translation = gate.value("allow_app0_model_device_translation", false);',
        'const bool allow_translation = gate.value("allow_app0_model_device_translation",false);\n'
        '                if(!allow_translation||!qwen_app::expert_q2_source_root(Expert_Q2_root))throw std::runtime_error("Q2 requires the existing exact title nullfs namespace");')
    text=once(text,'if (allow_translation && startup.model_receipt != "/app0/qwen-runtime/model/model-receipt.json")',
        'if (allow_translation && startup.model_receipt != Expert_Q2_root+"/model-receipt.json")')
    text=once(text,'if (type != GGML_TYPE_BF16 && type != GGML_TYPE_F32)',
        'if (type != GGML_TYPE_BF16 && type != GGML_TYPE_F32 && type != GGML_TYPE_Q2_K && type != GGML_TYPE_Q4_0)')
    text=once(text,'        footprint.tensor(name,bytes);',
        '''        if(!Expert_Q2_manifest)throw std::runtime_error("Complete Q2 tensor manifest required before inspection");
        Expert_Q2_manifest->tensor_ne(name,type==GGML_TYPE_Q2_K?"Q2_K":type==GGML_TYPE_Q4_0?"Q4_0":type==GGML_TYPE_BF16?"BF16":"F32",
            gguf_get_tensor_ne(metadata.get(),i),bytes);
        footprint.tensor(name,bytes);''')
    text=once(text,'        const bool large_cache_candidate=policy.contains("native_large_cache_scope");','        const bool large_cache_candidate=true;')
    begin=text.index('        if(large_cache_candidate) {\n            const bool layout=qwen_app::require_large_cache_scope')
    end=text.index('        const auto cache_geometry=',begin)
    text=text[:begin]+'''        qwen_app::select_experimental_padded_cache_128();
        qwen_native_stage("Q2_contiguous_cache_1333739520_byte_budget_selected_BF16_padded_paths_disabled");
'''+text[end:]
    text=once(text,'        model = llama_model_load_from_file(first_path.c_str(), model_params);',
        '''        std::vector<std::string> Expert_Q2_paths;
        for(const auto&file:receipt.at("files"))Expert_Q2_paths.push_back(model_file(startup.model_receipt,file.at("path").get<std::string>()));
        if(Expert_Q2_paths.size()!=76||Expert_Q2_paths.front()!=first_path)throw std::runtime_error("All ordered original logical splits are required");
        std::vector<const char*> Expert_Q2_cpaths;for(const auto&path:Expert_Q2_paths)Expert_Q2_cpaths.push_back(path.c_str());
        model = llama_model_load_from_splits(Expert_Q2_cpaths.data(),Expert_Q2_cpaths.size(),model_params);''')
    text=once(text,'reset.slots!=qwen_app::selected_padded_cache_geometry().active_slots','reset.slots!=581')
    text=once(text,'uploaded!=misses*9830400ull+result.predictive_bytes','uploaded!=misses*1996800ull+result.predictive_bytes')
    text=text.replace('{"cache_slots",qwen_app::selected_padded_cache_geometry().active_slots}','{"cache_slots",581}')
    text=once(text,'        constexpr std::size_t resident_reference_rows=23;','        constexpr std::size_t resident_reference_rows=33;')
    text=once(text,'            const bool refill=true;','            const bool refill=false;')
    text=once(text,'geometry_error||value_error||rows!=23||','geometry_error||value_error||!rows||')
    text=once(text,'            qwen_app::require_demo_sequence(result.output_bytes);',
        '''            bool counting_quality=true;
            try{qwen_app::require_demo_sequence(result.output_bytes);}catch(const std::exception&){counting_quality=false;}''')
    marker='            if(!routes[ordinal].complete)throw std::runtime_error("Complete actual additional routes required");'
    text=once(text,marker,marker+'''
            if(ordinal){const auto&a=routes[0],&b=routes[ordinal];
                if(a.rows.size()!=b.rows.size())throw std::runtime_error("Repeated Q2 route row count differs");
                for(std::size_t i=0;i<a.rows.size();++i)if(a.rows[i].layer!=b.rows[i].layer||a.rows[i].tokens!=b.rows[i].tokens||
                    !std::equal(a.rows[i].ids.begin(),a.rows[i].ids.begin()+10*a.rows[i].tokens,b.rows[i].ids.begin()))
                    throw std::runtime_error("Repeated Q2 original Expert selections differ");}''')
    # The quality disposition is recorded after successful synchronous work;
    # an incorrect answer does not turn known GPU completion into uncertainty.
    text=once(text,'            completed.push_back(row);write_fresh_report(report_prefix+".result",row);',
        '            row["counting_quality_passed"]=counting_quality;row["Expert_format"]="Gate_Up_Q2_K_Down_Q4_0";\n            completed.push_back(row);write_fresh_report(report_prefix+".result",row);')
    text=text.replace('"ps5-qwen-resident-additional-result-v1"','"ps5-qwen-expert-q2-model-result-v1"').replace('{"kind","additional-cache"}','{"kind","Expert-Q2"}')
    text=once(text,'{"requests",completed},{"model_loads",1},{"active_cache_slots",cache_geometry.active_slots}',
        '{"requests",completed},{"model_loads",1},{"active_cache_slots",581},{"Expert_format","Gate_Up_Q2_K_Down_Q4_0"},{"non_Expert_precision_preserved",true},{"KV_type","F32"},{"activation_quantization",false}')
    text=text.replace('"all_original_tokens_and_bytes_exact"','"all_repeated_Q2_tokens_and_bytes_exact"')
    text=text.replace('{"active_cache_slots",cache_geometry.active_slots}','{"active_cache_slots",581}')
    return text
