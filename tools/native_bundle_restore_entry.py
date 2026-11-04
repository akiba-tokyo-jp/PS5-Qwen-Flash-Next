# SPDX-License-Identifier: MIT
"""Compose the successful native CPU bootstrap with tracked serial copy storage."""
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need
from success_case_control import PHYSICAL

ROOT=Path(__file__).resolve().parents[1]


def compose(entry,bundle_plan,model_proof,out):
    plan=load(bundle_plan);proof=load(model_proof);out=Path(out)
    need(plan['completed'] and plan['quantization_changes']==0 and proof['completed'] and
         proof['complete_unchanged_file_metadata']==518 and proof['double_directory_snapshot_equal'],
         'Exact original copy plan and current-boot native identities required')
    need(record(plan['header']['path'])==plan['header'],'Original copy spans changed')
    canonical=proof['canonical_directory'][0];device=proof['application_directory'][0]
    need(canonical!=device and all(r['identity'][0]==canonical for r in plan['sources']),
         'Exact qualified canonical-to-title nullfs device pair required')
    header=Path(plan['header']['path']).read_text().replace(PHYSICAL,'/app0')
    old='{'+str(canonical)+'ULL,'
    need(header.count(old)==len(plan['sources']),'Only the source device components may translate')
    (out/'expert_q2_bundle_probe_plan.h').write_text(header,encoding='utf-8',newline='\n')
    native=ROOT/'native/qwen_flash_next/expert_q2_bundle_pack.cpp';text=native.read_text()
    replacements=[('constexpr size_t owned_bytes=8u<<20;','constexpr size_t owned_bytes=4u<<20;'),
        ('readback=scratch+(4u<<20);','readback=scratch;'),
        ('window_bytes=8388608','window_bytes=4194304'),
        ('int64_t physical=-1;',''),
        ('need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU Direct allocation failed");\n    if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||uintptr_t(owned)%16384)retain();mapped=true;',
         'need(!posix_memalign(&owned,16384,owned_bytes)&&owned&&ps5_heap_owns(owned),"Bounded tracked native CPU heap required");mapped=true;'),
        ('if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();',
         'if(mapped){free(owned);owned=nullptr;if(!split_report_line("CPU_COPY_SCRATCH tracked_free_returned=1 no_live_allocation=1 arena_backing_retained_until_OS_close=1"))retain();}else if(owned)retain();')]
    for old,new in replacements:
        need(text.count(old)==1,'Exact successful serial pack ownership boundary required')
        text=text.replace(old,new,1)
    # The successful native application uses open/fstat descriptors. Root-payload
    # statfs qualification does not qualify that API in the native title.
    old='Key path_key(const char*p){struct stat s{};need(!lstat(p,&s)&&S_ISREG(s.st_mode),"Sealed regular source missing");return key(s);}'
    new='''Key path_key(const char*p){struct stat s{};const int fd=open(p,O_RDONLY|O_NOFOLLOW);
    need(fd>=0,"Sealed native source descriptor missing");const bool valid=!fstat(fd,&s)&&S_ISREG(s.st_mode);
    const bool closed=!close(fd);need(valid&&closed,"Stable native source descriptor required");return key(s);}'''
    need(text.count(old)==1,'One original named-inode observation required');text=text.replace(old,new,1)
    start=text.index('    struct statfs capacity{};');end=text.index('    need(!posix_memalign(',start)
    text=text[:start]+'    line("CAPACITY bound_by_fresh_external_root_observation=1 native_statfs_calls=0");\n'+text[end:]
    need(text.count('==p.identity')==4,'All four original complete source identity comparisons required')
    text=text.replace('==p.identity','==required_bundle_source_identity(p.identity)')
    marker='line("SEALED bytes="+std::to_string(bundle_probe_file_bytes)+" SHA256="+hex(whole)+'
    need(text.count(marker)==1,'One original completed readback seal required')
    text=text.replace(marker,'const auto restored_digest=hex(whole);need(restored_digest=='+json.dumps(plan['expected_SHA256'])+',"Restored complete original bundle digest differs");\n    line("SEALED bytes="+std::to_string(bundle_probe_file_bytes)+" SHA256="+restored_digest+',1)
    text='extern "C" int qwen_bundle_payload_main(int,char**);\n#define main qwen_bundle_payload_main\n'+text+'\n#undef main\n'
    pack=out/'required-bundle-packer.inc';pack.write_text(text,encoding='utf-8',newline='\n')
    scope=dict(schema='ps5-qwen-required-bundle-native-CPU-restore-v1',kind=plan['kind'],
        path='/app0'+plan['output'][len(PHYSICAL):],bytes=plan['output_bytes'],sha256=plan['expected_SHA256'],
        input_plan_sha256=record(bundle_plan)['sha256'],tracked_CPU_heap_bytes=4<<20,source_workers=0,GPU_calls=0,
        model_loads=0,quantization_changes=0,source_writes=0,automatic_retries=0)
    context='#define REQUIRED_BUNDLE_BOOT_SECONDS '+str(proof['current_boot'][0])+'LL\n'
    context+='#define REQUIRED_BUNDLE_BOOT_MICROSECONDS '+str(proof['current_boot'][1])+'LL\n'
    context+='#define REQUIRED_BUNDLE_SOURCE_DEVICE '+str(canonical)+'ULL\n'
    context+='#include "required_bundle_restore_cpu.h"\n#include "required-bundle-packer.inc"\n'
    marker='int main(int argc,char **argv) {';need(entry.count(marker)==1,'One native CPU entry required')
    entry=entry.replace(marker,context+'\n'+marker,1)
    marker='        const auto &gate=policy.at("native_first_generation_validation");'
    need(entry.count(marker)==1,'One native CPU policy entry required')
    entry=entry.replace(marker,marker+'\n        if(policy.at("native_required_bundle_restore")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact original native CPU copy scope required");',1)
    marker='        qwen_native_stage("mini_shader_bootstrap_CPU_completed_GPU_not_started_waiting_for_ordinary_close");'
    need(entry.count(marker)==1,'One positive native CPU completion boundary required')
    body='''        required_bundle_native_PID=getpid();struct stat native_title_anchor{};
        required_bundle_native_anchor=startup.model_receipt;
        const int native_anchor=open(required_bundle_native_anchor.c_str(),O_RDONLY|O_NOFOLLOW);
        if(native_anchor<0)throw std::runtime_error("Verified native receipt anchor could not reopen");
        const bool anchor_valid=!fstat(native_anchor,&native_title_anchor)&&S_ISREG(native_title_anchor.st_mode)&&native_title_anchor.st_dev;
        const int anchor_closed=close(native_anchor);
        if(!anchor_valid||anchor_closed)throw std::runtime_error("Current verified native receipt descriptor required");
        required_bundle_native_device=static_cast<std::uint64_t>(native_title_anchor.st_dev);
        qwen_native_stage("required_bundle_native_CPU_copy_before_original_packer");
        if(qwen_bundle_payload_main(1,nullptr))throw std::runtime_error("Required native CPU bundle copy returned a known refusal");
        require_model_CPU_budget();struct stat restored{};
        const int completed_output=open(bundle_probe_path,O_RDONLY|O_NOFOLLOW);
        if(completed_output<0)throw std::runtime_error("Completed original bundle descriptor unavailable");
        const bool completed_identity=!fstat(completed_output,&restored)&&S_ISREG(restored.st_mode)&&
            (restored.st_mode&07777)==0444&&restored.st_size==static_cast<off_t>(bundle_probe_file_bytes);
        const int completed_closed=close(completed_output);
        if(!completed_identity||completed_closed)throw std::runtime_error("Completed original bundle inode unavailable");
        Json restored_identity=Json::array({static_cast<std::uint64_t>(restored.st_dev),static_cast<std::uint64_t>(restored.st_ino),
            static_cast<std::uint64_t>(restored.st_mode),static_cast<std::uint64_t>(restored.st_uid),static_cast<std::uint64_t>(restored.st_gid),
            static_cast<std::uint64_t>(restored.st_size),static_cast<std::uint64_t>(restored.st_mtim.tv_sec),static_cast<std::uint64_t>(restored.st_mtim.tv_nsec),
            static_cast<std::uint64_t>(restored.st_ctim.tv_sec),static_cast<std::uint64_t>(restored.st_ctim.tv_nsec)});
        write_fresh_report(startup.admission_report+".required-bundle",{{"schema","ps5-qwen-required-bundle-native-CPU-result-v1"},
            {"completed",true},{"pid",getpid()},{"run_id",run},{"scope",policy.at("native_required_bundle_restore")},
            {"full_original_SHA256_and_EOF_readback",true},{"identity",restored_identity},{"tracked_CPU_heap_free_returned",true},
            {"all_started_input_calls_returned",true},{"source_payloads_unchanged",true},{"GPU_calls",0},{"model_loaded",false}});
'''
    entry=entry.replace(marker,body+marker,1)
    need('sceKernelAllocateDirectMemory(' not in text and 'sceKernelReleaseDirectMemory(' not in text,
         'Only the already tracked native CPU heap may own restoration scratch')
    need('lstat(' not in text and 'statfs(' not in text,'Native title must use the qualified descriptor ABI and external capacity observation')
    details=dict(scope=scope,bundle_plan=record(bundle_plan),current_model_proof=record(model_proof),
        same_nullfs_device_translation_only=True,canonical_device=canonical,root_alias_device=device,
        native_device_must_be_sampled_from_current_verified_receipt=True,
        all_nine_other_source_identity_fields_preserved=True,CPU_heap_includes_copy_storage=True)
    inputs=[record(p) for p in (Path(__file__),native,ROOT/'native/app/required_bundle_restore_cpu.h',
        out/'expert_q2_bundle_probe_plan.h',pack,bundle_plan,model_proof)]
    return entry,details,inputs
