#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the actual C++ chat path and tokenize original metadata, without model inference.

Run with the existing conversion environment containing tokenizers. Input/output
token IDs are proposed host metadata until independently checked on the console.
"""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    from tokenizers import Tokenizer,__version__ as tokenizer_version
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();manifest_path=ROOT/'config/bounded-workloads.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    expected=dict(schema='ps5-qwen-bounded-workload-proposals-v1',context_tokens=256,maximum_rendered_prompt_tokens=30,
        maximum_output_tokens=22,prefill_tokens=4,thinking=False,sampler='greedy',console_execution_enabled=False)
    if any(type(manifest.get(k))is not type(v)or manifest[k]!=v for k,v in expected.items())or len(manifest.get('requests',[]))!=4:
        raise ValueError('Exact finite disabled workload scope required')
    names=[x['name']for x in manifest['requests']]
    if names!=['ja_dialogue','code_copy','short_reasoning','low_repetition']or any(not 1<=len(x['prompt'].encode())<=256 for x in manifest['requests']):
        raise ValueError('Four bounded workload classes required')
    template=a.cache/'model/chat_template.jinja';tokenizer_path=a.cache/'model/tokenizer.json';settings=a.cache/'model/tokenizer_config.json'
    if template.stat().st_size>256<<10 or tokenizer_path.stat().st_size>32<<20 or settings.stat().st_size>256<<10:
        raise ValueError('Only bounded original tokenizer/template metadata may be read')
    config=json.loads(settings.read_text(encoding='utf-8'))
    if config.get('add_bos_token',False)or config.get('add_eos_token',False):
        raise ValueError('Special-token insertion needs an independent native tokenizer qualification')
    prior=ROOT/'build/first-generation-check-006/receipt.private.json';receipt=json.loads(prior.read_text())
    objects=[ROOT/'build/first-generation-check-003'/('render-'+str(i)+'.o')for i in range(2,11)]
    for obj in objects:
        if hashlib.sha256(obj.read_bytes()).hexdigest()!=receipt['reused_objects'][str(obj)]:raise ValueError('Pinned renderer donor changed')
    assertions=ROOT/'build/first-generation-check-006/preview-assertions.o'
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    flags=['-std=c++17','-O0','-I',ROOT/'native/app','-I',up/'common','-I',up/'vendor','-I',up/'src','-I',up/'ggml/include']
    commands=[];compiled=[]
    for label,source in(('main',ROOT/'tests/render_bounded_workloads.cpp'),('prompt',ROOT/'native/app/chat_prompt.cpp')):
        obj=a.out/(label+'.o');compiled.append(obj);commands.append([host/'clang++.exe',*flags,'-c',source,'-o',obj])
    exe=a.out/'render.exe';commands.append([host/'clang++.exe',*compiled,*objects,assertions,'-o',exe]);commands.append([exe,template,manifest_path])
    inputs=[record(f)for f in [Path(__file__),manifest_path,template,tokenizer_path,settings,prior,assertions,*objects,
        ROOT/'tests/render_bounded_workloads.cpp',ROOT/'native/app/chat_prompt.cpp',ROOT/'native/app/first_generation.h',ROOT/'native/app/bounded_demo.h']]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate(commands):
        r=subprocess.run(list(map(str,c)),capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Metadata render '+str(i)+': '+r.stderr.decode(errors='replace')[-1800:])
    rows=json.loads(r.stdout);tokenizer=Tokenizer.from_file(str(tokenizer_path))
    for row in rows:
        ids=tokenizer.encode(row['rendered'],add_special_tokens=False).ids
        if not ids or len(ids)>30 or any(not 0<=i<262144 for i in ids):raise ValueError('Rendered workload exceeds its original token scope: '+row['name'])
        row.update(prompt_token_ids=ids,prompt_tokens=len(ids),rendered_SHA256=hashlib.sha256(row['rendered'].encode()).hexdigest())
    control_path=a.cache/'hardware-first-generation-2240/native-plan-observation/native-result.private.json';control=json.loads(control_path.read_text())
    counts=[control['metrics']['prompt_tokens'],control['demonstration']['requests'][0]['metrics']['prompt_tokens']]
    if counts!=[rows[i]['prompt_tokens']for i in range(2)]:raise ValueError('Host original tokenizer counts differ from completed native controls')
    inputs.append(record(control_path));assert inputs==[record(Path(x['path']))for x in inputs]
    result=dict(schema='ps5-qwen-host-bounded-workloads-v1',requests=rows,inputs=inputs,commands=[list(map(str,c))for c in commands],
        tokenizer_version=tokenizer_version,original_cpp_renderer_used=True,control_native_token_counts_match=True,
        native_token_ID_equality_qualified=False,native_workloads_executed=False,learned_inference=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(requests=[dict(name=x['name'],prompt_tokens=x['prompt_tokens'])for x in rows],
        control_native_token_counts_match=True,native_token_ID_equality_qualified=False,learned_inference=False,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
