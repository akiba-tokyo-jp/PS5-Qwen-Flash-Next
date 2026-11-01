#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage the exact close helper early; execute it only after terminal admission."""
import argparse,hashlib,importlib.util,json,os,re,secrets,textwrap,time
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def prepare(case):
    script=ROOT/f'.local/close_resident_cohort_{case+4}.py';text=script.read_text()
    text=text[:text.index('    raw=b.lan.execute_once(')]
    left=text.index("    analysis=b.load(CASE/'CPU-calibration-analysis.private.json')")
    right=text.index("    binding=b.load(",left)
    text=text[:left]+'    # Completion is checked by finish before any close execution.\n'+text[right:]
    text=once(text,"current_CPU_completion=b.record(CASE/'CPU-calibration-analysis.private.json'),",
              'completion_must_be_verified_before_execution=True,')
    ns={'__file__':str(script),'__name__':'post_top2_close_build_only'}
    exec(compile(text,str(script)+'#build-only-no-close-call','exec'),ns)
    b,m=ns['b'],ns['m'];out=ns['out'];artifact=ns['artifact'];remote=ns['remote'];journal=ns['journal']
    with b.writer_lease(ns['C']/'model-data-continuation.writer.lock'):
        m.frozen();state=b.current();assert state['native_running']and state['observed_native_pid']==ns['pid']
        proof=b.lan.stage_new(artifact,remote,b.sha(artifact))
        # One measured filesystem block of non-compressible owned padding can
        # be retired for the tiny close journal if later reports exhaust space.
        capacity=b.load(ns['C']/'post-top2-capacity-30824/complete.private.json');block=capacity['block_bytes']
        assert block==65536
        reserve=out/'close-journal-space.private.bin';reserve.write_bytes(os.urandom(block))
        reserve_remote='/data/ai/moss-qwen-close-space-'+secrets.token_hex(16)+'.bin'
        spare=b.lan.stage_new(reserve,reserve_remote,b.sha(reserve))
        b.save(m.CASE/'pre-staged-close.private.json',dict(completed=True,case=case,helper=ns['b'].record(artifact),
            original_intent=b.record(out/'intent.private.json'),original_close_source=b.record(script),
            helper_transfer=proof,remote=remote,journal=journal,reserve_transfer=spare,
            reserve_remote=reserve_remote,reserve_capture=b.record(reserve),expected_PID=ns['pid'],expected_AppID=ns['appid'],
            close_calls=0,completion_admission_still_required=True,automatic_retries=0))
    print('Exact close helper and one journal-space block staged; zero close/GPU calls.')

def finish(case):
    script=ROOT/f'.local/close_resident_cohort_{case+4}.py'
    spec=importlib.util.spec_from_file_location('current_comparison',ROOT/f'.local/resident_cohort_operator_{case}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=m.base;CASE=m.CASE;C=m.C
    with b.writer_lease(C/'model-data-continuation.writer.lock'):
        m.frozen();state=b.current();saved=b.load(CASE/'pre-staged-close.private.json')
        assert saved['completed']and state['native_running']and state['observed_native_pid']==saved['expected_PID']
        b.unchanged(saved['original_close_source']);b.unchanged(saved['original_intent'])
        analysis=b.load(CASE/'CPU-calibration-analysis.private.json')
        assert analysis['completed']and analysis['ordinary_OS_close_authorized']and(
            not analysis['unknown_completion']or analysis['uncertain_resources_retained_for_ordinary_OS_close'])
        artifact=b.unchanged(saved['helper']);pid=saved['expected_PID'];appid=saved['expected_AppID']
        remote=saved['remote'];journal=saved['journal'];out=CASE/'ordinary-close'
        raw=b.lan.web('/fs'+remote,saved['helper']['bytes']+1,8)
        assert len(raw)==saved['helper']['bytes']and hashlib.sha256(raw).hexdigest()==saved['helper']['sha256']
        b.unchanged(saved['reserve_capture'])
        b.save(out/'space-release.once.private.json',dict(remote=saved['reserve_remote'],capture=saved['reserve_capture'],purpose='Bounded close journal'))
        with b.lan.ftplib.FTP()as ftp:
            ftp.connect(b.lan.HOST,2121,timeout=30);ftp.login();reply=ftp.sendcmd('DELE '+saved['reserve_remote']);assert reply.startswith(('226 ','250 '))
        b.lan.absent(saved['reserve_remote'])
        old_stage=b.lan.stage_new
        def reuse(local,target,digest):
            assert Path(local)==artifact and target==remote and digest==saved['helper']['sha256']
            return saved['helper_transfer']
        b.lan.stage_new=reuse
        source=script.read_text();left=source.index('    raw=b.lan.execute_once(');right=source.index('\nprint(',left)
        context=dict(globals());context.update(locals())
        try:exec(compile(textwrap.dedent(source[left:right]),str(script)+'#pre-staged-first-execution','exec'),context,context)
        finally:b.lan.stage_new=old_stage
    print('Pre-staged helper completed its first guarded ordinary close; no helper upload was needed.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','finish'));p.add_argument('--case',type=int,required=True)
    a=p.parse_args()
    if a.case<31500 or a.case%100:raise ValueError('Fresh post-Top2 case required')
    globals()[a.mode](a.case)

if __name__=='__main__':main()
