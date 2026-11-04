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
from iq2_up_model_scope import require_arithmetic_qualification, require_down_qualification, require_gate_input_qualification, require_cache_layout, require_MMVQ_qualification
from iq2_route_geometry import correct_accounting, triplet_bytes
from prepare_iq2_up_model_overlay import literal
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def cache_text(source,down_carriers):
    if down_carriers:
        changed=once(source,'        const bool bundle_refill=qwen_app_Q2_bundle_enabled();',
                     '        const bool bundle_refill=false;')
        changed=once(changed,'        const bool six_refill=qwen_app_six_bank_refill_enabled();',
                     '        const bool six_refill=false;')
        return changed.replace('if(qwen_app_Q2_quad_enabled()', 'if(false')
    changed=once(source,'        const bool bundle_refill=qwen_app_Q2_bundle_enabled();',
        '''        const bool original_triplet=std::all_of(l.experts.begin(),l.experts.end(),[](const ggml_tensor*w){
            return w->type==GGML_TYPE_Q2_K||w->type==GGML_TYPE_Q2_0;});
        const bool bundle_refill=qwen_app_Q2_bundle_enabled()&&original_triplet;''')
    return once(changed,'if(qwen_app_Q2_quad_enabled()&&!six_refill){',
                'if(qwen_app_Q2_quad_enabled()&&!six_refill&&original_triplet){')


