#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise native mixed-precision admission using metadata-only host controls."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import EXPERT,LOCK,record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','inventory','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    inventory=json.loads(a.inventory.read_text());original=json.loads(Path(inventory['original_receipt']['path']).read_text())
    require(record(inventory['original_receipt']['path'])==inventory['original_receipt'],'Original BF16 receipt changed')
    files=[]
    for entry in inventory['files']:
        old=entry['original'];files.append(dict(**old,reused_original=not entry['replacement_required'],original_sha256=old['sha256']))
    tensors=[dict(name=t['name'],shape=t['shape'],type=('Q4_0'if EXPERT.fullmatch(t['name'])[2]=='down'else'Q2_K')if EXPERT.fullmatch(t['name'])else t['original_type'],
                  bytes=(t['bytes']*18//64 if EXPERT.fullmatch(t['name'])[2]=='down'else t['bytes']*84//512)if EXPERT.fullmatch(t['name'])else t['bytes']) for t in inventory['tensors']]
    fixture=dict(schema='ps5-qwen-expert-q2-model-v1',completed=True,Expert_format='Gate_Up_Q2_K_Down_Q4_0',
        original_revision=LOCK['model']['revision'],upstream_revision=LOCK['llama_cpp']['revision'],
        original_receipt_sha256=inventory['original_receipt']['sha256'],original_BF16_receipt=original,
        all_Experts_retained=True,non_Expert_payload_bytes_preserved=True,activation_quantization=False,KV_quantization=False,
        host_model_inference=False,files=files,tensors=tensors,mapped_file_bytes=sum(x['bytes'] for x in files))
    source=a.out/'metadata-control-not-for-deployment.private.json';write_json(source,fixture)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'expert-q2-receipt.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    upstream=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision'])
    commands=[[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',
               '-I',upstream/'vendor',ROOT/'tests/expert_q2_receipt.cpp','-o',exe],[exe,source]]
    for i,c in enumerate(commands):
        r=subprocess.run(list(map(str,c)),capture_output=True,timeout=120,env=env)
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        require(r.returncode==0,r.stderr.decode(errors='replace')[-4000:])
    write_json(a.out/'receipt.private.json',dict(completed=True,metadata_control_only=True,not_for_deployment=True,
        fixture=record(source),executable=record(exe),inputs=[record(x)for x in(Path(__file__),ROOT/'tests/expert_q2_receipt.cpp',ROOT/'native/app/expert_q2_receipt.h')],
        native_result=json.loads(r.stdout),commands=[list(map(str,c))for c in commands]))
    print(r.stdout.decode(),end='')

if __name__=='__main__':main()
