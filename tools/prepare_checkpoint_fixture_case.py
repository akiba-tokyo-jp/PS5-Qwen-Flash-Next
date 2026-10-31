#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate fresh private CPU/launch/close scripts for the checkpoint fixture."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COLLECT=r'''
def collect():
    plan=base.load(CASE/'prepared-launch.private.json');remote=plan['management_admission_report'];deadline=time.monotonic()+900;next_print=0
    while True:
        try:raw=base.lan.web('/fs'+remote,8<<20,8);report=json.loads(raw);break
        except base.lan.urllib.error.HTTPError as e:assert e.code==404
        for suffix in('.failure','.fatal'):
            try:
                failed=base.lan.web('/fs'+remote+suffix,1<<20,8)
                (CASE/('checkpoint'+suffix+'.private.json')).write_bytes(failed)
                raise RuntimeError('Checkpoint fixture returned failure; retain ownership and explicit failure evidence')
            except base.lan.urllib.error.HTTPError as e:assert e.code==404
        if time.monotonic()>=next_print:
            pid=base.current()['observed_native_pid'];assert any(x['pid']==pid and x['name']=='eboot.bin'for x in base.processes())
            progress=base.lan.web('/fs'+journal_remote(pid),8<<20,8);lines=progress.decode(errors='replace').splitlines()
            print(json.dumps(dict(checkpoint_fixture_running=True,stage=lines[-1]if lines else'pending',stage_bytes=len(progress))),flush=True);next_print=time.monotonic()+30
        assert time.monotonic()<deadline,'Finite fixture deadline; do not retry the GPU launch'
        time.sleep(2)
    (CASE/'native-model-terminal.private.json').write_bytes(raw);binding=base.load(CASE/'case-inputs.private.json')['binding'];state=base.current()
    assert report['schema']=='ps5-qwen-checkpoint-device-fixture-result-v1'and report['completed']
    assert report['pid']==state['observed_native_pid']and report['run_id']==binding['run_id']and report['candidate_SELF_sha256']==binding['candidate_SELF_sha256']
    assert report['requests']==[]and not report['model_loaded']and report['HTTP_requests']==report['VideoOut_starts']==0
    assert report['device_ledger_live_bytes']==0 and report['all_model_source_device_owners_positively_retired']and report['all_owners_positively_retired']
    assert report['save_restore_events']==60 and report['full_checked_bytes']==12*7*(121049088+8192)
    assert report['all_payload_bytes_and_canaries_exact']and report['mode_reset_to_original']and len(report['blocks'])==12
    assert [v['mode']for v in report['blocks']]==[0,1,1,0,0,3,3,0,1,2,2,1]
    for row in report['blocks']:
        assert row['all_payload_bytes_and_canaries_exact']and row['same_count_different_chunking_exact']and row['different_count_chunking_exact']and row['distinct_source_buffers_checked']
        assert len(row['samples'])==5
        if row['mode']in(1,2):assert row['counter_delta'][0]>0 and row['counter_delta'][1]>0
        if row['mode']in(2,3):assert row['counter_delta'][2]>0 and row['counter_delta'][3]>=49
    pid=state['observed_native_pid'];stages=base.lan.web('/fs'+journal_remote(pid),8<<20,8);(CASE/'current-startup-for-owner.private.txt').write_bytes(stages)
    assert b'checkpoint_device_fixture_complete_waiting_for_ordinary_close'in stages
    base.save(CASE/'CPU-terminal-owner-basis.private.json',dict(live_owner_start_and_AppInfo_must_be_admitted_by_normal_close=True,
        expected_PID=pid,owner_start_and_AppInfo_observation_deferred_to_qualified_normal_close=True))
    base.save(CASE/'CPU-calibration-analysis.private.json',dict(completed=True,model_requests_completed=0,GPU_initializations=1,
        all_resources_positively_retired=True,ordinary_OS_close_authorized=True,unknown_completion=False,
        native_terminal=base.record(CASE/'native-model-terminal.private.json')))
    print(json.dumps(dict(checkpoint_fixture_completed=True,save_restore_events=60,full_bytes_exact=True,device_live_bytes=0,unknown_completion=False)),flush=True)
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);p.add_argument('--build-name',required=True);p.add_argument('--package-name',required=True);p.add_argument('--fixture-kind',choices=['checkpoint','gdn-conv-norm'],default='checkpoint');a=p.parse_args()
 if a.case<14200 or a.case%100:raise ValueError('A fresh hundred-aligned case namespace is required')
 def shift(s):return re.sub(r'(?<![0-9])130\d{2}(?![0-9])',lambda m:str(int(m[0])-13000+a.case),s)
 names=['prepared_phase_model_13000.private.py','resident_cohort_operator_13000.py','first_operator_13000_base.py','close_resident_cohort_13004.py','restore_resident_cohort_13005.py','build_resident_owner_13003.py','collect_Q2_monitor_13000.py']
 for name in names:
  src=ROOT/'.local'/name;text=shift(src.read_text());dest=ROOT/'.local'/shift(name)
  text=text.replace('Limit-candidates-SELF-12968',a.package_name).replace('Limit-candidates-12964/core-safety.private.json',a.build_name+'/core-safety.private.json')
  if name.startswith('prepared_'):
   old="policy['native_limit_margin_probe']=actual_native['limit_margin_probe']['scope']"
   fixture_policy="policy['native_checkpoint_device_fixture']=actual_native['checkpoint_device_fixture']['scope']"if a.fixture_kind=='checkpoint'else"policy['native_GDN_conv_normalization_fixture']=actual_native['GDN_conv_normalization_fixture']['scope']"
   text=text.replace(old,old+";policy['native_strata_cache_comparison']=actual_native['strata_cache_comparison']['scope'];"+fixture_policy)
   text=text.replace('maximum_generation_requests=16','maximum_generation_requests=0')
   start=text.index("scope='544 additional");end=text.index("',\n",start)
   description='Actual pinned device checkpoint writer and reader; zero model loads and zero generation/HTTP/display requests;60 save-restore events in12 A-B-B-A blocks; original/descriptor-and-high-water/batch-only/combined modes; full121MB byte patterns and canaries, distinct source buffers and changed chunking; original shaders, physical reserves, OS minimum and positive completion retained; no reboot or retry'
   if a.fixture_kind=='gdn-conv-norm':description='Four full-shape convolution normalization cases and144 GPU graphs; zero model loads and generation/HTTP/display requests; full F64 recurrent state, unwritten snapshots, raw source history, weights and canaries; zero/epsilon-dominated heads and original two-token fallback; one additional immutable shader with full SHA256 before Vulkan; every original shader/registry/lease, physical reserve, OS minimum and positive completion retained; no reboot or retry'
   text=text[:start]+'scope='+repr(description)+text[end+1:]
  elif name.startswith('resident_cohort_operator_'):
   text=text.replace('maximum_generation_requests=16','maximum_generation_requests=0')
   collector=COLLECT
   if a.fixture_kind=='gdn-conv-norm':
    collector=collector.replace('ps5-qwen-checkpoint-device-fixture-result-v1','ps5-qwen-GDN-conv-normalization-fixture-result-v1').replace('checkpoint_fixture_running','GDN_conv_normalization_fixture_running')
    collector=collector.replace("and report['all_owners_positively_retired']",'')
    left=collector.index("    assert report['save_restore_events']");right=collector.index("    pid=state",left)
    collector=collector[:left]+'''    assert report['GPU_graphs']==144 and len(report['cases'])==4 and report['F64_reference_all_outputs_passed']
    assert report['additional_shader_verified']==1 and report['additional_shader_modules']>0
    for ordinal,row in enumerate(report['cases']):
        assert row['F64_reference_all_outputs_passed']and row['maximum_absolute_error']<=1e-6 and row['snapshot_unwritten_slots_preserved']and row['canary_passed']
        assert row['original_source_history_and_weights_exact']and row['positive_buffer_context_backend_retirement']
        assert row['eligible_fused_shape']==(ordinal<3)and (row['candidate_pipeline_selections']>0 if ordinal<3 else row['candidate_pipeline_selections']==0)
        assert len(row['arms'])==4 and all(len(arm['backend_samples_us'])==len(arm['completion_samples_us'])==8 for arm in row['arms'])
'''+collector[right:]
    collector=collector.replace('checkpoint_device_fixture_complete_waiting_for_ordinary_close','GDN_conv_normalization_fixture_complete_waiting_for_ordinary_close')
    collector=collector.replace('checkpoint_fixture_completed=True,save_restore_events=60,full_bytes_exact=True','GDN_conv_normalization_fixture_completed=True,GPU_graphs=144,full_state_F64_passed=True')
   start=text.index('def collect():\n');end=text.index('\ndef main():',start);text=text[:start]+collector+'\n'+text[end:]
  elif name.startswith('first_operator_'):
   text=text.replace('lan.web("/fs" + row["remote"], 1 << 20, 8)','lan.web("/fs" + row["remote"], 8 << 20, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["old"]','lan.web("/fs" + row["target"], row["old"]["bytes"]+1, 8)).hexdigest() == row["old"]')
   text=text.replace('lan.web("/fs" + row["backup"], 1 << 20, 8)','lan.web("/fs" + row["backup"], row["old"]["bytes"]+1, 8)')
   text=text.replace('lan.web("/fs" + row["target"], 1 << 20, 8)).hexdigest() == row["new"]','lan.web("/fs" + row["target"], row["new"]["bytes"]+1, 8)).hexdigest() == row["new"]')
  elif name.startswith('restore_'):
   text=text.replace("op.lan.web('/fs'+path,1<<20,12)","op.lan.web('/fs'+path,capture['bytes']+1,12)")
  ast.parse(text)
  if dest.exists():raise FileExistsError(dest)
  dest.write_text(text,newline='\n')
  # Every old output namespace must be gone before the first console operation.
  if re.search(r'(?<![0-9])130\d{2}(?![0-9])',text):raise ValueError('Stale operation namespace remains')
 print('Fresh finite checkpoint fixture scripts generated; no console calls.')
if __name__=='__main__':main()
