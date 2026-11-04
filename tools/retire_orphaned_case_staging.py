#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove two exact inactive publication images without reading their payloads."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from compact_case_integrity_markers import compact
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import build, current_files, lan_module

NAMES = ('moss-qwen-case-fe989b2aa1475fafab4b23bb3ebb8ffb-candidate-SELF.bin',
         'moss-qwen-case-f1b8779ce545ff273ef1a935fc135669-candidate-SELF.bin')
SIZE = 27033600
MODES = ('-rw-r--r--', '-r--r--r--')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'inventory', 'compact-marker-control', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--protected-plan', type=Path, action='append', required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    args = parser.parse_args()
    found = {}
    for line in args.inventory.read_text(encoding='utf-8').splitlines():
        fields = line.split(maxsplit=8)
        if len(fields) == 9 and fields[8] in NAMES:
            need(fields[:5] == [MODES[NAMES.index(fields[8])], '1', '0', '0', str(SIZE)],
                 'Bind exact root-owned regular staging images from the completed readonly inventory')
            found[fields[8]] = line
    need(set(found) == set(NAMES), 'Both exact unselected staging names must appear in the inventory')
    references = [args.current / name for name in ('deployment.private.json', 'qwen-runtime/app.json',
        'qwen-runtime/development.json', 'provenance/current-package.private.json',
        'provenance/model-source-plan.private.json', 'provenance/protected-model-source-plan.private.json',
        'provenance/required-bundle-inputs.private.json')]
    references += args.protected_plan
    need(all(all(name not in path.read_text(encoding='utf-8') for name in NAMES) for path in references),
         'A current or future model references a staging image; retain it')
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('source_publication_owner') and
         not state.get('CPU_source_seal_owner') and not state.get('GPU_retirement_readmission_pending'),
         'Only positive idle ownership permits this exact new cleanup scope')
    selected = current_files(args.current)
    targets = ['/data/ai/' + name for name in NAMES]
    need(not set(targets).intersection(row['remote'] for row in selected), 'Never retire selected application files')
    facts = dict(targets=targets, expected_bytes=SIZE, selected=selected, boot=state['current_boot'],
                 expected_modes=['0100644', '0100444'],
                 inventory=record(args.inventory), protected_plans=[record(path) for path in references],
                 source=record(Path(__file__)), recursive_operations=0, model_source_files_removed=0,
                 orphaned_unselected_payloads_not_authenticated_as_model_sources=True)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        context = 'static const char*staged[]={' + ','.join(map(json.dumps, targets)) + '};\n'
        context += r'''
static unsigned staging_free(void){unsigned value=0;size_t size=4;return !sysctlbyname("vm.stats.vm0.v_free_count",&value,&size,0,0)&&size==4?value:0;}
static int staging_exact(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&
 a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_nlink==b->st_nlink&&a->st_size==b->st_size&&
 a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
 a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
static int case_retire_completed_images(int*calls){
 struct stat initial[2];const unsigned modes[2]={0100644,0100444};const unsigned free_before=staging_free();
 for(unsigned i=0;i<2;++i){struct stat*s=initial+i;
  if(lstat(staged[i],s)||!S_ISREG(s->st_mode)||s->st_mode!=modes[i]||s->st_uid||s->st_gid||s->st_nlink!=1||s->st_size!=27033600)return 0;
  if(!report("ORPHAN_STAGING_ADMITTED index=%u inode=%llu bytes=%llu payload_reads=0",i,(unsigned long long)s->st_ino,(unsigned long long)s->st_size))return 0;
 }
 for(unsigned i=0;i<2;++i){struct stat opened,named,after;int fd=open(staged[i],O_RDONLY|O_NOFOLLOW);if(fd<0)return 0;
  int exact=!fstat(fd,&opened)&&staging_exact(&opened,initial+i);const int closed=!close(fd);
  if(!exact||!closed||lstat(staged[i],&named)||!staging_exact(&named,initial+i))return 0;
  if(!report("BEFORE ORPHAN_STAGING_UNLINK index=%u descriptor_closed=1 identity_exact=1",i))return 0;
  ++*calls;errno=0;int rc=unlink(staged[i]),saved=errno;int absent=lstat(staged[i],&after)==-1&&errno==ENOENT;
  if(!report("RETURN ORPHAN_STAGING_UNLINK index=%u rc=%d error=%d absent=%d",i,rc,saved,absent)||rc||!absent)return 0;
 }
 return report("ORPHAN_STAGING_COMPLETE files=2 bytes=54067200 free_before=%u free_after=%u source_writes=0 payload_reads=0 model_floor=7374",free_before,staging_free());
}
'''
        plan = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                     args.out / 'native', completed_images_context=context)
        compact(plan, args.out / 'native', args.compact_marker_control)
        save(args.out / 'intent.private.json', dict(facts, native_plan=record(args.out / 'native/plan.private.json')))
        print(json.dumps(dict(prepared=True, exact_images=2, bytes=2 * SIZE, PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(all(intent[key] == value for key, value in facts.items()) and
         intent['native_plan'] == record(args.out / 'native/plan.private.json'), 'The exact cleanup admission changed')
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], phase='retire-orphaned-staging-images',
        GPU_calls=0, title_launches=0, ordinary_helper_completion_pending=True)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    native = completed_operation(lan_module(), load(args.out / 'native/plan.private.json'), args.out / 'native')
    raw = Path(native['raw']['path']).read_bytes()
    found = re.findall(rb'ORPHAN_STAGING_COMPLETE files=2 bytes=54067200 free_before=(\d+) free_after=(\d+) source_writes=0 payload_reads=0 model_floor=7374', raw)
    need(native['completed'] and native['helper_exited'] and native['helper_files_removed'] and
         native['operation_calls'] == 2 and len(found) == 1, 'Both exact unlink operations, helper and current-seven hashes must finish positively')
    save(args.out / 'result.private.json', dict(completed=True, native=native, retired_files=2, retired_bytes=2 * SIZE,
        free_before=int(found[0][0]), free_after=int(found[0][1]), source_payload_reads=0,
        all_selected_and_pending_sources_preserved=True, current_seven_native_hashes_unchanged=True,
        model_readiness_pages_unchanged=7374, exclusive_RAM_gain_claimed=False))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'], 'Never clear another helper owner')
    state.pop('CPU_source_seal_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, retired_files=2, free_before=int(found[0][0]),
                          free_after=int(found[0][1]), model_readiness_pages=7374)), flush=True)


if __name__ == '__main__':
    main()
