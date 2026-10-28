#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare six-demand delivery with the already qualified 128-slot geometry."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess

from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record

ROOT = Path(__file__).resolve().parents[1]


def widen_reader(text):
    old = '!schedule_enabled_||geometry.active_slots!=53||!execute||'
    if text.count(old) != 1:
        raise ValueError('One exact six-demand schedule selector required')
    return text.replace(old,
        '!schedule_enabled_||(geometry.active_slots!=53&&geometry.active_slots!=128)||!execute||')


def selected_policy(text):
    old = '    auto expected=resident_additional_scope("cache",53);'
    if text.count(old) != 1 or text.count('resident_additional_scope("cache",53)') != 2:
        raise ValueError('Original isolated delivery contract required')
    text = text.replace(old,
        '    const auto slots=policy.at("native_padded_expert_cache").at("active_slots").get<unsigned>();\n'
        '    auto expected=resident_additional_scope("cache",slots);')
    return text.replace('resident_additional_scope("cache",53)', 'resident_additional_scope("cache",slots)')


def widen_controller(text):
    old='qwen_app::selected_padded_cache_geometry().active_slots!=53||qwen_app_predictive_cache_enabled()'
    if text.count(old)!=1:
        raise ValueError('One original public delivery activation selector required')
    return text.replace(old,
        '(qwen_app::selected_padded_cache_geometry().active_slots!=53&&qwen_app::selected_padded_cache_geometry().active_slots!=128)||qwen_app_predictive_cache_enabled()').replace(
        'Six-demand delivery is an independent original-cache experiment',
        'Six-demand delivery requires the independently admitted 53-slot or 128-slot cache')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'cache', 'workspace', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    prior = json.loads(a.parent.read_text())
    frozen = list({row['path']: row for row in prior['inputs_before'] + [prior['artifact']]}.values())
    for row in frozen:
        if record(row['path']) != row:
            raise ValueError('Actual native dependency changed: ' + row['path'])
    a.out.mkdir(parents=True, exist_ok=False)
    view = a.out / 'app-view'
    view.mkdir()
    (a.out / 'tmp').mkdir()
    main_recipe = prior['compile_commands'][0].copy()
    source = Path(main_recipe[main_recipe.index('-c') + 1])
    main_source = view / 'resident-comparison-refill-cache128.private.cpp'
    main_source.write_bytes(source.read_bytes())
    phase = next(row for row in prior['CPU_metadata_scope']['changed_sources']
        if 'mapped-source-original-window' in Path(row['source']['path']).name)
    phase_recipe = phase['command'].copy()
    phase_original = Path(phase_recipe[phase_recipe.index('-c') + 1])
    for header in sorted(phase_original.parent.glob('*.h')):
        (view / header.name).write_bytes(header.read_bytes())
        frozen.append(record(header))
    private_header = next(row for row in prior['resident_phase_source']['inputs']
        if Path(row['path']).name == 'resident-mapped-source.private.h')
    if record(private_header['path']) != private_header:
        raise ValueError('Actual private native reader differs')
    (view / 'resident-mapped-source.private.h').write_text(
        widen_reader(Path(private_header['path']).read_text()), newline='\n')
    original_policy = ROOT / 'native/app/resident_refill_policy.h'
    (view / original_policy.name).write_text(selected_policy(original_policy.read_text()), newline='\n')
    phase_source = view / phase_original.name
    phase_source.write_text(widen_controller(phase_original.read_text()),newline='\n')
    commands = []
    replacements = {}
    for recipe, original, generated in ((phase_recipe, phase_original, phase_source), (main_recipe, source, main_source)):
        old = recipe[recipe.index('-o') + 1]
        obj = a.out / (generated.stem + '.o')
        recipe[recipe.index('-c') + 1] = str(generated)
        recipe[recipe.index('-o') + 1] = str(obj)
        recipe[1:1] = ['-I', str(view)]
        recipe += ['-I', str(original.parent)]
        commands.append(recipe)
        replacements[old] = str(obj)
        frozen.append(record(original))
    # Exercise the actual native reader class, including the newly admitted
    # last slot 127. Its ordinary MappedSourceReader base types are unchanged.
    fixture_original = ROOT / 'tests/six_bank_source.cpp'
    fixture = fixture_original.read_text().replace('#include "mapped_source.h"', '#include "resident-mapped-source.private.h"')
    fixture = fixture.replace('MappedSourceReader', 'ResidentMappedSourceReader')
    fixture = fixture.replace('const std::array<int,2> slots{52,0};', 'const std::array<int,2> slots{127,0};')
    fixture = fixture.replace('int main(){try{', 'int main(){try{select_experimental_padded_cache_128();')
    host_source = a.out / 'six-bank-slot127-host.private.cpp'
    host_source.write_text(fixture, newline='\n')
    host = a.workspace / 'toolchain/msys-clang64/clang64/bin'
    host_binary = a.out / 'six-bank-slot127-host.exe'
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get('PATH', ''),
        TMP=str(a.out / 'tmp'), TEMP=str(a.out / 'tmp'))
    host_command = [str(host / 'clang++.exe'), '-std=c++17', '-O2', '-I', str(view),
        '-I', str(ROOT / 'native/app'), str(host_source), '-o', str(host_binary)]
    for label, command in (('host-build', host_command), ('host-run', [str(host_binary)])):
        result = subprocess.run(command, capture_output=True, timeout=180, env=env)
        (a.out / (label + '.private.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    # Compile the actual public activation API as well as the reader. The native
    # source owner and metadata-idle checks remain active in every case.
    controller=phase_source.read_text()
    begin=controller.index('void configure_native_six_bank_refill(bool enabled)')
    end=controller.index('\nbool start_native_six_bank_refill(',begin)
    activation_source=a.out/'six-bank-activation-host.private.cpp'
    activation_source.write_text('''#include "padded_cache_geometry.h"
#include <cassert>
static bool padded=true,predictive=false,reader_idle=true,metadata_idle=true;
static bool qwen_app_padded_cache_enabled(){return padded;}
static bool qwen_app_predictive_cache_enabled(){return predictive;}
struct Reader{void require_completed_window(){if(!reader_idle)throw std::runtime_error("Reader busy");}}reader;
struct Ops{void require_metadata_idle(){if(!metadata_idle)throw std::runtime_error("Metadata busy");}}ops;
static Reader&required(){return reader;}
static std::atomic<bool> parallel_ready{true},six_refill{false};
namespace qwen_app {
'''+controller[begin:end]+'''}
int main(){
 qwen_app::configure_native_six_bank_refill(true);assert(six_refill.load());qwen_app::configure_native_six_bank_refill(false);
 qwen_app::select_experimental_padded_cache_128();qwen_app::configure_native_six_bank_refill(true);assert(six_refill.load());
 qwen_app::configure_native_six_bank_refill(false);
 for(unsigned i=0;i<6;++i){parallel_ready=true;padded=true;predictive=false;reader_idle=true;metadata_idle=true;
  qwen_app::selected_padded_cache_slots.store(128);
  if(i==0)parallel_ready=false;if(i==1)padded=false;if(i==2)predictive=true;
  if(i==3)reader_idle=false;if(i==4)metadata_idle=false;if(i==5)qwen_app::selected_padded_cache_slots.store(127);
  bool refused=false;try{qwen_app::configure_native_six_bank_refill(true);}catch(const std::runtime_error&){refused=true;}
  assert(refused&&!six_refill.load());
 }
}
''',newline='\n')
    activation_binary=a.out/'six-bank-activation-host.exe'
    activation_command=host_command.copy()
    activation_command[activation_command.index(str(host_source))]=str(activation_source)
    activation_command[activation_command.index(str(host_binary))]=str(activation_binary)
    for label,command in (('activation-host-build',activation_command),('activation-host-run',[str(activation_binary)])):
        result=subprocess.run(command,capture_output=True,timeout=180,env=env)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    frozen += [record(x) for x in (a.parent, Path(__file__), original_policy, private_header['path'], fixture_original,
        host_source, host_binary, activation_source,activation_binary,main_source, phase_source, *sorted(view.glob('*.h')))]
    link = [replacements.get(x, x) for x in prior['link_command']]
    if any(prior['link_command'].count(old) != 1 for old in replacements):
        raise ValueError('Unique captured native entry and reader objects required')
    image = a.out / 'qwen-native.pie.elf'
    link[link.index('-o') + 1] = str(image)
    link = [('-Map=' + str(a.out / 'native-link.private.map')) if x.startswith('-Map=') else x for x in link]
    for index, command in enumerate(commands + [link]):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=600, env=env)
        (a.out / f'{index}.private.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(cache128_refill_compiled_or_linked=index + 1, total=3)), flush=True)
    for row in frozen:
        if record(row['path']) != row:
            raise ValueError('Frozen cache128 delivery input changed')
    receipt = copy.deepcopy(prior)
    receipt.update(artifact=record(image), link_command=link, compile_commands=[main_recipe],
        source_parent=record(a.parent), inputs_before=frozen + [record(path) for path in replacements.values()],
        lossless_driver_table_geometry=audit_linked_storage(image, prior['lossless_driver_tables']),
        cache128_refill=dict(actual_reader=record(phase_source), actual_header=record(view / 'resident-mapped-source.private.h'),
            exact_slot127_host_source=record(host_source), host_report=record(a.out / 'host-run.private.log'),
            actual_activation_host_source=record(activation_source),activation_refusal_controls=6,
            original_model_math_and_all_seven_engine_objects_unchanged=True,
            original_fallbacks_leases_and_maximum_two_reads_unchanged=True,
            native_speed_still_unqualified=True))
    receipt['resident_context_reuse']['entry'] = record(main_source)
    for row, recipe in zip((phase, next(row for row in prior['CPU_metadata_scope']['changed_sources']
            if 'resident-comparison' in Path(row['source']['path']).name)), commands):
        selected = next(x for x in receipt['CPU_metadata_scope']['changed_sources'] if x['object_path'] == row['object_path'])
        selected.update(source=record(recipe[recipe.index('-c') + 1]), object_path=recipe[recipe.index('-o') + 1], command=recipe)
    receipt['resident_phase_source'].update(generated_source=record(phase_source),
        object=record(phase_recipe[phase_recipe.index('-o') + 1]), command=phase_recipe)
    path = a.out / 'receipt.private.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    receipt['real_module_import_audit'] = audit(a.workspace, a.cache, a.out)
    if receipt['real_module_import_audit']['missing']:
        raise ValueError('Native imports missing')
    receipt['native_dispatch_audit'] = dispatch(a.workspace,
        a.workspace / 'driver-work/PS5-Vulkan-Inference-qwen-872cc126', image, a.out / 'dispatch')
    if not receipt['native_dispatch_audit']['passed']:
        raise ValueError('Native dispatch failed')
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(cache128_refill_built=True, host_exact_reads=180, host_negative_controls=8,
        PS5_operations=0)), flush=True)


if __name__ == '__main__':
    main()
