#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently review the finite split-backing report, not model speed/adoption."""
import argparse,json,math,re
from pathlib import Path
from build_preservation_integrity import record
PACK_SHA='4d6247378c577a586d8cc552b14c771f63a732f8b9762ead8405612aea2d371d'
# These are original pack zero, group zero. Host scope checks independently
# compare the application's complete matrix table with the qualified pack plan.
HASHES=(
 ('d078e826bc9af5874b09a11d72da5afd1ef0ea526c92afb0823c21b2343ccf94','a7860aefe9ada5e7abc8f7ee60208534dd382779a1670e06e4f5981d70750078'),
 ('9d5c49abe64e05751aafa4f9db91682c77a71fee414f09dfc08a605961e847ce','93d0b3f9b5cb7161388be0b6b8292395b1ce3d101e09aef4ab9d46252850b776'),
 ('ae84d1de690d0a627967c7b8a108062428605b2a111105e4ec689ddef16842dc','2c5ce2fdbaf299e0ce254332ade85ea280aeb47136e497b090afa4d27f87701a'),
 ('bc51fe9700a6c80b16f6a131aa358d55f1a67cb533436517f41a66d9b4d97418','0ff87036f608eb3c96d09355432c1eaf87aad5591a404ce8e73dd68c9671d25a'),
 ('31f2e953692f1784b76a50761146b28394f0a768f5f0e0da3ff55aa374660ddc','9c473d2fbc2a25045c5db2fcf1bcd70c21002983773b14de7570a55faf75368b'),
 ('a5949679890a798b9df50a2c1c77a75475b0ec6efcea3de02f39eaeac9e98656','f62d473879d8a482e03f3d5cece08d06cacd3b13ed5d0a94e55175ed5ada23af'))
PHASES=('main_entered','SELF_integrity_completed','CPU_shader_completed','before_source_and_GPU_scope','GPU_scope_completed')

def require(good,message):
    if not good:raise ValueError(message)
def integer(value,low,high):return type(value)is int and low<=value<=high
def finite(value,high):return type(value)in(int,float)and math.isfinite(value)and 0<=value<=high

