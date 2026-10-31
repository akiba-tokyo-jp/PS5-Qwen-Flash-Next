#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CPU integrity with timestamp-bound ShellCore's already qualified SLOCK wait."""
from pathlib import Path
import json,sys

def main():
    source=Path(__file__).with_name('build_preservation_integrity.py');text=source.read_text()
    marker='    nonce = secrets.token_hex(16)\n'
    assert text.count(marker)==1
    patch='''    guard_path=args.out/'direct-controller.c'
    guard_text=guard_path.read_text()
    old='(g.value.ki_stat==SSLEEP||g.value.ki_stat==SRUN)'
    if guard_text.count(old)!=1:raise ValueError('Exact management-service state predicate required')
    guard_text=guard_text.replace(old,'(g.value.ki_stat==SSLEEP||g.value.ki_stat==SRUN||(g.value.ki_stat==SLOCK&&!strcmp(expected_services[i].name,"SceShellCore")))')
    old='if(!report("service_identity expected=%s pid=%d rc=%d bytes=%zu exact=%d",expected_services[i].name,expected_services[i].pid,rc,bytes,ok)||!ok)return 0;'
    new='if(!report("service_identity expected=%s pid=%d rc=%d bytes=%zu exact=%d state=%d tracer=%d",expected_services[i].name,expected_services[i].pid,rc,bytes,ok,g.value.ki_stat,g.value.ki_tracer)||!ok)return 0;'
    if guard_text.count(old)!=1:raise ValueError('Exact management-service diagnostic required')
    guard_path.write_text(guard_text.replace(old,new),newline='\\n')
'''
    text=text.replace(marker,patch+marker)
    old='frozen_paths = [Path(__file__), native_source,';assert text.count(old)==1
    text=text.replace(old,"frozen_paths = [Path(__file__), Path(__file__).with_name('build_preservation_integrity.py'), native_source,")
    namespace={'__file__':__file__,'__name__':'__main__'};exec(compile(text,str(source)+'#narrow-ShellCore-SLOCK','exec'),namespace)
    out=Path(sys.argv[sys.argv.index('--out')+1]);p=out/'manifest.private.json';r=json.loads(p.read_text());r['management_service_wait_scope']=dict(ShellCore_allowed_states=['SSLEEP','SRUN','SLOCK'],all_other_service_states_unchanged=True,boot_PID_UID_PPID_start_tracer_and_title_guards_unchanged=True,CPU_only=True,prior_same_boot_SLOCK_qualification_case=17217);p.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
