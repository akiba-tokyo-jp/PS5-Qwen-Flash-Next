#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price isolated PLE phases from closed cases; never admit or run a console case."""
import argparse,hashlib,json,re
from pathlib import Path

CPU_PHASES=('main_entered','SELF_integrity_completed','CPU_shader_completed','CPU_source_owner_completed')
GPU_PHASES=('before_GPU_initialization','GPU_completed')

def uint(value,name,maximum=(1<<64)-1):
    if type(value)is not int or not 0<=value<=maximum:raise ValueError('Invalid '+name)
    return value

def price(cases,variation_pages=256):
    if type(variation_pages)is not int or variation_pages<256:raise ValueError('The separate variation allowance must not be reduced')
    if not isinstance(cases,list)or not cases:raise ValueError('Completed isolated cases required')
    identity=None;cpu_requirement=0;gpu_requirement=0;details=[];observed_GPU=False
    for case in cases:
        if set(case)!={'label','SELF_sha256','policy','admission','result','owner','completion','restoration'}:
            raise ValueError('Exact closed-case evidence required')
        digest=case['SELF_sha256']
        if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Exact SELF required')
        if identity is not None and identity!=digest:raise ValueError('Different executables cannot share startup pricing')
        identity=digest;scope=case['policy']['native_PLE_slice_validation'];binding=case['policy']['native_isolated_PLE_title']
        pin=(scope['driver_revision'],scope['profile'],scope['native_archive_sha256'])
        if pin!=('872cc1264ad8ba5d6b888b092968fa5858a38c58','cumulative-idle','b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925'):
            raise ValueError('Qualified unchanged driver required')
        if binding['candidate_SELF_sha256']!=digest or binding['model_loading_enabled']is not False or scope['persistent_caches_enabled']is not False:
            raise ValueError('Isolated execution scope changed')
        result=case['result'];restored=case['restoration'];completion=case['completion']
        if completion.get('completed')is not True or restored.get('completed')is not True or restored.get('unknown_completion')is not False or restored.get('native_owners')!=0:
            raise ValueError('Positive completion and restored idle evidence required')
        if type(result.get('pid'))is not int or result['pid']<=0 or result['pid']!=case['owner'].get('pid')or result.get('model_loaded')is not False:
            raise ValueError('Matching exact native owner required')
        cpu=result.get('schema')=='ps5-qwen-isolated-PLE-CPU-calibration-v2'
        gpu=result.get('schema') in('ps5-qwen-PLE-slice-smoke-v1','ps5-qwen-PLE-slice-paired-fixture-v2')
        if not(cpu or gpu)or binding['CPU_only_startup_calibration']is not cpu:raise ValueError('Unknown phase scope')
        if cpu:
            if result.get('all_started_CPU_operations_returned')is not True or result.get('GPU_graphs')!=0 or result.get('GPU_initializations')!=0 or result.get('source_owner_prepared')is not True:
                raise ValueError('Incomplete CPU preparation')
        elif result.get('positive_device_idle_and_epoch_retirement')is not True or result.get('all_F32_outputs_bit_exact')is not True or result.get('F64_reference_passed')is not True:
            raise ValueError('Incomplete GPU numerical or lifecycle evidence')
        samples=case['admission'].get('observations')
        if case['admission'].get('completed')is not True or not isinstance(samples,list)or len(samples)!=10:
            raise ValueError('Ten preceding observations required')
        before=[]
        for row in samples:
            if any(row.get(k)!=v for k,v in dict(minimum=898,reserved=206,page_bytes=16384,native_startup_target=2974,full_prelaunch_required=10142).items()):
                raise ValueError('Memory domains or original floors changed')
            before.extend([uint(row['free_first'],'prelaunch free'),uint(row['free_last'],'prelaunch free')])
        # Use the upper observation bound to avoid understating the decline.
        start=max(before);observations=result['observations']if cpu else result['isolated_title_memory_observations']
        expected=CPU_PHASES+(()if cpu else GPU_PHASES)
        if not isinstance(observations,list)or tuple(r['phase']for r in observations)!=expected:
            raise ValueError('Every ordered phase must be present exactly once')
        requirements=[]
        for row in observations:
            free=uint(row['kernel_free_pages'],'phase free');vm=row['VM']
            if vm['free']!=free or row['kernel_startup_target_pages']!=2974 or row['CPU_heap_libc_fallbacks']!=0:
                raise ValueError('Phase admission or heap ownership differs')
            if row['CPU_heap_mapped_bytes']!=16<<20 or row['CPU_heap_peak_bytes']!=16<<20 or uint(row['Flexible_available_bytes'],'Flexible')<64<<20:
                raise ValueError('This price is restricted to the measured isolated heap and pools')
            floor=2974 if row['phase']=='before_GPU_initialization'else 1154
            if free<floor:raise ValueError('A phase failed its existing floor')
            decline=max(0,start-free);required=decline+floor+variation_pages
            cpu_requirement=max(cpu_requirement,required if row['phase'] in CPU_PHASES else 0)
            if row['phase']=='CPU_source_owner_completed':gpu_requirement=max(gpu_requirement,decline+2974+variation_pages)
            requirements.append(dict(phase=row['phase'],free_pages=free,observed_decline_pages=decline,phase_floor_pages=floor,priced_pages=required))
        observed_GPU|=gpu
        details.append(dict(label=case['label'],prelaunch_minimum_pages=min(before),prelaunch_maximum_pages=start,phases=requirements))
    return dict(schema='ps5-qwen-isolated-PLE-phase-price-v1',SELF_sha256=identity,cases=details,
        variation_pages=variation_pages,CPU_phase_requirement_pages=cpu_requirement,GPU_startup_requirement_pages=gpu_requirement,
        proposed_future_prelaunch_pages=max(cpu_requirement,gpu_requirement),physical_GPU_completion_in_inputs=observed_GPU,
        GPU_startup_target_pages=2974,operational_floor_pages=1154,regular_full_model_prelaunch_pages=10142,
        physical_hardware_minimum_established=False,fresh_admission_granted=False,console_operations=0,production_adopted=False)

def load_case(case,admission):
    files=dict(package=case/'candidate-package.private.json',policy=case/'private-policy/development.json',
        admission=case/admission,result=case/'native-result.private.json',owner=case/'native-owner.private.json',
        completion=case/'native-positive-completion.private.json',restoration=case/'restored-complete.private.json')
    values={};inputs=[]
    for name,path in files.items():
        raw=path.read_bytes();values[name]=json.loads(raw)
        inputs.append(dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    result=dict(label=case.name,SELF_sha256=values.pop('package')['SELF']['sha256'],**values)
    return result,inputs

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',nargs=2,action='append',metavar=('DIRECTORY','ADMISSION_FILE'),required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();cases=[];inputs=[]
    for folder,admission in a.case:
        case,rows=load_case(Path(folder),admission);cases.append(case);inputs+=rows
    result=price(cases);result['inputs']=inputs
    with a.out.open('x',encoding='utf-8',newline='\n')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('cases','inputs','SELF_sha256')}))
if __name__=='__main__':main()