def validate_report(report,binding,expected_pid,*,ready_numerical=False,original_source=False):
    r=report;b=binding
    require(type(r)is dict and type(b)is dict and integer(expected_pid,1,0x7fffffff),'Bound report, title and expected owner required')
    require(not original_source or ready_numerical,'Original-source scope requires the preceding numerical gate')
    workers=2 if original_source else int(ready_numerical)
    require(b.get('schema')=='ps5-qwen-isolated-split-bank-title-v1'and
        isinstance(b.get('run_id'),str)and re.fullmatch('[0-9a-f]{32}',b['run_id'])and
        isinstance(b.get('candidate_SELF_sha256'),str)and re.fullmatch('[0-9a-f]{64}',b['candidate_SELF_sha256'])and
        integer(b.get('candidate_SELF_bytes'),1,32<<20)and b.get('model_loading_enabled')is False and type(b.get('source_workers'))is int and b['source_workers']==workers,
        'Exact original predeclared isolated title binding required')
    require(r.get('schema')=='ps5-qwen-split-bank-result-v1'and type(r.get('pid'))is int and r['pid']==expected_pid and
        r.get('run_id')==b['run_id']and r.get('candidate_SELF_sha256')==b['candidate_SELF_sha256'],'Native owner/run/SELF identity differs')
    for key,value in dict(mapped_Direct_read_calls=6,GPU_graphs=12,independent_actual_VkDeviceMemory_groups=2,
        contiguous_roles_per_actual_group=3,nested_strong_backing_leases=6,conservative_cache_charge_bytes=512<<20,
        device_ledger_live_bytes=0,source_workers=workers,automatic_retries=0).items():
        require(type(r.get(key))is int and r[key]==value,'Finite split-backing count differs: '+key)
    for key in('original_pack_SHA256_checked','all_original_raw_and_envelope_SHA256_checked','positive_resource_retirement',
        'all_started_IO_closed','positive_device_idle_and_epoch_retirement','current_complete_shader_file_SHA256_checked',
        'all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned'):
        require(r.get(key)is True,'Missing positive completion: '+key)
    for key in('model_loaded','GPU_IO_overlap_tested','generation_speed_measured'):require(r.get(key)is False,'Fixture scope changed: '+key)
    require(r.get('source_pack_sha256')==PACK_SHA and integer(r.get('non_BF16_exact_F32_input_values'),1,100000),
        'Original BF16 pack and non-BF16-exact F32 inputs required')
    require(integer(r.get('device_ledger_peak_bytes'),512<<20,1792<<20),'Device allocation price exceeds its retained ledger')
    require(integer(r.get('shader_module_inputs'),1,8192),'Actual original shader inputs required')
    require(integer(r.get('Direct_available_before_GPU'),1<<30,16<<30)and integer(r.get('Flexible_available_before_GPU'),64<<20,16<<30),
        'Actual Direct/Flexible setup headroom required')
    require(r.get('kernel_startup_target_pages')==2974 and integer(r.get('kernel_free_after_CPU_source_before_GPU'),2974,1000000),
        'Unchanged native startup admission must follow CPU source preparation')
    cases=r.get('cases');require(type(cases)is list and len(cases)==6,'Exactly six original matrices required')
    maximum=normalized=0.0
    for index,c in enumerate(cases):
        require(type(c)is dict,'Native matrix case required');group,role=divmod(index,3)
        for key,value in dict(group=group,role=role,global_slot=52 if group else 0,local_slot=26 if group else 0,
            columns=640 if role==2 else 2560,rows=2560 if role==2 else 640,residue=1632 if role==2 else 2784,GPU_graphs=2).items():
            require(type(c.get(key))is int and c[key]==value,'Original split case geometry differs: '+key)
        raw,envelope=HASHES[role*2+group]
        require(c.get('original_raw_sha256')==raw and c.get('original_envelope_sha256')==envelope,'Original matrix byte identity differs')
        for key in('F64_reference_passed','same_F32_outputs_bit_exact','whole_envelope_unchanged_after_GPU'):require(c.get(key)is True,'Numerical or byte invariant failed')
        require(c.get('preceding_canary_checked')is bool(group)and c.get('following_canary_checked')is (not bool(group)),
            'Canary coverage must respect each actual allocation boundary')
        require(c.get('reference_absolute_tolerance')==1e-5 and c.get('reference_relative_tolerance')==1e-5,'Numerical tolerances changed')
        require(finite(c.get('maximum_absolute_error'),1e30)and finite(c.get('maximum_normalized_error'),1),'Nonfinite or failed F64 reference')
        maximum=max(maximum,c['maximum_absolute_error']);normalized=max(normalized,c['maximum_normalized_error'])
    require(finite(r.get('maximum_absolute_error'),1e30)and r['maximum_absolute_error']==maximum and
        finite(r.get('maximum_normalized_error'),1)and r['maximum_normalized_error']==normalized,'Numerical summary differs from its cases')
    memory=r.get('memory_observations');require(type(memory)is list and len(memory)==len(PHASES),'Every isolated title memory boundary required')
    for row,phase in zip(memory,PHASES):
        require(type(row)is dict and row.get('phase')==phase,'Memory phases are incomplete or reordered')
        require(integer(row.get('CPU_heap_mapped_bytes'),1,512<<20)and integer(row.get('CPU_heap_peak_bytes'),row['CPU_heap_mapped_bytes'],512<<20)and
            type(row.get('CPU_heap_libc_fallbacks'))is int and row['CPU_heap_libc_fallbacks']==0,'Untracked or over-budget CPU heap')
        require(integer(row.get('kernel_free_pages'),0,1000000)and row.get('kernel_startup_target_pages')==2974,'Original kernel VM boundary required')
    return dict(native_report_scope_passed=True,original_matrices=6,GPU_graphs=12,
        independent_backing_groups=2,ordinary_OS_close_and_restore_review_required=True,
        physical_GPU_IO_overlap_qualified=False,model_speed_qualified=False,production_adopted=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('report','policy','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-pid',type=int,required=True);a=p.parse_args()
    inputs=[record(a.report),record(a.policy)];r=json.loads(a.report.read_bytes());policy=json.loads(a.policy.read_bytes())
    result=validate_report(r,policy['native_isolated_split_bank_title'],a.expected_pid)
    require(inputs==[record(a.report),record(a.policy)],'Review inputs changed')
    result.update(schema='ps5-qwen-split-bank-review-v1',inputs=inputs)
    with a.out.open('x',encoding='utf-8',newline='\n')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
