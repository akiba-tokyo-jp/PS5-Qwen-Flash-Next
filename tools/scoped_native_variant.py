# SPDX-License-Identifier: MIT
"""Relink explicit application providers while retaining all shared GPU archives."""
import copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import record,require,write_json
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch

def link(parent_path,out,variants,inputs):
    prior=json.loads(Path(parent_path).read_text());out=Path(out)
    require(out.is_dir()and not(out/'receipt.private.json').exists(),'Fresh scoped source directory required')
    (out/'tmp').mkdir();frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
    frozen +=[record(parent_path),record(__file__),*[record(p)for p in inputs]]
    for row in frozen:require(record(row['path'])==row,'Scoped variant input changed')
    replacements={};commands={};sources={};added=[]
    for label,(original,text)in variants.items():
        cmd=original.copy();oldsrc=Path(cmd[cmd.index('-c')+1]);oldobj=cmd[cmd.index('-o')+1]
        source=out/(label+'.private.cpp');source.write_text(text,newline='\n');obj=out/(label+'.o')
        cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
        cmd[1:1]=['-I',str(oldsrc.parent),'-I',str(out)]
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(out/(label+'.private.d'))
        require(prior['link_command'].count(oldobj)==1,'Exactly one current provider must be replaced')
        replacements[oldobj]=str(obj);commands[label]=cmd;sources[label]=record(source);added.append(record(source))
    image=out/'qwen-native.pie.elf';command=[replacements.get(x,x)for x in prior['link_command']]
    command[command.index('-o')+1]=str(image);command=[('-Map='+str(out/'native-link.private.map'))if x.startswith('-Map=')else x for x in command]
    for i,cmd in enumerate([*commands.values(),command]):
        run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(out/'tmp'),TEMP=str(out/'tmp')))
        (out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4500:])
        print(json.dumps(dict(scoped_build_step=i+1,total=len(commands)+1)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Frozen scoped provider changed during build: '+row['path'])
    result=copy.deepcopy(prior);result.update(artifact=record(image),link_command=command,source_parent=record(parent_path),
        inputs_before=frozen+added+[record(out/(k+'.o'))for k in variants],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    if 'entry'in commands:
        result['compile_commands']=[commands['entry']]
        result['expert_q2_model']['actual_entry']=sources['entry']
        if 'all_Q2_IO_measurement'in result:result['all_Q2_IO_measurement']['entry']=sources['entry']
        result['routing_sharing']['actual_sources']['entry']=sources['entry'];result['routing_sharing']['commands'][0]=commands['entry']
    if 'cache'in commands:
        result['expert_q2_model']['actual_cache']=sources['cache']
        result['routing_sharing']['actual_sources']['cache']=sources['cache'];result['routing_sharing']['commands'][1]=commands['cache']
    if 'engine'in commands:
        result['routing_sharing']['actual_sources']['engine']=sources['engine'];result['routing_sharing']['commands'][2]=commands['engine']
    if 'owner'in commands:
        result['all_Q2_optimized_monitor']['commands'][1]=commands['owner']
    return result,commands,sources

def seal(result,workspace,cache,out):
    target=Path(out)/'receipt.private.json';write_json(target,result)
    result['real_module_import_audit']=audit(workspace,cache,out)
    result['native_dispatch_audit']=dispatch(workspace,Path(workspace)/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',Path(result['artifact']['path']),Path(out)/'dispatch')
    require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Actual scoped imports/dispatch required')
    write_json(target,result)
