#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Seal already transferred sources once after an explicit unsubmitted-helper handoff."""
import argparse
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
from build_performance_quantizer import record
from publish_iq2_up_model_overlay import finish
from start_success_route import load,need,save
from success_case_control import complete,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','publication','sealer','transfer-proof'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--submit',action='store_true');p.add_argument('--collect',action='store_true')
    a=p.parse_args();need(a.submit!=a.collect,'Choose exactly one submission or same-helper collection')
    publication=load(a.publication/'plan.private.json');handoff_path=a.sealer/'pre-submission-handoff.private.json'
    handoff=load(handoff_path);plan_path=a.sealer/'plan.private.json';plan=load(plan_path)
    need(handoff['completed'] and handoff['old_plan']==record(a.publication/'native/plan.private.json') and
         handoff['replacement_plan']==record(plan_path) and handoff['old_native_submissions']==0 and
         plan['operation']=='seal-shared-Q4' and plan['whole_integrity_window_bytes']==262144 and
         plan['CPU_metadata_margin_pages']==97 and not plan['CPU_control_independent_thresholds'] and
         plan['minimum_live_free_pages']==1201 and plan['full_physical_alias_SHA256_EOF_unchanged'],
         'The exact unsubmitted-helper handoff and stronger qualified window are required')
    old=load(a.publication/'native/plan.private.json');backup=Path(handoff['quarantined_path'])
    need(not(a.publication/'native/execution/execution.once.private.json').exists() and
         not Path(old['artifact']['path']).exists() and
         all(record(backup)[k]==old['artifact'][k] for k in ('bytes','sha256')),
         'The old local helper must remain quarantined and never submitted')
    transfer=load(a.transfer_proof);rows=sorted(transfer['rows'],key=lambda r:r['uploaded_file'])
    need(transfer['complete'] and transfer['exit_code']==1 and transfer['expected_quarantined_helper_error'] and
         [r['uploaded_file'] for r in rows]==list(range(1,len(publication['files'])+1)) and
         all(r['total']==len(rows) and r['bytes']==f['local']['bytes'] for r,f in zip(rows,publication['files'])),
         'Every original positive whole-file store and the expected pre-submission host exit are required')
    need(plan['old_files']==plan['new_files']==old['old_files']==old['new_files']==current_files(a.current),
         'The selected current seven files must remain exact')
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'],'One positively restored source-only owner required')
    once=a.sealer/'execution/execution.once.private.json';result_path=a.sealer/'result.private.json'
    result=load(result_path) if result_path.exists() else None
    if a.submit:
        need(not once.exists() and result is None,'Never repeat the native sealing submission')
        save(a.sealer/'transfer-handoff.private.json',dict(completed=True,transfer=record(a.transfer_proof),
            publication=record(a.publication/'plan.private.json'),handoff=record(handoff_path),
            payload_retransmissions=0,old_native_submissions=0,new_native_submissions=1))
        state['CPU_source_seal_owner']=dict(plan=record(plan_path),publication=str(a.publication),
            GPU_calls=0,title_launches=0,ordinary_helper_completion_pending=True)
        state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
        try:
            result=execute(lan_module(),plan,a.sealer,observation_seconds=1)
        except RuntimeError:
            need(once.exists() and not result_path.exists(),'Only the same submitted helper may be collected')
            print(json.dumps(dict(submitted_once=True,collection_pending=True,payload_retransmissions=0,
                first_quiet_collection_after_seconds=350,PS5_GPU_calls=0)),flush=True)
            return
    elif result is None:
        need(once.exists(),'Collection cannot submit a helper')
        lan=lan_module()
        try:raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20,8)
        except urllib.error.HTTPError as error:
            need(error.code==404,'Same-helper observation failed; no replay')
            print(json.dumps(dict(completed=False,same_helper_pending=True,native_resubmissions=0)));return
        if not re.search(rb'\nEND success=\d+ operation_calls=\d+ app_id=-?\d+ log_healthy=\d+ GPU_calls=0 initializer_requests=0 mount_calls=0\n$',raw):
            print(json.dumps(dict(completed=False,same_helper_pending=True,journal_bytes=len(raw),native_resubmissions=0)));return
        log=a.sealer/'completed-console.private.log';log.write_bytes(raw)
        result=complete(lan,plan,a.sealer,raw,log)
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and
         result['GPU_calls']==result['initializer_requests']==result['mount_calls']==0,
         'Positive complete source sealing and helper retirement are required before model admission')
    if not(a.publication/'result.private.json').exists():
        finish(a.publication,Path(publication['preparation']['path']),publication,result,
            native_result_path=result_path,source_handoff=a.sealer/'transfer-handoff.private.json')
    owner=state.get('CPU_source_seal_owner')
    if owner:
        need(owner['plan']==record(plan_path),'Another source owner must not be cleared')
        state.pop('CPU_source_seal_owner');state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    publication_owner=state.get('source_publication_owner')
    if publication_owner:
        need(publication_owner['plan']==record(a.publication/'plan.private.json'),'Another publication owner must not be cleared')
        state.pop('source_publication_owner');state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,native_submissions=1,payload_retransmissions=0,
        full_physical_alias_SHA256_EOF=True,positive_helper_retirement=True,PS5_GPU_calls=0)))


if __name__=='__main__':
    main()
