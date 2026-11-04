#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe existing input-mode and stream-sync eligibility without changing GPU work."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'cache-proof', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--resume-entry', action='store_true')
    parser.add_argument('--resume-package', action='store_true')
    args = parser.parse_args()
    need(not (args.resume_entry and args.resume_package), 'Continue only one positively completed build suffix')
    if args.resume_entry or args.resume_package:
        need(args.out.is_dir() and not (args.out / 'result.private.json').exists(), 'Continue only the unfinished host entry build')
    else:
        args.out.mkdir(parents=True, exist_ok=False)
    selected = load(args.current / 'provenance/selected-entry-build.private.json')
    profile = load(selected['application_policy']['path'])
    source = Path(profile['source']['path'])
    need(record(source) == profile['source'], 'Exact selected P1 entry required')
    cache = load(args.cache_proof)
    need(cache['completed'] and record(cache['source']['path']) == cache['source'], 'Exact reconstructed cache source required')
    actual = cache['actual_provider']
    need(record(actual['path']) == actual, 'The reconstructed source must still bind the selected cache object')
    if args.resume_package:
        link = load(args.out / 'link/result.private.json')
        changed = load(args.out / 'application-policy.private.json')
        need(link['completed'] and record(link['artifact']['path']) == link['artifact'] and
             record(changed['source']['path']) == changed['source'] and
             record(changed['entry_artifact']['path']) == changed['entry_artifact'],
             'Retain the already compiled and linked observation; do not rebuild it')
        finish_package(args, changed)
        return
    for header in source.parent.glob('*.h'):
        shutil.copyfile(header, args.out / header.name)
    commands = []

    def run(command, label):
        command = list(map(str, command))
        commands.append(command)
        result = subprocess.run(command, capture_output=True, timeout=360,
            env=dict(os.environ, TMP=str(args.out), TEMP=str(args.out)))
        with (args.out / (label + '.private.log')).open('xb') as stream:
            stream.write(result.stdout + result.stderr)
        need(result.returncode == 0, (result.stdout + result.stderr).decode(errors='replace')[-4000:])

    original_cache = Path(cache['source']['path']).read_text(encoding='utf-8')
    context = '''#include <cstdint>
static std::uint64_t strata_stream_counts[8]{};
extern "C" void qwen_strata_stream_counts(std::uint64_t*out){for(unsigned i=0;i<8;++i)out[i]=strata_stream_counts[i];}
'''
    cache_text = context + original_cache
    marker = '            for(unsigned first=0;first<remaining;first+=4){'
    additions = '''            ++strata_stream_counts[0];strata_stream_counts[1]+=remaining;
            const unsigned strata_groups=(remaining+3)/4;
            strata_stream_counts[2]+=strata_groups;
            if(strata_groups)strata_stream_counts[3]+=strata_groups-1;
            if(strata_groups>1)++strata_stream_counts[4];
'''
    cache_text = once(cache_text, marker, additions + marker)
    begin = cache_text.index('        if(qwen_app_Q2_quad_enabled()&&!six_refill){')
    end = cache_text.index('\n        for (size_t ip = 0;', begin)
    block = cache_text[begin:end]
    block = once(block, '                ggml_backend_synchronize(backend);',
        '                ++strata_stream_counts[5];ggml_backend_synchronize(backend);')
    block = once(block, '                    ggml_backend_tensor_set(u.banks[id],data,offset,u.bytes[id]);',
        '                    ggml_backend_tensor_set(u.banks[id],data,offset,u.bytes[id]);++strata_stream_counts[6];')
    block = once(block, ')){for(unsigned e=0;e<experts;++e)delivered[available[first+e]]=true;',
        ')){++strata_stream_counts[7];for(unsigned e=0;e<experts;++e)delivered[available[first+e]]=true;')
    cache_text = cache_text[:begin] + block + cache_text[end:]
    restored = cache_text[len(context):].replace(additions, '', 1)
    restored = restored.replace('++strata_stream_counts[5];', '', 1).replace('++strata_stream_counts[6];', '', 1)
    restored = restored.replace('++strata_stream_counts[7];', '', 1)
    need(restored == original_cache, 'Only bounded CPU observation counters may change the selected cache')
    cache_source, cache_object = args.out / 'cache.private.cpp', args.out / 'cache.o'
    command = cache['command'].copy()
    command[command.index('-c') + 1], command[command.index('-o') + 1] = str(cache_source), str(cache_object)
    if '-MF' in command:
        command[command.index('-MF') + 1] = str(args.out / 'cache.private.d')
    if args.resume_entry:
        need(cache_source.read_text(encoding='utf-8') == cache_text and cache_object.is_file() and
             (args.out / 'cache-compile.private.log').is_file() and
             b'redefinition' in (args.out / 'entry-compile.private.log').read_bytes(),
             'Reuse only the exact positive cache compilation after the known host overlay failure')
        save(args.out / 'reused-positive-cache-build.private.json', dict(source=record(cache_source),
            artifact=record(cache_object), known_entry_failure=record(args.out / 'entry-compile.private.log'),
            cache_recompilations=0, PS5_operations=0))
    else:
        cache_source.write_text(cache_text, encoding='utf-8', newline='\n')
        run(command, 'cache-compile')

    scope = dict(schema='ps5-qwen-strata-applicability-v1', kind='Strata-applicability', requests=3,
        model_loads=1, HTTP_requests=0, VideoOut_starts=0, original_cold_retained_exact_prefix_sequence=True,
        GPU_instructions_unchanged=True, source_IO_and_completion_unchanged=True,
        original_live_reserves_preserved=True, persistent_caches=False, selected_cache_slots=3712)
    baseline = source.read_text(encoding='utf-8')
    entry = '''extern "C" void qwen_strata_stream_counts(std::uint64_t*);
static std::array<std::uint64_t,8> strata_stream_report(){std::array<std::uint64_t,8>r{};qwen_strata_stream_counts(r.data());return r;}
''' + baseline
    # Use declarations after standard includes, preserving the exact original file prefix.
    declaration, entry = entry[:entry.index(baseline)], baseline
    marker = 'int main(int argc, char ** argv) {'
    entry = once(entry, marker, declaration + '\n' + marker)
    policy_marker = '        const auto policy = Json::parse(policy_file);'
    entry = once(entry, policy_marker, policy_marker + '\n        if(policy.at("native_headless_model_audit")!=Json::parse(' +
        json.dumps(json.dumps(scope, separators=(',', ':'))) + '))throw std::runtime_error("Exact Strata observation scope required");')
    entry = once(entry, '            row["routing_policy"]=',
        '            row["strata_stream_counts_after"]=strata_stream_report();\n'
        '            row["strata_integer_dot_disabled"]=getenv("GGML_VK_DISABLE_INTEGER_DOT_PRODUCT")&&std::strcmp(getenv("GGML_VK_DISABLE_INTEGER_DOT_PRODUCT"),"1")==0;\n'
        '            row["routing_policy"]=')
    entry = headless_entry(entry, scope['kind'], 3,
        'Json{{"completed",true},{"strata_scope",policy.at("native_headless_model_audit")},{"requests",completed},{"strata_stream_counts_final",strata_stream_report()}}')
    for name in ('observed_system_headroom', 'require_model_CPU_budget', 'wait_for_initial_model_CPU_budget',
                 'model_file_identity', 'model_directory_identity', 'resident_reset_empty_context'):
        need(body(entry, name) == body(baseline, name), 'An original memory, identity or reset guard changed: ' + name)
    need(entry.count('setenv("GGML_VK_DISABLE_INTEGER_DOT_PRODUCT","1",1)') == 1 and 'unsetenv(' not in entry,
         'The selected floating-activation policy must remain unchanged')
    entry_source, entry_object = args.out / 'entry.private.cpp', args.out / 'entry.o'
    entry_source.write_text(entry, encoding='utf-8', newline='\n')
    command = next(row.copy() for row in selected['commands'] if '-ivfsoverlay' in row)
    view = load(command[command.index('-ivfsoverlay') + 1])
    for row in view['roots']:
        local = args.out / Path(row['external-contents']).name
        if local.exists():
            row['external-contents'] = local.resolve().as_posix()
    overlay = args.out / 'selected-view.private.json'
    save(overlay, view)
    command[command.index('-ivfsoverlay') + 1] = str(overlay)
    command[1:1] = ['-I', str(args.out)]
    command[command.index('-c') + 1], command[command.index('-o') + 1] = str(entry_source), str(entry_object)
    if '-MF' in command:
        command[command.index('-MF') + 1] = str(args.out / 'entry.private.d')
    run(command, 'entry-compile-corrected' if args.resume_entry else 'entry-compile')
    changed = copy.deepcopy(profile)
    changed.update(kind='headless-model-audit', entry_artifact=record(entry_object), source=record(entry_source),
        headless_model_audit=True, headless_audit_kind=scope['kind'], headless_requests=3,
        model_and_GPU_topology_unchanged=False, model_and_GPU_guards_preserved=True,
        overrides=dict(profile['overrides'], native_headless_model_audit=scope),
        performance_timings_usable=False, native_performance_qualified=False, production_adopted=False)
    policy = args.out / 'application-policy.private.json'
    save(policy, changed)
    run([sys.executable, '-B', ROOT / 'tools/relink_retained_current.py', '--current', args.current,
        '--out', args.out / 'link', '--replace', 'entry.o=' + str(entry_object), '--replace', 'cache.o=' + str(cache_object),
        '--replace', 'early-SELF.o=' + profile['CPU_SELF_provider']['artifact']['path'], '--application-policy', policy], 'link')
    finish_package(args, changed, commands)