def compile_cache(a, run, down_carriers=False):
    proof = load(a.cache_baseline)
    need(proof['completed'] and proof['baseline_provider_qualified'] and proof['selected_object_byte_exact'] and
         not proof['section_differences'] and record(proof['artifact']['path']) == proof['artifact'] and
         record(proof['source']['path']) == proof['source'], 'The full byte-identical selected cache reconstruction is required')
    changed=cache_text(Path(proof['source']['path']).read_text(),down_carriers)
    if getattr(a, 'format_stream_provider', None):
        from iq2_format_stream_cache import transform
        changed = transform(Path(proof['source']['path']).read_text(), down_carriers)
    if getattr(a, 'Down_prefix_cache', False):
        from iq2_down_prefix_cache import transform
        changed = transform(changed)
    if getattr(a,'cache_provider_proof',None):
        built=load(a.cache_provider_proof)
        need(built['completed'] and built['actual_selected_PS5_ABI_compiled'] and
             record(built['artifact']['path'])==built['artifact'] and record(built['source']['path'])==built['source'] and
             Path(built['source']['path']).read_text()==changed and
             built['commands'][0][0]==proof['command'][0] and
             built['commands'][0][built['commands'][0].index('-c')+1]==built['source']['path'] and
             built['commands'][0][built['commands'][0].index('-o')+1]==built['artifact']['path'],
             'The completed cache provider must match the exact selected source transformation and compiler')
        return built['artifact'],built['source']
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
    p.add_argument('--Down-resource-provider',type=Path)
    p.add_argument('--cache-provider-proof',type=Path,help='Reuse an already completed exact selected-ABI cache provider')
    p.add_argument('--completed-control-case',type=Path,help='Reuse the exact already completed normal control without rebuilding it')
    p.add_argument('--MMVQ-decode-qualification',type=Path,help='Enable normal MMVQ only after its twelve distinct native decode graphs pass')
    p.add_argument('--Down-prefix-cache',action='store_true',help='Reuse the compiled index-safe Down prefix provider with explicit physical/logical byte accounting')
    p.add_argument('--candidate-only',action='store_true',help='Build only a first-screen candidate; a new matched normal control remains required before adoption')
    p.add_argument('--format-stream-provider', type=Path, help='Reuse the exact compiled four-lease cache and original-owner wrapper')
    p.add_argument('--format-stream-IO-proof', type=Path, help='Require all69 native rows/routes/outputs before observer-free streaming timing')
    a = p.parse_args()
    need(not (a.candidate_only and a.completed_control_case), 'Choose a candidate-only screen or exact completed-control reuse')
    arithmetic_qualification = record(a.arithmetic_qualification)
    down_carriers=a.Down_resource_provider is not None
    MMVQ_proof = record(a.MMVQ_decode_qualification) if a.MMVQ_decode_qualification else None
    if MMVQ_proof:
        need(not down_carriers, 'The stock IQ2 MMVQ refinement does not qualify custom Down carriers')
        require_MMVQ_qualification(MMVQ_proof)
    Down_provider=record(a.Down_resource_provider) if down_carriers else None
    Down_F16=down_carriers and load(a.Down_resource_provider).get('F16_arithmetic_only') is True
    if a.Down_prefix_cache:
        need(down_carriers and Down_F16 and a.cache_provider_proof is not None,
             'A Down prefix model requires its exact compiled cache and F16 index-safe operator provider')
        from iq2_down_prefix_scope import require_compiled_prefix
        require_compiled_prefix(record(a.cache_provider_proof), Down_provider)
    if down_carriers:require_down_qualification(arithmetic_qualification,Down_provider)
    else:require_arithmetic_qualification(arithmetic_qualification)
    prep, pub = load(a.preparation), load(a.publication)
    Gate_layers=prep.get('IQ2_Gate_layers',[])
    need(down_carriers or prep['IQ2_Up_layers']==list(range(48)),
         'Reject a partial nonuniform Up cache before compilation or model packaging')
    if Gate_layers:
        need(not down_carriers and Gate_layers==prep['IQ2_Up_layers']==list(range(48)),
             'Only the complete uniform Gate/Up model may use this scope')
        require_gate_input_qualification(prep['Gate_input_identity'])
    stream = None
    if a.format_stream_provider:
        from iq2_format_stream_scope import require_compiled_stream
        need(not a.Down_prefix_cache and a.cache_provider_proof == a.format_stream_provider and
             (a.F32_observer is not None or a.format_stream_IO_proof is not None),
             'Format streaming requires the exact cache, a distinct observed IO qualification or its positive native proof')
        stream = require_compiled_stream(record(a.format_stream_provider), 'Down' if down_carriers else ('Gate-Up' if Gate_layers else 'Up'))
    Down_format_proof=(load(load(a.Down_resource_provider)['F16_operands']['path'])['native_F32_proof']
                      if Down_F16 else arithmetic_qualification)
    need(not down_carriers or (prep['IQ2_Down_layers']==list(range(48)) and
         prep['native_operator_proof']==Down_format_proof),
         'All48 Down carriers must match their exact native arithmetic proof')
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
    cache, cache_source = compile_cache(a, run, down_carriers)
    baseline = Path(original['source']['path']).read_text()
    candidate_raw = Path(prep['candidate']['path']).read_text()
    need(record(prep['candidate']['path']) == prep['candidate'], 'The prepared complete candidate changed')
    candidate = json.loads(candidate_raw)
    candidate_triplet_bytes = triplet_bytes(candidate)
    packages = {}
    arms = ('candidate',) if a.candidate_only else ('control', 'candidate')
    if a.completed_control_case:
        from run_headless_decode_sequence import returned
        from success_case_control import current_files
        prior_plan = load(a.completed_control_case/'case/plan.private.json')
        prior_package = Path(prior_plan['package']['path'])
        returned(a.completed_control_case, prior_package)
        package = load(prior_package)
        policy_row = package['effective_application_policy']['profile']
        need(record(policy_row['path'])==policy_row, 'The completed control policy changed')
        policy = load(policy_row['path'])
        require_cache_layout(policy)
        control_scope = policy['overrides']['native_headless_model_audit']
        expected_kind = 'Q3-IQ2-Down-model' if down_carriers else ('Q2-IQ2-Gate-Up-model' if Gate_layers else 'Q2-IQ2-Up-model')
        need(policy['headless_audit_kind']==expected_kind and control_scope['arm']=='control' and
             control_scope['arithmetic_qualification']==arithmetic_qualification and
             control_scope['backend_environment']=={} and 'model_layer' not in policy and
             prior_plan['old_files']==current_files(a.current),
             'Only the same normal current control and arithmetic lineage may be reused')
        packages['control'] = record(prior_package)
        arms = ('candidate',)
    identity = load(a.current / 'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    for arm in arms:
        root = a.out / arm
        root.mkdir()
        for path in old_dir.glob('*.h'):
            shutil.copyfile(path, root / path.name)
        scope = dict(schema='ps5-qwen-IQ2-Up-model-v1', kind='Q2-IQ2-Up-model', arm=arm, requests=3, model_loads=1,
            HTTP_requests=0, VideoOut_starts=0, maximum_output_tokens_per_request=32,
            original_cold_retained_exact_prefix_sequence=True, IQ2_Up_layers=prep['IQ2_Up_layers'] if arm=='candidate' else [],
            original_BF16_direct_quantization=True, heldout_decode_calibration=False,
            backend_environment={} if arm=='control' else dict(GGML_VK_DISABLE_MMVQ='1'), normal_F16_enabled=True,
            IQ2_only_FP32_accumulation=True, arithmetic_qualification=arithmetic_qualification,
            selected_cache_slots=3712, original_live_reserves_preserved=True, persistent_caches=False)
        scope['actual_Expert_triplet_bytes'] = candidate_triplet_bytes if arm == 'candidate' else 1536000
        scope['completed_route_accounting_uses_uniform_tensor_bytes'] = True
        if MMVQ_proof and arm == 'candidate':
            scope.update(backend_environment={}, MMVQ_decode_qualification=MMVQ_proof)
        if down_carriers:
            scope.update(schema='ps5-qwen-IQ2-Down-model-v1',kind='Q3-IQ2-Down-model',IQ2_Up_layers=[],
                IQ2_Down_layers=prep['IQ2_Down_layers'] if arm=='candidate' else [],
                IQ2_only_FP32_accumulation=False,normal_F16_enabled=Down_F16 or arm=='control',
                backend_environment={} if arm=='control' else (
                    dict(GGML_VK_DISABLE_MMVQ='1') if Down_F16 else dict(GGML_VK_DISABLE_MMVQ='1',GGML_VK_DISABLE_F16='1')),
                global_F32_candidate_only=not Down_F16,Down_only_FP32_accumulation=Down_F16,Down_resource_provider=Down_provider)
            if a.Down_prefix_cache and arm == 'candidate':
                scope['Down_source_prefix_cache'] = record(a.cache_provider_proof)
        elif Gate_layers:
            scope.update(schema='ps5-qwen-IQ2-Gate-Up-model-v1',kind='Q2-IQ2-Gate-Up-model',
                IQ2_Gate_layers=Gate_layers if arm=='candidate' else [],Gate_input_identity=prep['Gate_input_identity'])
        if stream and arm == 'candidate':
            scope.update(format_stream_provider=record(a.format_stream_provider),
                format_stream_model_receipt=prep['candidate'], format_stream_observation_only=bool(a.F32_observer),
                format_stream_IO_qualification=record(a.format_stream_IO_proof) if a.format_stream_IO_proof else None)
        require_cache_layout(dict(headless_audit_kind=scope['kind'],overrides=dict(native_headless_model_audit=scope)))
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
            if down_carriers:
                body_text='inline bool precision_selected_type(const std::string&name,int type){\n'+''.join(
                    'if(name=='+json.dumps(t['name'])+')return type=='+str(42 if t['type']=='Q2_0' else 2)+';\n'
                    for t in candidate['precision_overlay']['tensors'])+'return false;}'
            # All original109 selected tensors are Q4_0; the new Up tensors are IQ2_XXS.
            need(all(t['type'] in (('Q4_0','Q2_0') if down_carriers else ('Q4_0','IQ2_XXS'))
                     for t in candidate['precision_overlay']['tensors']), 'An unexpected selected format differs')
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
        environment='        if(setenv("GGML_VK_DISABLE_MMVQ","1",1)||unsetenv("GGML_VK_DISABLE_F16")||getenv("GGML_VK_DISABLE_F16"))throw std::runtime_error("Qualified IQ2 backend profile unavailable");'
        if arm=='control' or MMVQ_proof:
            environment='        if(unsetenv("GGML_VK_DISABLE_MMVQ")||unsetenv("GGML_VK_DISABLE_F16"))throw std::runtime_error("Normal P1 backend profile unavailable");'
        elif down_carriers and not Down_F16:
            environment=('        if(unsetenv("GGML_VK_DISABLE_MMVQ")||unsetenv("GGML_VK_DISABLE_F16"))' if arm=='control' else
                         '        if(setenv("GGML_VK_DISABLE_MMVQ","1",1)||setenv("GGML_VK_DISABLE_F16","1",1))')
            environment+='throw std::runtime_error("Exact Down model backend profile unavailable");'
        text = once(text, marker, marker + '\n        if(policy.at("native_headless_model_audit")!=Json::parse(' +
            json.dumps(json.dumps(scope, separators=(',', ':'))) + '))throw std::runtime_error("Exact IQ2 Up model scope required");\n' +
            environment)
        text = once(text, '(ordinal==1&&rows!=reference_rows)', 'false')
        text = once(text, '            else if(ordinal==1&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))\n                throw std::runtime_error("Original additional tokens or bytes differ");',
                    '            // Precision quality differences are recorded before ordinary owner retirement.')
        text = headless_entry(text, scope['kind'], 3, 'Json{{"completed",true},{"IQ2_Up_scope",policy.at("native_headless_model_audit")},{"requests",completed}}')
        if arm == 'candidate':
            text = correct_accounting(text, candidate_triplet_bytes)
            if a.Down_prefix_cache:
                from iq2_down_prefix_cache import accounting_entry
                text = accounting_entry(text)
        if arm == 'candidate' and (not down_carriers or Down_F16):
            wrapper=(ROOT / 'native/app/iq2_up_precision.cpp').read_text()
            if Down_F16:
                wrapper=once(wrapper,'GGML_TYPE_IQ2_XXS','GGML_TYPE_Q2_0')
                wrapper=once(wrapper,'qualified Up path','qualified Down carrier path')
            text += '\n' + wrapper
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
        profile['qualification_observer'] = record(a.F32_observer) if observer else None
        if arm == 'candidate':
            profile['model_layer'] = dict(kind='IQ2-Down' if down_carriers else ('IQ2-Gate-Up' if Gate_layers else 'IQ2-Up'), parent_recipe_sha256=prep['selected_model_sha256'],
                model_receipt=prep['candidate'], application_model_receipt=seal['source_directory']+'/model-receipt.json',
                source_policy=pub['policy'], publication=record(a.publication))
            if down_carriers:
                profile.update(candidate_cache_provider=cache,candidate_cache_source=cache_source,
                    original_Q2_bundle_six_refill_and_quad_paths_disabled=not bool(stream),
                    original_Q2_bundle_and_six_refill_paths_disabled=True)
            if stream:
                profile.update(candidate_cache_provider=cache, candidate_cache_source=cache_source)
        policy = root / 'application-policy.private.json'
        save(policy, profile)
        job = [sys.executable, '-B', ROOT/'tools/relink_retained_current.py', '--current', a.current, '--out', root/'link',
            '--replace', 'entry.o='+str(entry), '--replace', 'early-SELF.o='+original['CPU_SELF_provider']['artifact']['path'], '--application-policy', policy]
        if arm == 'candidate':
            job += ['--replace', 'cache.o='+cache['path']]
            if stream and stream['wrapper']:
                job += ['--add-object', stream['wrapper']['path']]
                job += ['--link-flag=' + flag for flag in stream['required_link_flags']]
            if down_carriers:
                provider=load(a.Down_resource_provider)
                for key,name in [('GPU','gpu.o'),('shader_registry','shader-registry.o')]:
                    job+=['--replace',name+'='+provider[key]['path']]
                for key in ('shader_data','shader_wrapper'):job+=['--add-object',provider[key]['path']]
                job+=['--link-flag='+f for f in provider['link_flags']]
                if Down_F16:job+=['--link-flag=--wrap=ggml_mul_mat_id']
            else:
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
        reused_cache_provider=record(a.cache_provider_proof) if a.cache_provider_proof else None,
        reused_completed_control=record(a.completed_control_case/'result.private.json') if a.completed_control_case else None,
        candidate_only_screen=bool(a.candidate_only),new_matched_control_required_before_adoption=bool(a.candidate_only),
        commands=commands, F32_qualification=bool(observer), original_memory_identity_reset_guards_unchanged=True,
        only_converted_layers_bypass_incompatible_old_bundle_and_quad_paths=True, driver_unchanged=True,
        explicit_global_F32_backend_profile=down_carriers and not Down_F16, IQ2_only_FP32_accumulation=not down_carriers,
        Down_only_FP32_accumulation=Down_F16,
        arithmetic_qualification=arithmetic_qualification,
        MMVQ_decode_qualification=MMVQ_proof,
        format_stream_provider=record(a.format_stream_provider) if stream else None,
        format_stream_IO_qualification=record(a.format_stream_IO_proof) if a.format_stream_IO_proof else None,
        Down_source_prefix_cache=record(a.cache_provider_proof) if a.Down_prefix_cache else None,
        Down_resource_provider=Down_provider,
        precision_wrapper_source=record(ROOT/'native/app/iq2_up_precision.cpp') if not down_carriers or Down_F16 else None,
        actual_candidate_Expert_triplet_bytes=candidate_triplet_bytes,
        PS5_operations=0, native_quality_and_rate_qualified=False, production_adopted=False))
    print(json.dumps(dict(completed=True, model_packages=len(packages), IQ2_Up_layers=prep['IQ2_Up_layers'],
                         IQ2_Gate_layers=Gate_layers,
                         IQ2_Down_layers=prep.get('IQ2_Down_layers',[]), PS5_operations=0)))


if __name__ == '__main__':
    main()
