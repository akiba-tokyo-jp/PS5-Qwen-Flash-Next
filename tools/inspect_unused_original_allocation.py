#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Diagnose a retired zero-write reclaim refusal using metadata only."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from start_success_route import load, need, save
from success_case_control import build, current_files, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'prior', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    previous = load(a.prior / 'native/result.private.json')
    intent = load(a.prior / 'intent.private.json')
    plan = load(a.prior / 'native/plan.private.json')
    state = load(a.current / 'active-console.private.json')
    need(not previous['completed'] and previous['operation_calls'] == 0 and
         previous['helper_exited'] and previous['helper_files_removed'] and
         state['original_restored'] and not state['native_running'] and
         not state['model_loaded'] and not state['unknown_completion'] and
         state['source_publication_owner']['phase'].startswith('disk-full'),
         'Only a retired zero-write refusal with idle restored P1 may be diagnosed')
    need(intent['selected'] == current_files(a.current), 'The selected P1 must remain exact')
    a.out.mkdir(parents=True, exist_ok=False)
    context = '#include <sys/stat.h>\n'
    context += 'static const char*live[]={' + ','.join(map(json.dumps, intent['existing_live_files'])) + '};\n'
    context += 'static const char*targets[]={' + ','.join(json.dumps(r['path']) for r in intent['candidates']) + '};\n'
    context += r'''
static int case_retire_completed_images(int*calls){
 (void)calls;unsigned failures=0;
 for(unsigned i=0;i<sizeof(live)/sizeof(live[0]);++i){struct stat s={0};errno=0;
  int rc=lstat(live[i],&s),saved=errno;
  if(rc||!S_ISREG(s.st_mode)){++failures;
   if(!report("ALLOCATION_LIVE_REFUSAL index=%u rc=%d errno=%d mode=%u",i,rc,saved,(unsigned)s.st_mode))return 0;}}
 for(unsigned i=0;i<sizeof(targets)/sizeof(targets[0]);++i){struct stat s={0};errno=0;
  int rc=lstat(targets[i],&s),saved=errno;
  if(!report("ALLOCATION_TARGET index=%u rc=%d errno=%d mode=%u nlink=%llu bytes=%lld blocks=%lld blocksize=%u",
   i,rc,saved,(unsigned)s.st_mode,(unsigned long long)s.st_nlink,(long long)s.st_size,(long long)s.st_blocks,(unsigned)s.st_blksize))return 0;
 }
 return report("ALLOCATION_INSPECTION_COMPLETE protected_failures=%u data_writes=0",failures);
}
'''
    prepared = build(a.workspace, plan['original_mount_plan']['path'], intent['selected'], intent['selected'], [],
                     'retire-completed-images', a.out / 'native', completed_images_context=context,
                     CPU_metadata_extra_pages=64)
    need('ftruncate' not in prepared['imports'], 'This diagnostic must contain no truncation API')
    save(a.out / 'intent.private.json', dict(prior=record(a.prior / 'intent.private.json'),
         native_plan=record(a.out / 'native/plan.private.json'), metadata_only=True, data_writes=0))
    result = completed_operation(lan_module(), prepared, a.out / 'native')
    raw = Path(result['raw']['path']).read_text()
    rows = [dict(zip(('index', 'rc', 'errno', 'mode', 'nlink', 'bytes', 'blocks', 'blocksize'), map(int, m)))
            for m in re.findall(r'ALLOCATION_TARGET index=(\d+) rc=(-?\d+) errno=(\d+) mode=(\d+) nlink=(\d+) bytes=(-?\d+) blocks=(-?\d+) blocksize=(\d+)', raw)]
    need(result['completed'] and len(rows) == len(intent['candidates']) and result['operation_calls'] == 0,
         'The complete metadata-only diagnostic must retire positively')
    save(a.out / 'result.private.json', dict(completed=True, native=result, targets=rows,
         protected_refusals=re.findall(r'ALLOCATION_LIVE_REFUSAL[^\n]+', raw), data_writes=0))
    print(json.dumps(dict(completed=True, targets=len(rows), protected_refusals=raw.count('ALLOCATION_LIVE_REFUSAL'),
          allocation_classes=sorted(set((r['bytes'], r['blocks'], r['blocksize']) for r in rows)), data_writes=0)))


if __name__ == '__main__':
    main()
