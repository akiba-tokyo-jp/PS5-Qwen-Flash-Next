#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reclaim exact unused PS5 chunks while retaining authenticated PC originals."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import struct

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, lan_module

ROOT = PHYSICAL + '/qwen-runtime/model'
CHUNK = 512 << 20


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'protected', 'listing', 'original-receipt', 'paused-publication', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    parser.add_argument('--allocation-diagnosis', type=Path, required=True)
    args = parser.parse_args()
    state = load(args.current / 'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner') and
         state['source_publication_owner']['plan'] == record(args.paused_publication / 'plan.private.json') and
         state['source_publication_owner']['phase'].startswith('disk-full') and
         not (args.paused_publication / 'native/execution/execution.once.private.json').exists(),
         'Only a retired disk-full source writer with exact restored P1 may permit this cleanup')
    original = load(args.original_receipt)
    need(original['original_shards_verified'] and not original['learned_inference_performed'],
         'The authenticated complete PC BF16 source must remain retained')
    protected = set(load(args.protected))
    selected = current_files(args.current)
    protected.update(row['remote'] for row in selected)
    targets, originals = [], {}
    for line in args.listing.read_text(encoding='utf-8').splitlines():
        fields = line.split(maxsplit=8)
        if len(fields) != 9 or not fields[0].startswith('-') or fields[1] != '1' or fields[4] != str(CHUNK):
            continue
        name = fields[8]
        match = re.fullmatch(r'(qwen-flash-next-bf16-\d{5}-of-00076\.gguf)\.part-([1-9][0-9]*)', name)
        if not match:
            continue
        path = ROOT + '/' + name
        if path in protected:
            continue
        source = next((row for row in original['files'] if PurePosixPath(row['path']).name == match[1]), None)
        need(source is not None, 'Every exact historical chunk must have an authenticated PC original')
        local = args.original_receipt.parent / source['path']
        info = local.stat()
        need(local.is_file() and info.st_size == source['bytes'], 'The complete authenticated PC source must remain available')
        if (int(match[2]) + 1) * CHUNK > source['bytes']:
            continue
        originals[str(local)] = dict(source, local=str(local), inode=info.st_ino, mtime_ns=info.st_mtime_ns)
        targets.append(dict(path=path, bytes=CHUNK, original=str(local), original_chunk=int(match[2])))
    need(52 <= len(targets) <= 713 and all(row['path'] not in protected for row in targets),
         'A bounded pool of unreferenced chunks outside all live and prepared maps is required')
    # Validate only existing protected files natively; future publication names
    # remain part of the PC exclusion set but have not been created yet.
    physical = load(args.current / 'provenance/protected-model-source-plan.private.json')['physical']
    source_plan = load(args.current / 'provenance/model-source-plan.private.json')
    required = load(args.current / 'provenance/required-bundle-inputs.private.json')['rows']
    live = {PHYSICAL + row['path'][5:] for row in physical + source_plan['physical'] + source_plan['backing'] + required}
    live.update(row['remote'] for row in selected)
    need(live.issubset(protected), 'Every actual current file and required bundle must remain excluded')
    diagnosis = load(args.allocation_diagnosis)
    prior_intent = load(Path(load(args.allocation_diagnosis.parent / 'intent.private.json')['prior']['path']))
    need(diagnosis['completed'] and diagnosis['data_writes'] == 0 and not diagnosis['protected_refusals'] and
         prior_intent['candidates'] == targets and prior_intent['existing_live_files'] == sorted(live) and
         len(diagnosis['targets']) == len(targets) and
         all(r['rc'] == 0 and r['nlink'] == 1 and r['bytes'] == CHUNK and
             r['blocks'] == (CHUNK + 65536) // 512 and r['blocksize'] == 65536
             for r in diagnosis['targets']),
         'The completed metadata-only diagnosis must bind the exact64KiB allocation overhead and protected scope')
    intent = dict(candidates=targets, maximum_truncations=52, protected=sorted(protected), existing_live_files=sorted(live),
        authenticated_PC_originals=list(originals.values()), original_receipt=record(args.original_receipt),
        listing=record(args.listing), exclusion=record(args.protected), selected=selected,
        allocation_diagnosis=record(args.allocation_diagnosis), observed_allocation_overhead_bytes=65536,
        planned_logical_bytes=52 * CHUNK, minimum_allocated_reclaim_bytes=24 << 30,
        data_operations='ftruncate only; directory entries and required source files unchanged',
        source_parent_directory_entries_preserved=True, GPU_calls=0, title_launches=0, initializer_requests=0)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        context = '#include <sys/stat.h>\n#include <unistd.h>\n'
        context += 'static const char*reclaim_paths[]={' + ','.join(json.dumps(row['path']) for row in targets) + '};\n'
        context += 'static const char*reclaim_protected[]={' + ','.join(map(json.dumps, sorted(live))) + '};\n'
        context += r'''
#define RECLAIM_COUNT (sizeof(reclaim_paths)/sizeof(reclaim_paths[0]))
#define RECLAIM_TARGET_COUNT 52u
#define RECLAIM_PROTECTED_COUNT (sizeof(reclaim_protected)/sizeof(reclaim_protected[0]))
static struct stat reclaim_target_before[RECLAIM_COUNT],reclaim_live_before[RECLAIM_PROTECTED_COUNT];
static unsigned reclaim_selected[RECLAIM_TARGET_COUNT];
static int reclaim_same(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&
 a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&
 a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
 a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
static int case_retire_completed_images(int*calls){
 uint64_t allocated=0;unsigned selected=0;
 for(unsigned i=0;i<RECLAIM_PROTECTED_COUNT;++i){struct stat*s=reclaim_live_before+i;
  if(lstat(reclaim_protected[i],s)||!S_ISREG(s->st_mode))return 0;}
 for(unsigned i=0;i<RECLAIM_COUNT;++i){struct stat*s=reclaim_target_before+i;
  if(lstat(reclaim_paths[i],s)||!S_ISREG(s->st_mode)||s->st_nlink!=1||s->st_size!=UINT64_C(536870912)||s->st_blocks<0)return 0;
  const uint64_t bytes=(uint64_t)s->st_blocks*512;
  if(bytes!=UINT64_C(536936448)||s->st_blksize!=65536){
   report("RECLAIM_REFUSED index=%u allocated_bytes=%llu blocksize=%u",i,(unsigned long long)bytes,(unsigned)s->st_blksize);return 0;}
  for(unsigned j=0;j<RECLAIM_PROTECTED_COUNT;++j)if(s->st_dev==reclaim_live_before[j].st_dev&&s->st_ino==reclaim_live_before[j].st_ino)return 0;
  if(bytes>=UINT64_C(536870912)&&selected<RECLAIM_TARGET_COUNT){reclaim_selected[selected++]=i;allocated+=bytes;}
 }
 if(!report("RECLAIM_ADMITTED candidates=%u selected=%u protected=%u allocated_bytes=%llu source_writes_before_admission=0",
  (unsigned)RECLAIM_COUNT,selected,(unsigned)RECLAIM_PROTECTED_COUNT,(unsigned long long)allocated)||
  selected!=RECLAIM_TARGET_COUNT||allocated<UINT64_C(25769803776))return 0;
 for(unsigned ordinal=0;ordinal<RECLAIM_TARGET_COUNT;++ordinal){const unsigned i=reclaim_selected[ordinal];
  struct stat before={0},after={0},named={0};int fd=open(reclaim_paths[i],O_WRONLY|O_NOFOLLOW);if(fd<0)return 0;
  if(fstat(fd,&before)||!reclaim_same(&before,reclaim_target_before+i)){close(fd);return 0;}
  const int truncated=!ftruncate(fd,0),synced=truncated&&!fsync(fd);++*calls;
  const int verified=synced&&!fstat(fd,&after)&&after.st_size==0&&after.st_blocks==0&&
   after.st_dev==before.st_dev&&after.st_ino==before.st_ino&&after.st_mode==before.st_mode&&
   after.st_uid==before.st_uid&&after.st_gid==before.st_gid&&after.st_nlink==1;
  const int closed=!close(fd),bound=!lstat(reclaim_paths[i],&named)&&reclaim_same(&after,&named);
  if(!report("RECLAIM_CHUNK index=%u truncated=%d synced=%d verified=%d closed=%d bound=%d before_allocated=%llu",
   i,truncated,synced,verified,closed,bound,(unsigned long long)before.st_blocks*512)||!verified||!closed||!bound)return 0;
 }
 for(unsigned i=0;i<RECLAIM_PROTECTED_COUNT;++i){struct stat s;
  if(lstat(reclaim_protected[i],&s)||!reclaim_same(&s,reclaim_live_before+i))return 0;}
 return report("RECLAIM_COMPLETE files=52 allocated_bytes_released=%llu all_protected_identities_unchanged=1 PC_originals_retained=1 GPU_calls=0 title_launches=0",
  (unsigned long long)allocated);
}
'''
        plan = build(args.workspace, args.mount_plan, selected, selected, [], 'retire-completed-images',
                     args.out / 'native', completed_images_context=context, CPU_metadata_extra_pages=64)
        image = Path(plan['artifact']['path']).read_bytes()
        offset = struct.unpack_from('<Q', image, 32)[0]
        stride, count = struct.unpack_from('<HH', image, 54)
        headers = [struct.unpack_from('<IIQQQQQQ', image, offset + i * stride) for i in range(count)]
        need(stride == 56 and sum((h[6] + 16383) // 16384 for h in headers if h[0] == 1) <= 64,
             'The entire static helper must fit inside the additional64-page CPU allowance')
        save(args.out / 'intent.private.json', intent)
        print(json.dumps(dict(prepared=True, candidate_chunks=len(targets), maximum_truncations=52, logical_bytes=52 * CHUNK,
                              minimum_allocated_reclaim=24 << 30, PS5_operations=0)))
        return
    need(load(args.out / 'intent.private.json') == intent, 'The exact prepared cleanup scope changed')
    plan = load(args.out / 'native/plan.private.json')
    need(not (args.out / 'native/execution/execution.once.private.json').exists(), 'Never repeat a consumed retirement')
    result = completed_operation(lan_module(), plan, args.out / 'native')
    raw = Path(result['raw']['path']).read_bytes()
    need(result['completed'] and result['operation_calls'] == 52 and
         raw.count(b'RECLAIM_CHUNK index=') == 52 and b'RECLAIM_COMPLETE files=52 ' in raw,
         'Every exact truncation, positive close and unchanged protected identity must complete')
    save(args.out / 'result.private.json', dict(completed=True, native=result, truncated_unused_chunks=52,
        logical_bytes_released=52 * CHUNK, actual_allocation_release_verified=True,
        all_current_and_prepared_sources_preserved=True, authenticated_PC_originals_preserved=True,
        directory_entries_preserved=True, GPU_calls=0, title_launches=0, initializer_requests=0))
    print(json.dumps(dict(completed=True, unused_chunks_retired=52, logical_bytes_released=52 * CHUNK)))


if __name__ == '__main__':
    main()
