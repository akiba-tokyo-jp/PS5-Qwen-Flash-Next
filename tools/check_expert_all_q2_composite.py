#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the all-Q2 source parser with clearly non-deployable metadata controls."""
import argparse,copy,hashlib,json,os,subprocess
from pathlib import Path
from expert_q4 import LOCK,record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('workspace','cache','plan','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);plan=json.loads(a.plan.read_text());mixed_path=Path(plan['mixed_receipt']['path']);seal_path=Path(plan['mixed_seal']['path']);mixed=json.loads(mixed_path.read_text());oldseal=json.loads(seal_path.read_text());root='/app0/'+Path(plan['new_directory']).name
 require(record(mixed_path)==plan['mixed_receipt']and record(seal_path)==plan['mixed_seal'],'Actual retained mixed metadata changed')
 inode=2000000;dev=oldseal['directory_identity'][0]
 def key(n,mode=0o100644):
  nonlocal inode
  inode+=1;return[dev,inode,mode,0,0,n,1793240000,0,1793240000,0]
 digest=lambda s:hashlib.sha256(('METADATA-ONLY-NOT-FOR-DEPLOYMENT:'+s).encode()).hexdigest()
 model=dict(schema='ps5-qwen-expert-all-q2-model-v1',completed=True,Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',Down_encoding='signed_FP16_scale_MSE_fit',original_revision=plan['original_revision'],upstream_revision=plan['upstream_revision'],original_receipt_sha256=plan['original_receipt_sha256'],original_BF16_receipt=plan['original_BF16_receipt'],all_Experts_retained=True,non_Expert_payload_bytes_preserved=True,activation_quantization=False,KV_quantization=False,host_model_inference=False,packed_composite_sources=True,files=copy.deepcopy(plan['files']),tensors=copy.deepcopy(plan['tensors']),mapped_file_bytes=plan['mapped_file_bytes'],retained_mixed_source_seal=record(seal_path),retained_mixed_model_receipt=record(mixed_path),Down_files=[])
 downproof=[]
 for i in range(49):
  name='blk.'+str(i)+'.ffn_down_exps.weight';row=dict(name=name,layer=i,path='down-'+str(i)+'.q2_0',bytes=235929600,sha256=digest(name),original_payload_sha256=digest('original:'+name));model['Down_files'].append(row);downproof.append(dict(path=root+'/'+row['path'],bytes=row['bytes'],sha256=row['sha256'],identity=key(row['bytes'])))
 for t in model['tensors']:
  if t['type']=='Q2_0':t['payload_sha256']=model['Down_files'][int(t['name'].split('.')[1])]['sha256']
 files=[]
 for f in model['files']:
  if f['reused_original']:files.append(copy.deepcopy(next(x for x in oldseal['logical_files']if x['path']==f['path'])));continue
  f['sha256']=digest(f['path']);f['parts']=[dict(path=f['path'],offset=0,bytes=f['header_bytes'],sha256=digest('header:'+f['path']),identity=key(f['header_bytes']))];s=copy.deepcopy(f);s.pop('regions');s['parts'][0]['path']=root+'/'+f['path'];files.append(s)
 mp=a.out/'metadata-control-not-for-deployment.private.json';write_json(mp,model);bound=record(mp)
 seal=dict(schema='ps5-qwen-expert-all-q2-native-source-integrity-v1',model_receipt_sha256=bound['sha256'],source_directory=root,canonical_source_directory='/data/ai/native-moss-image-sft/PPSA99190'+root[5:],logical_bytes=plan['mapped_file_bytes'],Down_encoding='signed_FP16_scale_MSE_fit',same_existing_title_nullfs_namespace=True,all_new_parts_complete_Direct_SHA256_readback=True,all_parts_unchanged_since_readback=True,CPU_owners_positively_closed=True,original_BF16_Q4_and_mixed_sources_unchanged=True,Gate_Up_and_non_Expert_payloads_byte_exact=True,source_writes=0,GPU_calls=0,automatic_retries=0,permission_changes=0,mount_changes=0,model_loaded=False,directory_identity=key(65536,0o40755),receipt_identity=key(bound['bytes']),backing_metadata=[dict(identity=key(record(seal_path)['bytes']))],Down_files=downproof,logical_files=files,verification_elapsed_ms=1)
 raw=json.dumps(seal,indent=2)+'\n';gate=dict(model_receipt_sha256=bound['sha256'],model_receipt_bytes=bound['bytes'],Expert_all_Q2_source_integrity=dict(schema='ps5-qwen-expert-all-q2-source-policy-v1',raw=raw,sha256=hashlib.sha256(raw.encode()).hexdigest()));gp=a.out/'metadata-control-gate.private.json';write_json(gp,gate)
 host=a.workspace/'toolchain/msys-clang64/clang64/bin';upstream=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision']);sha=a.out/'SHA256.o';exe=a.out/'all-Q2-composite.exe';q4=a.cache/'Expert-Q4-receipt-7629.json';q4seal=a.cache/'build/Expert-Q4-relocation-7670/source-integrity.private.json';q4layout=a.cache/'expert-q4-local-conversion-7605/model-receipt.private.json'
 topology=a.out/'resolved-topology-not-for-deployment.private.json'
 commands=[[host/'clang.exe','-std=c11','-O2','-I',upstream/'vendor','-I',upstream/'vendor/hash','-c',upstream/'vendor/hash/sha256/sha256.c','-o',sha],[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app','-I',upstream/'vendor',ROOT/'tests/expert_all_q2_composite.cpp',ROOT/'native/app/model_integrity.cpp',sha,'-o',exe],[exe,mp,gp,mixed_path,seal_path,q4,q4seal,q4layout,topology]]
 env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
 for i,cmd in enumerate(commands):
  run=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6000:])
 write_json(a.out/'receipt.private.json',dict(completed=True,metadata_only=True,not_for_deployment=True,PS5_operations=0,native_result=json.loads(run.stdout),model=record(mp),gate=record(gp),topology=record(topology),plan=record(a.plan),inputs=[record(x)for x in (Path(__file__),ROOT/'tests/expert_all_q2_composite.cpp',ROOT/'native/app/expert_all_q2_source_integrity.h',ROOT/'native/app/expert_all_q2_receipt.h')]))
 print(run.stdout.decode(),end='')
if __name__=='__main__':main()
