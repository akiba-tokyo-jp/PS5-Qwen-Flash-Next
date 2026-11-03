#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a sealed IQ2 Up model with scoped FP32 accumulation and normal F16 storage."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from iq2_up_model_scope import require_arithmetic_qualification
from prepare_iq2_up_model_overlay import literal
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def compile_cache(a, run):
    proof = load(a.cache_baseline)
    need(proof['completed'] and proof['baseline_provider_qualified'] and proof['selected_object_byte_exact'] and
         not proof['section_differences'] and record(proof['artifact']['path']) == proof['artifact'] and
         record(proof['source']['path']) == proof['source'], 'The full byte-identical selected cache reconstruction is required')
    out = a.out / 'candidate-cache'
    out.mkdir()
    previous = Path(a.cache_baseline).parent
    for path in previous.glob('*.h'):
        shutil.copyfile(path, out / path.name)
    view = load(proof['selected_VFS_view']['path'])
    for row in view['roots']:
        local = out / Path(row['external-contents']).name
        if local.exists():
            row['external-contents'] = local.resolve().as_posix()
    overlay = out / 'selected-view.private.json'
    save(overlay, view)
    source = Path(proof['source']['path']).read_text()
    changed = once(source, '        const bool bundle_refill=qwen_app_Q2_bundle_enabled();',
        '''        const bool original_triplet=std::all_of(l.experts.begin(),l.experts.end(),[](const ggml_tensor*w){
            return w->type==GGML_TYPE_Q2_K||w->type==GGML_TYPE_Q2_0;});
        const bool bundle_refill=qwen_app_Q2_bundle_enabled()&&original_triplet;''')
    changed = once(changed, 'if(qwen_app_Q2_quad_enabled()&&!six_refill){',
                   'if(qwen_app_Q2_quad_enabled()&&!six_refill&&original_triplet){')
    # All unchanged layers retain their qualified bundle/stream fast paths.
    # IQ2 layers use the original generic format-aware pair/coalescing path.
    path, obj = out / 'cache.private.cpp', out / 'cache.o'
    path.write_text(changed, newline='\n')
    command = [str(out) if v == str(previous) else v for v in proof['command']]
    command[command.index('-ivfsoverlay')+1] = str(overlay)
    command[command.index('-c')+1], command[command.index('-o')+1] = str(path), str(obj)
    if '-MF' in command:
        command[command.index('-MF')+1] = str(out / 'cache.private.d')
    run(command, 'candidate-cache')
    return record(obj), record(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'preparation', 'publication', 'cache-baseline', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--F32-observer', type=Path)
    p.add_argument('--arithmetic-qualification', type=Path, required=True)
    a = p.parse_args()
    arithmetic_qualification = record(a.arithmetic_qualification)
    require_arithmetic_qualification(arithmetic_qualification)
    prep, pub = load(a.preparation), load(a.publication)
    need(prep['completed'] and pub['completed'] and pub['preparation'] == record(a.preparation) and
         pub['whole_new_bytes_and_all_parent_identities_qualified'], 'The exact new-only native IQ2 source publication is required')
    seal = load(pub['source_integrity']['path'])
    need(record(pub['source_integrity']['path']) == pub['source_integrity'] and
         seal['model_receipt_sha256'] == prep['candidate']['sha256'] and
         seal['selected_previous_model_sha256'] == prep['selected_model_sha256'], 'The two actual complete model identities must match')
    selected = load(a.current / 'provenance/selected-entry-build.private.json')
    original = load(selected['application_policy']['path'])
    need(record(original['source']['path']) == original['source'], 'The selected original entry changed')
    old_dir = Path(original['source']['path']).parent
    old_header = (old_dir / 'precision-plan.private.h').read_text()
    need(literal(old_header, 'precision_candidate_sha256') == prep['selected_model_sha256'] and
         literal(old_header, 'precision_parent_sha256') == prep['parent_model_sha256'], 'Exact selected metadata ancestry required')
    observer = load(a.F32_observer) if a.F32_observer else None
    if observer:
        need(observer['completed'] and observer['qualification_only'] and
             record(observer['artifact']['path']) == observer['artifact'], 'The existing complete F32 observer must be exact')
    a.out.mkdir(parents=True, exist_ok=False)
    commands = []
    def run(command, label):
        command = list(map(str, command))
        commands.append(command)
        result = subprocess.run(command, capture_output=True, timeout=240, env=dict(os.environ, TMP=str(a.out), TEMP=str(a.out)))
        (a.out / (label + '.private.log')).write_bytes(result.stdout + result.stderr)
        need(not result.returncode, (result.stdout + result.stderr).decode(errors='replace')[-5000:])
    cache, cache_source = compile_cache(a, run)
    baseline = Path(original['source']['path']).read_text()
    candidate_raw = Path(prep['candidate']['path']).read_text()
    need(record(prep['candidate']['path']) == prep['candidate'], 'The prepared complete candidate changed')
    candidate = json.loads(candidate_raw)
    packages = {}
    identity = load(a.current / 'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    for arm in ('control', 'candidate'):
        root = a.out / arm
        root.mkdir()
        for path in old_dir.glob('*.h'):
            shutil.copyfile(path, root / path.name)
        scope = dict(schema='ps5-qwen-IQ2-Up-model-v1', kind='Q2-IQ2-Up-model', arm=arm, requests=3, model_loads=1,
            HTTP_requests=0, VideoOut_starts=0, maximum_output_tokens_per_request=32,
            original_cold_retained_exact_prefix_sequence=True, IQ2_Up_layers=prep['IQ2_Up_layers'] if arm=='candidate' else [],
            original_BF16_direct_quantization=True, heldout_decode_calibration=False,
            backend_environment=dict(GGML_VK_DISABLE_MMVQ='1'), normal_F16_enabled=True,
            IQ2_only_FP32_accumulation=True, arithmetic_qualification=arithmetic_qualification,
            selected_cache_slots=3712, original_live_reserves_preserved=True, persistent_caches=False)
        text = baseline
        if arm == 'candidate':
            h = old_header
            for name, value in (('precision_candidate_raw', candidate_raw), ('precision_candidate_sha256', prep['candidate']['sha256'])):
                old = 'inline constexpr const char*' + name + '=' + json.dumps(literal(h, name)) + ';'
                h = once(h, old, 'inline constexpr const char*' + name + '=' + json.dumps(value) + ';')
            h, count = re.subn(r'(precision_expert_bytes=)\d+ull', r'\g<1>' + str(prep['footprint']['mapped_experts']) + 'ull', h)
            need(count == 1, 'One exact original expert-footprint constant required')
            start = h.index('inline bool precision_selected_type(')
            body_text = 'inline bool precision_selected_type(const std::string&name,int type){\n' + ''.join(
                'if(name==' + json.dumps(t['name']) + ')return type==' + str(16 if t['type']=='IQ2_XXS' else 2) + ';\n'
                for t in candidate['precision_overlay']['tensors']) + 'return false;}'
            # All original109 selected tensors are Q4_0; the new Up tensors are IQ2_XXS.
            need(all(t['type'] in ('Q4_0', 'IQ2_XXS') for t in candidate['precision_overlay']['tensors']), 'An unexpected selected format differs')
            # The generated function ends before the namespace's closing brace.
            close = h.index('return false;}', start) + len('return false;}')
            h = h[:start] + body_text + h[close:]
            (root / 'precision-plan.private.h').write_text(h, newline='\n')
            paths = [r['path'] for r in seal['parts'][:pub['retained_parts']]]
            resolver = 'inline std::string IQ2_precision_part_path(const std::string&root,std::size_t i){\n'
            resolver += ''.join('if(i==' + str(i) + ')return ' + json.dumps(path) + ';\n' for i, path in enumerate(paths))
            resolver += 'return root+"/precision.part"+std::to_string(i)+".bin";\n}\n'
            typed = root / 'precision_overlay_receipt.h'
            raw = typed.read_text()
            raw = once(raw, 'namespace qwen_app {', 'namespace qwen_app {\n' + resolver)
            raw = once(raw, 'const auto path=root+"/precision.part"+std::to_string(i)+".bin";',
                       'const auto path=IQ2_precision_part_path(root,i);')
            typed.write_text(raw, newline='\n')
            text = once(text, 'type==GGML_TYPE_Q4_0?"Q4_0":type==GGML_TYPE_Q8_0?',
                        'type==GGML_TYPE_IQ2_XXS?"IQ2_XXS":type==GGML_TYPE_Q4_0?"Q4_0":type==GGML_TYPE_Q8_0?')
        marker = '        const auto policy = Json::parse(policy_file);'
        text = once(text, marker, marker + '\n        if(policy.at("native_headless_model_audit")!=Json::parse(' +
            json.dumps(json.dumps(scope, separators=(',', ':'))) + '))throw std::runtime_error("Exact IQ2 Up model scope required");\n' +
            '        if(setenv("GGML_VK_DISABLE_MMVQ","1",1)||unsetenv("GGML_VK_DISABLE_F16")||getenv("GGML_VK_DISABLE_F16"))throw std::runtime_error("Qualified IQ2 backend profile unavailable");')
        text = once(text, '(ordinal==1&&rows!=reference_rows)', 'false')
        text = once(text, '            else if(ordinal==1&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))\n                throw std::runtime_error("Original additional tokens or bytes differ");',
                    '            // Precision quality differences are recorded before ordinary owner retirement.')
        text = headless_entry(text, scope['kind'], 3, 'Json{{"completed",true},{"IQ2_Up_scope",policy.at("native_headless_model_audit")},{"requests",completed}}')
        if arm == 'candidate':
            text += '\n' + (ROOT / 'native/app/iq2_up_precision.cpp').read_text()
        if not observer:
            text = once(text, '{"timings_usable_for_performance",false}', '{"timings_usable_for_performance",true}')
        for name in ('observed_system_headroom', 'require_model_CPU_budget', 'wait_for_initial_model_CPU_budget',
                     'model_file_identity', 'model_directory_identity', 'resident_reset_empty_context'):
            need(body(text, name) == body(baseline, name), 'An original memory/identity/reset guard changed: ' + name)
        source, entry = root / 'entry.private.cpp', root / 'entry.o'
        source.write_text(text, newline='\n')
        command = next(c.copy() for c in selected['commands'] if '-ivfsoverlay' in c)
        view = load(command[command.index('-ivfsoverlay')+1])
        for row in view['roots']:
            local = root / Path(row['external-contents']).name
            if local.exists():
                row['external-contents'] = local.resolve().as_posix()
        typed = (ROOT / 'native/app/precision_overlay_receipt.h').resolve().as_posix()
        view['roots'] = [row for row in view['roots'] if row['name'] != typed]
        view['roots'].append(dict(type='file', name=typed, **{'external-contents':(root / 'precision_overlay_receipt.h').resolve().as_posix()}))
        overlay = root / 'selected-view.private.json'
        save(overlay, view)
        command = [str(root) if v == str(old_dir) else v for v in command]
        command[1:1] = ['-I', str(root)]
        command[command.index('-ivfsoverlay')+1] = str(overlay)
        command[command.index('-c')+1], command[command.index('-o')+1] = str(source), str(entry)
        if '-MF' in command:
            command[command.index('-MF')+1] = str(root / 'entry.private.d')
        run(command, arm + '-entry')
        profile = copy.deepcopy(original)
        profile.update(kind='headless-model-audit', entry_artifact=record(entry), source=record(source), headless_model_audit=True,
            headless_audit_kind=scope['kind'], headless_requests=3, model_and_GPU_topology_unchanged=False,
            model_and_GPU_guards_preserved=True, overrides=dict(original['overrides'], native_headless_model_audit=scope),
            performance_timings_usable=not bool(observer), native_performance_qualified=False, production_adopted=False)
        if arm == 'candidate':
            profile['model_layer'] = dict(kind='IQ2-Up', parent_recipe_sha256=prep['selected_model_sha256'],
                model_receipt=prep['candidate'], application_model_receipt=seal['source_directory']+'/model-receipt.json',
                source_policy=pub['policy'], publication=record(a.publication))
        policy = root / 'application-policy.private.json'
        save(policy, profile)
        job = [sys.executable, '-B', ROOT/'tools/relink_retained_current.py', '--current', a.current, '--out', root/'link',
            '--replace', 'entry.o='+str(entry), '--replace', 'early-SELF.o='+original['CPU_SELF_provider']['artifact']['path'], '--application-policy', policy]
        if arm == 'candidate':
            job += ['--replace', 'cache.o='+cache['path']]
            job += ['--link-flag=--wrap=ggml_mul_mat_id']
        if observer:
            job += ['--add-object', observer['artifact']['path']] + ['--link-flag='+f for f in observer['link_flags']]
        run(job, arm+'-link')
        run([sys.executable, '-B', ROOT/'tools/package_retained_current.py', '--workspace', a.workspace, '--current', a.current,
             '--relink', root/'link/result.private.json', '--out', root/'SELF', '--formatter-from',
             a.current/'provenance/current-package.private.json', '--identity-provider', identity['path']], arm+'-SELF')
        packages[arm] = record(root/'SELF/result.private.json')
    save(a.out/'result.private.json', dict(completed=True, preparation=record(a.preparation), publication=record(a.publication),
        packages=packages, cache_baseline=record(a.cache_baseline), cache=cache, cache_source=cache_source,
        commands=commands, F32_qualification=bool(observer), original_memory_identity_reset_guards_unchanged=True,
        only_converted_layers_bypass_incompatible_old_bundle_and_quad_paths=True, driver_unchanged=True,
        explicit_global_F32_backend_profile=False, IQ2_only_FP32_accumulation=True,
        arithmetic_qualification=arithmetic_qualification,
        precision_wrapper_source=record(ROOT/'native/app/iq2_up_precision.cpp'),
        PS5_operations=0, native_quality_and_rate_qualified=False, production_adopted=False))
    print(json.dumps(dict(completed=True, model_packages=2, IQ2_Up_layers=prep['IQ2_Up_layers'], PS5_operations=0)))


if __name__ == '__main__':
    main()