def finish_package(args, changed, commands=None):
    identity = load(args.current / 'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    bound = load(identity['path'])
    retained = load(args.current / 'provenance/retained-relink-inputs.private.json')
    matches = [row for row in retained if all(row[key] == bound['artifact'][key] for key in ('bytes', 'sha256'))]
    need(len(matches) == 1, 'One retained byte-identical data-only identity provider required')
    row = {key: matches[0][key] for key in ('path', 'bytes', 'sha256')}
    need(record(row['path']) == row, 'Canonical identity provider changed')
    bound.update(artifact=row, canonical_path_rebind_of=identity, recompilations=0)
    identity_path = args.out / 'retained-required-input-identities.private.json'
    save(identity_path, bound)
    packaged = args.out / 'SELF-retained-identity'
    command = list(map(str, [sys.executable, '-B', ROOT / 'tools/package_retained_current.py', '--workspace', args.workspace,
        '--current', args.current, '--relink', args.out / 'link/result.private.json', '--out', packaged,
        '--formatter-from', args.current / 'provenance/current-package.private.json', '--identity-provider', identity_path]))
    result = subprocess.run(command, capture_output=True, timeout=360)
    with (args.out / 'SELF-retained-identity.private.log').open('xb') as stream:
        stream.write(result.stdout + result.stderr)
    need(result.returncode == 0, (result.stdout + result.stderr).decode(errors='replace')[-4000:])
    save(args.out / 'result.private.json', dict(completed=True, package=record(packaged / 'result.private.json'),
        cache_source=record(args.out / 'cache.private.cpp'), entry_source=changed['source'], commands=(commands or []) + [command],
        original_cache_recovers_after_removing_CPU_counters=True, original_guards_unchanged=True,
        original_integer_dot_disable_retained=True, GPU_provider_and_shader_bytes_unchanged=True,
        retained_data_provider_rebound_without_recompilation=True,
        PS5_operations=0, native_applicability_pending=True, production_adopted=False))
    print(json.dumps(dict(completed=True, package=str(packaged / 'result.private.json'), PS5_operations=0)), flush=True)


if __name__ == '__main__':
    main()
