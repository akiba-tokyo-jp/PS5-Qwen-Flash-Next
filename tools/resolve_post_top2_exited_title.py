#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resolve only the exact exited title through its current OS registration."""
import argparse,importlib.util,json,re,secrets,subprocess,time
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
ABSENT=r'''
static int exited_title_state(unsigned phase){
 struct {uint64_t a;struct kinfo_proc value;uint64_t b;}g;memset(&g,0,sizeof(g));g.a=g.b=GUARD;
 size_t bytes=sizeof(g.value);int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,EXPECTED_PID};errno=0;
 int rc=sysctl(mib,4,&g.value,&bytes,NULL,0),saved=errno;
 int absent=g.a==GUARD&&g.b==GUARD&&((!rc&&!bytes)||(rc&&saved==ESRCH));
 int lookup=sceSystemServiceGetAppId("PPSA99190"),big=sceSystemServiceGetAppIdOfRunningBigApp();
 if(!report("EXITED_TITLE phase=%u PID=%d rc=%d errno=%d bytes=%zu canaries=%d PID_absent=%d lookup=%d BigApp=%d expected=%u",phase,EXPECTED_PID,rc,saved,bytes,g.a==GUARD&&g.b==GUARD,absent,lookup,big,EXPECTED_APP_ID)||!absent)return 0;
 if(lookup<=0&&big!=(int)EXPECTED_APP_ID)return 1;
 if(lookup!=(int)EXPECTED_APP_ID||big!=(int)EXPECTED_APP_ID)return 0;
 struct {uint64_t a;char text[32];uint64_t b;}t={GUARD,{0},GUARD};rc=sceLncUtilGetAppTitleId(EXPECTED_APP_ID,t.text);
 if(rc||t.a!=GUARD||t.b!=GUARD||!memchr(t.text,0,sizeof(t.text))||strcmp(t.text,"PPSA99190"))return 0;
 return 2;
}
int main(int argc,char**argv){(void)argv;int calls=0,accepted=0,resolved=0,rc=-1;
 output_fd=open(JOURNAL,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(output_fd<0)return 3;output_selected=1;
 if(!report("ENTRY scope=exact_exited_title_resolution nonce=%s PID=%d AppID=%u EBADF_fallback=%d GPU_calls=0 manual_GPU_release=0 Unix_signals=0",CLOSE_NONCE,EXPECTED_PID,EXPECTED_APP_ID,fallback_used))return 1;
 if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1))goto done;
 int first=exited_title_state(1);if(!first||!context(2))goto done;int second=exited_title_state(2);if(first!=second)goto done;
 if(second==1){resolved=1;goto done;}
 if(!report("BEFORE normal_OS_KillApp exact_orphan_AppID=%u PID_absent=1 calls_max=1 GPU_idle_claimed=0",EXPECTED_APP_ID))goto done;
 calls=1;rc=sceSystemServiceKillApp(EXPECTED_APP_ID,-1,0,0);accepted=rc==0;
 if(!report("RETURN normal_OS_KillApp rc=0x%08x accepted=%d",(unsigned)rc,accepted))goto done;
 if(accepted)for(unsigned i=0;i<10;++i){if(exited_title_state(3+i)==1){resolved=1;break;}usleep(100000);}
 done:if(!report("END nonce=%s resolved=%d normal_close_calls=%d normal_close_accepted=%d log_healthy=%d GPU_calls=0 automatic_retry=0 GPU_cleanup_claimed=0",CLOSE_NONCE,resolved,calls,accepted,healthy))resolved=0;
 return resolved&&healthy?0:1;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args();spec=importlib.util.spec_from_file_location('operator',ROOT/f'.local/resident_cohort_operator_{a.case}.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o);b=o.base;case=o.CASE;old=case/'ordinary-close';saved=b.load(case/'pre-staged-close.private.json');recipe=b.load(old/'intent.private.json')
 with b.writer_lease(o.C/'model-data-continuation.writer.lock'):
  o.frozen();state=b.current();require(state['native_running']and state['observed_native_pid']==saved['expected_PID']and not any(x['name']=='eboot.bin'for x in b.processes()),'Exact disappeared original native owner required');require(not(old/'execution.once.private.json').exists(),'Original close must be unused')
  out=case/'exited-title-resolution-v2';out.mkdir(exist_ok=False);(out/'tmp').mkdir();nonce=secrets.token_hex(16);journal='/data/ai/moss-qwen-exited-title-'+nonce+'.log';header=(old/'close_context.h').read_text();header,count=re.subn(r'(#define CLOSE_NONCE )"[0-9a-f]+"',lambda m:m[1]+json.dumps(nonce),header);require(count==1,'One fresh close nonce required');(out/'close_context.h').write_text(header,newline='\n')
  source=(old/'normal-close-admitted-owner.c').read_text();source=source[:source.index('int main(int argc,char **argv)')]+ABSENT.replace('JOURNAL',json.dumps(journal));source=source.replace('static int owner(unsigned phase)','__attribute__((unused)) static int owner(unsigned phase)').replace('static int admit_current_owner_start(void)','__attribute__((unused)) static int admit_current_owner_start(void)');cfile=out/'exited-title.c';cfile.write_text(source,newline='\n');commands=[[arg.replace(str(old),str(out))for arg in c]for c in recipe['commands']]
  for c in commands:
   if '-c'in c:c[c.index('-c')+1]=str(cfile)
  for i,c in enumerate(commands):
   r=subprocess.run(c,capture_output=True,timeout=90);(out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-1200:])
  artifact=out/Path(recipe['artifact']['path']).name;remote='/data/ai/moss-qwen-exited-title-'+nonce+'.elf';write_json(out/'manifest.private.json',dict(nonce=nonce,artifact=record(artifact),commands=commands,inputs=[record(cfile),record(out/'close_context.h'),record(__file__)],remote=remote,journal=journal,expected_PID=saved['expected_PID'],expected_AppID=saved['expected_AppID'],normal_close_calls_max=1,GPU_calls=0))
  raw=b.lan.execute_once(str(artifact),b.sha(artifact),'',remote,journal,out/'execution',45);text=raw.decode(errors='replace');require(('END nonce='+nonce+' resolved=1 ')in text and 'GPU_cleanup_claimed=0'in text,'Positive exact exited-title resolution required')
  require(not any(x['name']=='eboot.bin'for x in b.processes()),'No new native process may exist');b.update(state='native_exited_exact_OS_title_resolved',native_running=False,gateway_running=False,model_loaded=False,native_owners=0,original_native_process_exited=True,OS_title_resolution=str(out/'manifest.private.json'))
  stages=(case/'post-exit-startup.private.txt').read_bytes();completed=stages.count(b'resident_comparison_arm_completed_positive_request_reset')+stages.count(b'resident_additional_arm_completed_positive_request_reset')
  write_json(old/'complete.private.json',dict(completed=True,normal_OS_close_accepted='normal_close_accepted=1'in text,normal_OS_orphan_resolved=True,native_eboot_count=0,automatic_process_exit=True,source=record(out/'execution/console.private.log'),GPU_completion_not_inferred=True))
  write_json(case/'CPU-calibration-analysis.private.json',dict(completed=True,all_declared_comparisons_completed=False,ordinary_OS_close_authorized=True,OS_title_resolved=True,model_requests_completed=completed,GPU_initializations=1,all_resources_positively_retired=False,unknown_completion=True,uncertain_resources_retained_for_ordinary_OS_close=True,source=record(case/'post-exit-startup.private.txt')))
  original=ROOT/f'.local/restore_resident_cohort_{a.case+5}.py';restore=ROOT/f'.local/restore_exited_resident_cohort_{a.case+5}.py';s=once(original.read_text(),"closed['normal_OS_close_accepted']","closed['normal_OS_orphan_resolved']");s=s.replace('CPU_title_normally_closed=True','native_process_exit_and_OS_title_resolution_confirmed=True').replace('after the bounded model comparison and ordinary OS close','after automatic native exit and exact OS title resolution');require(not restore.exists(),'Fresh exit-restoration script required');restore.write_text(s,newline='\n')
  print(json.dumps(dict(exact_exited_title_resolved=True,normal_OS_close_called='normal_close_calls=1'in text,native_process_absent=True,GPU_idle_not_claimed=True,restore_script=str(restore))))
if __name__=='__main__':main()
