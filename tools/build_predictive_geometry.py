#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink one original model I/O object with its corrected geometry guard."""
import argparse,copy,json,os,shlex,subprocess
from pathlib import Path
from shader_storage import record
from predictive_model_geometry import generate
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--model-io',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();prior=json.loads(args.parent.read_text());io=json.loads(args.model_io.read_text())
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Original qualified native input changed: '+row['path'])
    row=next(x for x in io['objects']if x['source']=='src/llama-moe-cache.cpp')
    recipe=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in shlex.split(row['command'],posix=False)]
    original=Path(recipe[recipe.index('-c')+1]);old_object=row['object']
    if record(old_object['path'])!=old_object or recipe[recipe.index('-o')+1]!=old_object['path']:
        raise ValueError('Actual original MoE object/compile recipe differs')
    args.out.mkdir(parents=True);(args.out/'tmp').mkdir()
    generated=args.out/'llama-moe-cache-geometry.private.cpp';generated.write_text(generate(original.read_text()),newline='\n')
    obj=args.out/'llama-moe-cache-geometry.o';recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj)
    inputs=[record(x)for x in (Path(__file__),ROOT/'tools/predictive_model_geometry.py',ROOT/'native/app/predictive_model_geometry.h',
        args.parent,args.model_io,original,generated)]+prior['inputs_before']
    image=args.out/'qwen-native.pie.elf';command=prior['link_command'].copy()
    if command.count(old_object['path'])!=1:raise ValueError('Unique actual linked MoE object required')
    command=[str(obj)if x==old_object['path']else x for x in command];command[command.index('-o')+1]=str(image)
    command=[('-Map='+str(args.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in command]
    for index,arguments in enumerate((recipe,command)):
        result=subprocess.run(arguments,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(args.out/'tmp'),TEMP=str(args.out/'tmp')))
        (args.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
    for item in inputs:
        if record(item['path'])!=item:raise ValueError('Frozen geometry source changed')
    receipt=copy.deepcopy(prior);objects=receipt['bounded_model_source_overrides']['objects']
    replacement=next(x for x in objects if x['source']=='src/llama-moe-cache.cpp');replacement.update(object=record(obj),original_object=old_object,command=recipe,actual_source=record(generated))
    receipt.update(artifact=record(image),link_command=command,inputs_before=inputs+[record(obj)],
        compile_commands=prior['compile_commands']+[recipe],source_parent=record(args.parent),
        predictive_geometry_correction=dict(trunk_layers=48,total_layers=49,retained_MTP_layers=1,forecast_layer_limit=48,
            original_precision_and_arithmetic_preserved=True,source=record(original),generated=record(generated),header=record(ROOT/'native/app/predictive_model_geometry.h')),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    (args.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(actual_MoE_geometry_guard_relinked=True,original_MTP_block_retained=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
