#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile Q4 model providers while preserving original BF16 strategy dispatch."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from expert_q2 import record,require,write_json
from shader_storage import patch_vulkan
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
from active_native_inputs import active_link_inputs
ROOT=Path(__file__).resolve().parents[1]
BF16_FIXTURE_OVERRIDE='''    if(src0->type==GGML_TYPE_BF16 && src0->ne[2]==10 && src0->ne[3]==1 &&
       ((src0->ne[0]==2560&&src0->ne[1]==640)||(src0->ne[0]==640&&src0->ne[1]==2560)) &&
       src0->nb[0]==2 && src0->nb[1]==std::uint64_t(src0->ne[0])*2 &&
       src0->nb[2]==3276800 && dst->src[1]->type==GGML_TYPE_F32 &&
       dst->src[1]->ne[0]==src0->ne[0] && (dst->src[1]->ne[1]==1||dst->src[1]->ne[1]==10) &&
       ids->type==GGML_TYPE_I32 && ids->ne[0]==10 &&
       (ids->ne[1]==1||ids->ne[1]==2||ids->ne[1]==4))return true;
'''
Q2_INSERT='''
    // The Expert-only Q2 experiment retains the original F32 activations.
    if(src0_type==GGML_TYPE_Q2_K)return false;
'''

def build(providers,control,out):
    providers,control,out=map(Path,(providers,control,out));base=json.loads(providers.read_text());prior=json.loads(control.read_text())
    frozen=list({row['path']:row for row in active_link_inputs(base)+active_link_inputs(prior)}.values())
    for row in frozen:require(record(row['path'])==row,'Qualified provider ancestry changed')
    external=json.loads(Path(base['shader_resource_manifest']['path']).read_text());embedded=json.loads(Path(external['embedded_control']['path']).read_text())
    old_external=json.loads(Path(prior['shader_resource_manifest']['path']).read_text());old_embedded=json.loads(Path(old_external['embedded_control']['path']).read_text())
    key='ggml/src/ggml-vulkan/ggml-vulkan.cpp';manifests=[];objects=[];commands=[];sources=[]
    out.mkdir(parents=True,exist_ok=False);(out/'tmp').mkdir()
    for label,role in (('parent','parent_model_io'),('extended','extended_model_io')):
        manifest_path=Path(embedded[role]['path']);data=json.loads(manifest_path.read_text());source=manifest_path.parent/'source'/key
        require(source.read_text().count(BF16_FIXTURE_OVERRIDE)==1,'One component-only BF16 override must be identified exactly')
        text=source.read_text().replace(BF16_FIXTURE_OVERRIDE,'',1)
        require(text.count(Q2_INSERT)==1,'Exact Q2_K fixture input predicate required')
        text=text.replace(Q2_INSERT,Q2_INSERT.replace('src0_type==GGML_TYPE_Q2_K','src0_type==GGML_TYPE_Q2_K||src0_type==GGML_TYPE_Q4_0'),1)
        control_source=Path(old_embedded[role]['path']).parent/'source'/key
        combined=Q2_INSERT.replace('src0_type==GGML_TYPE_Q2_K','src0_type==GGML_TYPE_Q2_K||src0_type==GGML_TYPE_Q4_0')
        require(text.count(combined)==1 and text.replace(combined,'',1)==control_source.read_text(),
            'Every original BF16 dispatch byte must remain unchanged; only the Q4 F32-input predicate may differ')
        directory=out/label;target=directory/'source'/key;target.parent.mkdir(parents=True);target.write_text(text,newline='\n')
        row=next(row for row in data['objects']if row['source']==key);command=row['command'];obj=directory/'ggml-vulkan.cpp.o'
        require(isinstance(command,str),'Captured native Vulkan command string required')
        for flag,path in (('o',obj),('c',target)):
            command,count=re.subn(r'(?<=\s)-'+flag+r'\s+(?:"[^"]+"|\S+)',lambda _: '-'+flag+' '+subprocess.list2cmdline([str(path)]),command)
            require(count==1,'One exact Vulkan compile argument required')
        commands.append(command);objects.append(obj);sources.append(target)
        row.update(command=command,actual_source=record(target));data['sources'][key]['patched_sha256']=record(target)['sha256']
        manifests.append((directory/'model-io.private.json',data,row))
        frozen +=[record(manifest_path),record(source),record(control_source),record(target)]
    require(sources[1].read_text()==patch_vulkan(sources[0].read_text()),'Packed-shader restoration must remain the sole parent/extended difference')
    frozen +=[record(path)for path in (Path(__file__),providers,control)]
    for i,command in enumerate(commands):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(out/'tmp'),TEMP=str(out/'tmp')))
        (out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
        print(json.dumps(dict(Q4_model_provider_compiled=i+1,total=2,BF16_dispatch_restored_to_exact_control=True)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Provider input changed during compilation')
    rows=[]
    for i,(path,data,row)in enumerate(manifests):
        row['object']=record(objects[i]);write_json(path,data);validate_overrides(path,prior['engine_receipt']['path']);rows.append(record(path))
    replace={embedded['parent_model_io']['path']:rows[0],embedded['extended_model_io']['path']:rows[1],embedded['vulkan_object']['path']:record(objects[1])}
    def updated(inputs):return[replace.get(row['path'],row)for row in inputs]
    added=[record(path)for path in sources+objects]
    embedded.update(parent_model_io=rows[0],extended_model_io=rows[1],vulkan_object=record(objects[1]),inputs=updated(embedded['inputs'])+added)
    ep=out/'embedded-shader.private.json';write_json(ep,embedded);replace[external['embedded_control']['path']]=record(ep)
    external.update(parent_model_io=rows[0],extended_model_io=rows[1],vulkan_object=record(objects[1]),embedded_control=record(ep),inputs=updated(external['inputs'])+added)
    xp=out/'external-shader.private.json';write_json(xp,external);storage=validate_shader_resources(xp,rows[1]['path'],prior['engine_receipt']['path'])
    receipt=dict(schema='ps5-qwen-expert-q2-model-providers-v1',completed=True,application_image_built=False,console_operations=0,
        original_BF16_dispatch_byte_exact=True,Q2_F32_input_predicate_preserved=True,original_SPIRV_unchanged=True,
        source_parent=record(providers),BF16_control=record(control),commands=commands,shader_resource_manifest=record(xp),lossless_shader_storage=storage,
        inputs=frozen+added+rows+[record(ep),record(xp)])
    write_json(out/'receipt.private.json',receipt);return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('providers','control','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();build(a.providers,a.control,a.out)
if __name__=='__main__':main()
