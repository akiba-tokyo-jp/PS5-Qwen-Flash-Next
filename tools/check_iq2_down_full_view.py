#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check previously unqualified full-row, nonzero-descriptor carrier views on software Vulkan."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load, need, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--provider', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--prior-full-view', type=Path)
    a = p.parse_args()
    rows_per_group = [2, 4] if a.prior_full_view else [1]
    if a.prior_full_view:
        previous_view = load(a.prior_full_view)
        need(previous_view['completed'] and previous_view['full_view_cases'] == 18 and
             previous_view['all_outputs_and_guards_passed'] and previous_view['PS5_operations'] == 0 and
             record(previous_view['plan']['path']) == previous_view['plan'] and
             load(previous_view['plan']['path'])['provider'] == record(a.provider),
             'Reuse the completed row-one full-view scope; execute only new row-two/four specializations')
    provider = load(a.provider)
    proof_row = provider['software_proof']
    need(record(proof_row['path']) == proof_row, 'The completed tile proof must remain exact')
    proof = load(proof_row['path'])
    need(proof['completed'] and proof['actual_model_matvec_shaders'] == 6 and
         proof['shape_cases'] == 18 and proof['all_outputs_passed'] and
         proof['all_GPU_resources_positively_retired'] and proof['PS5_operations'] == 0,
         'Reuse the six qualified F32 resources without replaying their old tile scope')
    previous = Path(proof_row['path']).parent
    plan = load(previous / 'plan.private.json')
    need(all(record(r['path']) == r for r in plan['inputs']), 'Every original software input must be unchanged')
    manifest = load(plan['manifest']['path'])
    build = load(provider['shaders']['path'])
    need(record(provider['shaders']['path']) == provider['shaders'], 'The selected resource build changed')
    shaders = [dict(r, indexed='_id_' in r['name'], half_input=False) for r in build['shaders']
        if r['name'].startswith('mul_mat_vec_') and r['recipe']['defines']['B_TYPE'] == 'float']
    need(len(shaders) == 6 and len(manifest['cases']) == 3 and
         all(record(r['artifact']['path']) == r['artifact'] for r in shaders), 'Exact six shaders and three layers required')
    a.out.mkdir(parents=True, exist_ok=False)
    source = (previous / 'model_shader_fixture.private.cpp').read_text()
    source = once(source, '    const float zero=0;std::vector<float>output(values+128,42.125f);',
        '''    const std::size_t descriptor_prefix=22u*537600u+460800u;
    const std::size_t payload_bytes=packed.size(),suffix_bytes=16384;
    auto payload=packed;packed.assign(descriptor_prefix+payload_bytes+suffix_bytes,0xa5);
    std::memcpy(packed.data()+descriptor_prefix,payload.data(),payload_bytes);
    const float zero=0;std::vector<float>output(values+128,42.125f);''')
    source = once(source, '    a.vkUpdateDescriptorSets(a.device,6,writes,0,nullptr);',
        '''    bi[0].offset=descriptor_prefix;bi[0].range=payload_bytes;
    need(descriptor_prefix%a.properties.limits.minStorageBufferOffsetAlignment==0,"Exact aligned nonzero descriptor required");
    a.vkUpdateDescriptorSets(a.device,6,writes,0,nullptr);''')
    source = once(source, '    for(unsigned row:{0u,1248u,2496u})a.vkCmdDispatchBase(command,row,0,0,64,selected,1);',
        '    a.vkCmdDispatchBase(command,0,0,0,2560,selected,1);')
    source = once(source, '    bool canaries=true;unsigned mismatches=0,compared=0;double maximum=0;',
        '''    const auto*observed=static_cast<const unsigned char*>(buffers[0].mapped);
    bool canaries=!std::memcmp(observed,packed.data(),descriptor_prefix)&&
        !std::memcmp(observed+descriptor_prefix+payload_bytes,packed.data()+descriptor_prefix+payload_bytes,suffix_bytes);
    unsigned mismatches=0,compared=0;double maximum=0;''')
    source = once(source, '        const bool touched=inside&&(row<64||(row>=1248&&row<1312)||row>=2496);',
        '        const bool touched=inside;')
    source = once(source, '{"distinct_row_tiles",3}',
        '{"distinct_row_tiles",40},{"descriptor_prefix_bytes",descriptor_prefix},{"all2560_rows",true}')
    if a.prior_full_view:
        source = once(source, 'const Json&c,bool indexed,bool half_input){',
            'const Json&c,bool indexed,bool half_input,unsigned rows_per_group){')
        source = once(source, 'a.vkCmdDispatchBase(command,0,0,0,2560,selected,1);',
            'a.vkCmdDispatchBase(command,0,0,0,2560/rows_per_group,selected,1);')
        source = once(source, '    for(const auto&shader:manifest.at("shaders")){',
            '    for(const auto&shader:manifest.at("shaders")){for(unsigned rows_per_group:{2u,4u}){')
        source = once(source, 'no_shared?subgroup.subgroupSize:32u,1,1',
            'no_shared?subgroup.subgroupSize:32u,rows_per_group,1')
        source = once(source, 'c,shader.at("indexed"),shader.at("half_input"));',
            'c,shader.at("indexed"),shader.at("half_input"),rows_per_group);row["rows_per_group"]=rows_per_group;')
        source = once(source, 'a.vkDestroyShaderModule(a.device,module,nullptr);\n    }',
            'a.vkDestroyShaderModule(a.device,module,nullptr);\n    }}')
    generated = a.out / 'model_shader_fixture.private.cpp'
    generated.write_text(source, newline='\n')
    api = a.out / 'model_shader_desktop_API.private.h'
    api.write_bytes((previous / api.name).read_bytes())
    manifest_path = a.out / 'cases.private.json'
    save(manifest_path, dict(shaders=shaders, cases=manifest['cases']))
    command = [x.replace(str(previous), str(a.out)) for x in plan['command']]
    executable = a.out / Path(plan['executable']['path']).name
    env = dict(os.environ, TMP=str(a.out), TEMP=str(a.out))
    compiler_directory = str(Path(command[0]).parent)
    env['PATH'] = compiler_directory + os.pathsep + env.get('PATH', '')
    need(record(plan['software_ICD']['path']) == plan['software_ICD'], 'The qualified software-only ICD changed')
    env['VK_DRIVER_FILES'] = plan['software_ICD']['path']
    save(a.out / 'plan.private.json', dict(completed=True, provider=record(a.provider), prior_tile_proof=proof_row,
        source=record(generated), API=record(api), manifest=record(manifest_path), command=command,
        full_rows=2560, descriptor_prefix_bytes=12288000, expected_cases=18*len(rows_per_group),
        rows_per_group=rows_per_group, prior_full_view=record(a.prior_full_view) if a.prior_full_view else None,
        old_tile_scope_replayed=False,
        PS5_operations=0, physical_GPU_execution=False))
    run = subprocess.run(command, capture_output=True, timeout=90, env=env)
    (a.out / 'compile.private.log').write_bytes(run.stdout + run.stderr)
    need(run.returncode == 0, run.stderr.decode(errors='replace')[-2500:])
    output = a.out / 'software.private.json'
    with (a.out / 'software.private.log').open('xb') as stream:
        run = subprocess.run([str(executable), str(manifest_path), str(output)], stdout=stream,
            stderr=subprocess.STDOUT, timeout=600, env=env)
    need(run.returncode == 0, 'The changed full-view scope returned failure; preserve its completed prefix')
    result = load(output)
    need(result['completed'] and result['all_GPU_resources_positively_retired'] and len(result['cases']) == 18*len(rows_per_group) and
         all(r['passed'] and r['positive_fence'] and r['all_case_resources_retired'] and
             r['all2560_rows'] and r['compared_values'] == 5120 and r['descriptor_prefix_bytes'] == 12288000
             for r in result['cases']), 'Every complete nonzero-view output and guard must pass')
    save(a.out / 'result.private.json', dict(completed=True, plan=record(a.out / 'plan.private.json'),
        software=record(output), full_view_cases=18*len(rows_per_group), complete_output_values=92160*len(rows_per_group),
        rows_per_group=rows_per_group,
        descriptor_prefix_bytes=12288000, all_outputs_and_guards_passed=True,
        software_only=True, native_GGML_failure_cause_proved=False, native_model_speed_qualified=False,
        PS5_operations=0, unchanged_completed_tests_replayed=0))
    print(json.dumps(dict(completed=True, full_view_cases=18*len(rows_per_group),
        output_values=92160*len(rows_per_group), PS5_operations=0)))


if __name__ == '__main__':
    main()
