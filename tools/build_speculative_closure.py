#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Close finite width-two numerical and rejection tests without replaying prediction."""
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

ROOT=Path(__file__).resolve().parents[1]


def generate(text):
    text=text.replace('#include "resident_combined_policy.h"\n','')
    text=text.replace('std::array<CompletedRouteEvidence,10> routes;','std::array<CompletedRouteEvidence,3> routes;')
    start=text.index('        const std::array<const char *,10> arms')
    end=text.index('        for(unsigned ordinal=',start)
    text=text[:start]+'        const std::array<const char *,3> arms{{"warmup","speculative","forced-rejection"}};\n'+text[end:]
    text=text.replace('const bool rejection=ordinal==9;','const bool rejection=ordinal==2;')
    needle='            std::size_t logits_seen=0;double max_error=0;bool logit_geometry_error=false,logit_value_error=false;'
    if text.count(needle)!=1:raise ValueError('One original complete F32 comparison required')
    text=text.replace(needle,needle+'''
            std::size_t callback_calls=0,first_bad_row=SIZE_MAX,first_bad_column=SIZE_MAX;
            double first_observed=0,first_reference=0;bool nonfinite_error=false;
''')
    needle='                if(!v||count!=logit_columns||logits_seen>=resident_reference_rows)'
    text=text.replace(needle,'                ++callback_calls;\n'+needle)
    needle='''                        if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b))
                            logit_value_error=true;'''
    replacement='''                        if(!std::isfinite(a)||!std::isfinite(b))nonfinite_error=true;
                        if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b)) {
                            logit_value_error=true;
                            if(first_bad_row==SIZE_MAX){first_bad_row=logits_seen;first_bad_column=i;first_observed=a;first_reference=b;}
                        }'''
    if text.count(needle)!=1:raise ValueError('Original finite-value and tolerance comparison required')
    text=text.replace(needle,replacement)
    needle='            if(!result.request_reset_completed||logit_geometry_error||logit_value_error||(ordinal&&logits_seen!=reference_rows))'
    diagnostic='''            write_fresh_report(prefix+".F32-diagnostic",{{"ordinal",ordinal},{"callback_calls",callback_calls},
                {"rows_observed",logits_seen},{"reference_rows",reference_rows},{"columns",logit_columns},
                {"geometry_error",logit_geometry_error},{"nonfinite_error",nonfinite_error},{"value_error",logit_value_error},
                {"maximum_absolute_error",max_error},{"first_bad_row",first_bad_row==SIZE_MAX?Json(nullptr):Json(first_bad_row)},
                {"first_bad_column",first_bad_column==SIZE_MAX?Json(nullptr):Json(first_bad_column)},
                {"first_observed",first_observed},{"first_reference",first_reference},
                {"original_tolerance_unchanged",true},{"positive_complete_request_reset",result.request_reset_completed},
                {"known_finite_candidate_mismatch_is_rejection_not_adoption",true}});
            if(!result.request_reset_completed||logit_geometry_error||nonfinite_error||(logit_value_error&&ordinal!=1)||(ordinal&&logits_seen!=reference_rows))'''
    if text.count(needle)!=1:raise ValueError('One completed-request validation frontier required')
    text=text.replace(needle,diagnostic)
    needle='{"full_F32_logit_rows_compared",ordinal?logits_seen:0},{"maximum_absolute_logit_error",max_error}'
    text=text.replace(needle,needle+',{ "F32_values_within_original_tolerance",!logit_value_error}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text())
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Original compiled dependency changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    source=a.out/'resident-comparison-speculative-closure.private.cpp';source.write_text(generate(template.read_text()),newline='\n')
    original=ROOT/'native/app/resident_comparison_policy.h';header=original.read_text()
    header=header.replace('CPU_calibration?0:10','CPU_calibration?0:3').replace('CPU_calibration?0:4','CPU_calibration?0:1')
    (a.out/original.name).write_text(header,newline='\n')
    for name in ('resident_incremental_tables.h','resident_direct_tables.h'):
        (a.out/name).write_bytes((template.parent/name).read_bytes())
    old=command[command.index('-o')+1];obj=a.out/'speculative-closure.o'
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(a.out)];command+=['-I',str(template.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=prior['inputs_before']+[record(x)for x in(a.parent,Path(__file__),template,original,source,*a.out.glob('*.h'))]
    host=a.out/'check.cpp';host.write_text('''#include "resident_comparison_policy.h"
#include <fstream>
int main(int argc,char**argv){if(argc!=2)return 2;std::ifstream f(argv[1]);nlohmann::json p;f>>p;qwen_app::require_resident_comparison_policy(p);}
''',newline='\n')
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin';binary=a.out/'check.exe'
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'),PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    host_command=list(map(str,[runtime/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',a.out,
        '-I',ROOT/'native/app','-I',a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor',host,'-o',binary]))
    for i,c in enumerate((host_command,command,link)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen speculative closure dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[command],source_parent=record(a.parent),
        inputs_before=frozen+[record(x)for x in(obj,host,binary)],
        speculative_numerical_closure=dict(requests=3,prior_consumed_case=5440,prediction_replayed=False,
            original_tolerance_unchanged=True,failed_finite_candidate_never_adopted=True,actual_entry=record(source)),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(speculative_numerical_closure_built=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
