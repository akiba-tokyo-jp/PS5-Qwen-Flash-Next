#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify exact prefix reuse on the current 128-slot delivery objects."""
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


def generate(base, prefix, scope):
    marker='        const bool prefix_comparison='
    result=base[:base.index(marker)]+prefix[prefix.index(marker):]
    if 'static Json report_load_VM()'not in result:
        start=prefix.index('static std::atomic_flag load_VM_lock=')
        end=prefix.index('static Json bind_resident_main_SELF(',start)
        at=result.index('static Json bind_resident_main_SELF(')
        result=result[:at]+prefix[start:end]+result[at:]
        result=result.replace('model_params.progress_callback=observe_model_load;',
            'model_params.progress_callback=observe_load_VM;')
        needle='        qwen_native_stage("model_load_completed");'
        if result.count(needle)!=1:raise ValueError('One positively returned model loader required')
        result=result.replace(needle,needle+'\n        write_fresh_report(startup.admission_report+".resident.loader-VM",report_load_VM());')
    old='qwen_app::require_resident_refill_policy(policy);'
    if result.count(old)!=1:raise ValueError('One isolated delivery policy frontier required')
    gate='qwen_app::require_resident_additional_policy(policy,"prefix");\n'
    gate+='        if(policy.at("native_prefix_delivery_combination")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))'
    gate+='throw std::runtime_error("Exact independently qualified prefix/delivery combination required");'
    result=result.replace(old,gate)
    result=result.replace('{"kind","prefix"},{"active_cache_slots",53}',
        '{"kind","prefix"},{"active_cache_slots",cache_geometry.active_slots}')
    marker='        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {'
    if result.count(marker)!=1:raise ValueError('One complete nine-request prefix cohort required')
    enabled='true' if scope['six_demand_enabled'] else 'false'
    result=result.replace(marker,'        qwen_app::configure_native_six_bank_refill('+enabled+');\n'+marker+
        '\n            qwen_six_bank_refill_stats delivery_before{};qwen_app_six_bank_refill_counters(&delivery_before);')
    marker='            completed.push_back(row);write_fresh_report(report_prefix+".result",row);'
    extra='''            qwen_six_bank_refill_stats delivery_after{};qwen_app_six_bank_refill_counters(&delivery_after);
            const auto delivery_batches=delivery_after.batches-delivery_before.batches;
            const auto delivery_reads=delivery_after.reads-delivery_before.reads;
            const auto delivery_bytes=delivery_after.logical_bytes-delivery_before.logical_bytes;
            if(qwen_app_six_bank_refill_enabled()!=DELIVERY_ENABLED||
               (DELIVERY_ENABLED?(!delivery_batches||delivery_reads!=6*delivery_batches||!delivery_bytes):
                   (delivery_batches||delivery_reads||delivery_bytes)))
                throw std::runtime_error("Actual six-demand combination accounting differs");
            row["six_demand"]={{"enabled",DELIVERY_ENABLED},{"batches",delivery_batches},
                {"reads",delivery_reads},{"logical_bytes",delivery_bytes}};
'''.replace('DELIVERY_ENABLED',enabled)
    if result.count(marker)!=1:raise ValueError('One positively reset prefix result required')
    result=result.replace(marker,extra+marker)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','prefix-parent','prefix-review','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--refill-review',type=Path)
    a=p.parse_args();prior=json.loads(a.parent.read_text());prefix=json.loads(a.prefix_parent.read_text())
    qualified=json.loads(a.prefix_review.read_text())
    if not(qualified['kind']=='prefix' and qualified['full_F32_rows_compared']==184 and
           qualified['prefix_pair_total']['reproducible_in_this_finite_cohort'] and
           qualified['only_closed_completed_native_evidence_used']):
        raise ValueError('Complete reverse-order exact prefix qualification required')
    refill=json.loads(a.refill_review.read_text())if a.refill_review else None
    enabled=bool(refill and refill['kind']=='refill' and
        refill['comparison']['decode']['reproducible_in_this_finite_cohort'] and
        refill['comparison']['total']['reproducible_in_this_finite_cohort'])
    scope=dict(schema='ps5-qwen-prefix-cache128-delivery-v1',active_cache_slots=128,physical_planes=129,
        six_demand_enabled=enabled,prefix_review_SHA256=record(a.prefix_review)['sha256'],
        refill_review_SHA256=record(a.refill_review)['sha256']if a.refill_review else None,
        complete_F32_and_routes_required=True,maximum_requests=9,automatic_retries=0)
    frozen=list({r['path']:r for r in prior['inputs_before']+prefix['inputs_before']+[prior['artifact'],prefix['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Actual compiled dependency changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    original=ROOT/'native/app/resident_additional_policy.h'
    header=original.read_text();needle='||(kind=="prefix"&&slots!=53)'
    if header.count(needle)!=1:raise ValueError('One old isolated prefix geometry selector required')
    (a.out/original.name).write_text(header.replace(needle,''),newline='\n')
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    prefix_command=prefix['compile_commands'][0];prefix_source=Path(prefix_command[prefix_command.index('-c')+1])
    source=a.out/'resident-comparison-prefix-cache128.private.cpp'
    source.write_text(generate(template.read_text(),prefix_source.read_text(),scope),newline='\n')
    # Quoted includes resolve first beside the fresh source. Copy the exact
    # delivery contract so its include also resolves to the widened prefix gate.
    for name in ('resident_refill_policy.h','resident_incremental_tables.h','resident_direct_tables.h'):
        (a.out/name).write_bytes((template.parent/name).read_bytes())
    old=command[command.index('-o')+1];obj=a.out/'prefix-cache128.o'
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(a.out)];command+=['-I',str(template.parent),'-I',str(prefix_source.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']]
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen.extend(record(x)for x in(a.parent,a.prefix_parent,a.prefix_review,Path(__file__),original,template,prefix_source,source,*a.out.glob('*.h')))
    if a.refill_review:frozen.append(record(a.refill_review))
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    host=a.out/'check.cpp';host.write_text('''#include "resident_additional_policy.h"
#include <cassert>
#include <fstream>
int main(int argc,char**argv){
 if(argc==2){std::ifstream f(argv[1]);nlohmann::json p;f>>p;qwen_app::require_resident_additional_policy(p,"prefix");return 0;}
 for(unsigned s:{53u,128u}){auto p=qwen_app::resident_additional_scope("prefix",s);assert(p.at("active_cache_slots")==s&&p.at("maximum_requests")==9);}
 bool refused=false;try{qwen_app::resident_additional_scope("prefix",127);}catch(...){refused=true;}assert(refused);
}
''',newline='\n')
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin';binary=a.out/'check.exe'
    host_env=dict(env,PATH=str(runtime)+os.pathsep+env.get('PATH',''))
    host_command=list(map(str,[runtime/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',a.out,
        '-I',ROOT/'native/app','-I',a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor',host,'-o',binary]))
    for i,c in enumerate((host_command,[str(binary)],command,link)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=host_env)
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen prefix combination dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[command],
        inputs_before=frozen+[record(x)for x in(obj,host,binary)],source_parent=record(a.parent),
        prefix_cache128_combination=dict(scope=scope,actual_entry=record(source),policy_host_check=record(binary),
            all_engine_and_driver_objects_unchanged=True,native_qualification_pending=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['resident_context_reuse']['entry']=record(source)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(prefix_cache128_built=True,six_demand_enabled=enabled,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
