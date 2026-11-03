#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconstruct the retained selected cache source using its maintained generators."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def patch(text,source):
    lines=text.splitlines(keepends=True);rows=source.splitlines(keepends=True);out=[];cursor=0;i=0
    while i<len(rows):
        match=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',rows[i])
        if not match:i+=1;continue
        start=int(match[1])-1;old=[];new=[];i+=1
        while i<len(rows) and not rows[i].startswith('@@'):
            line=rows[i]
            if line.startswith((' ','-')):old.append(line[1:])
            if line.startswith((' ','+')):new.append(line[1:])
            i+=1
        need(start>=cursor and lines[start:start+len(old)]==old,'Exact original cache patch context required')
        need(len(old)==int(match[2] or 1) and len(new)==int(match[4] or 1),'Complete original patch hunk required')
        out.extend(lines[cursor:start]);out.extend(new);cursor=start+len(old)
    out.extend(lines[cursor:]);return ''.join(out)


def function(name,symbol,text):
    path=ROOT/'tools'/name;tree=ast.parse(path.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==symbol)
    env=dict(once=once,re=re,ROOT=ROOT)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
    return env[symbol](text)


def inline(name,text,**variables):
    path=ROOT/'tools'/name;tree=ast.parse(path.read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    env=dict(once=once,re=re,ROOT=ROOT,cache=text,**variables);count=0
    for node in main.body:
        if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='cache':
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env);count+=1;continue
        if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):continue
        target=node.targets[0].id
        if target in ('marker','old') and isinstance(node.value,ast.Constant):
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
        if target=='cache':
            if not any(isinstance(x,ast.Name) and x.id=='cache' for x in ast.walk(node.value)):
                class OriginalInput(ast.NodeTransformer):
                    def visit_Call(self,value):
                        if isinstance(value.func,ast.Attribute) and value.func.attr=='read_text':
                            return ast.copy_location(ast.Name(id='cache',ctx=ast.Load()),value)
                        return self.generic_visit(value)
                node=OriginalInput().visit(node)
            if isinstance(node.value,ast.Name):continue
            if any(isinstance(x,ast.Name) and x.id=='cache' for x in ast.walk(node.value)):
                exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env);count+=1
    need(count>0,'At least one original inline cache transformation must be recovered')
    return env['cache']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='Preserve identical already generated source stages; never compile or execute them')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=a.resume)
    original=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/llama-moe-cache.cpp'
    need(record(original)['sha256']=='d0b19ef2e921ec16ed04e751d32cbc7682973e915f0df85b6cadc8800e0af6cd','Exact pinned original cache source required')
    text=original.read_text();history=[]
    def keep(label,value):
        nonlocal text
        text=value;path=a.out/(str(len(history)).zfill(2)+'-'+label+'.private.cpp')
        reused=path.exists()
        if reused:need(a.resume and path.read_text()==text,'An already reconstructed source stage changed')
        else:path.write_text(text,newline='\n')
        history.append(dict(label=label,source=record(path)))
        if not reused:print(dict(stage=label,bytes=len(text.encode()),sha256=history[-1]['source']['sha256']),flush=True)
    keep('model-IO',patch(text,(ROOT/'patches/native-model-io/0002-llama-moe-cache.patch').read_text()))
    for label,name,symbol in (
        ('predictive-geometry','predictive_model_geometry.py','generate'),('six-demand','refill_model_io.py','generate'),
        ('resident-reuse','resident_cache_reuse.py','generate'),('mixed-Q2','expert_q2_model_source.py','cache_source'),
        ('all-Q2','expert_all_q2_model_source.py','cache_source'),('probation','build_expert_q2_policy_comparison.py','cache_source'),
        ('bundle','expert_q2_bundle_reader.py','cache_source'),('adjacent-bundle','expert_q2_adjacent_bundle.py','cache_source'),
        ('IO-reduction','expert_q2_io_reduction.py','cache_source'),('routing','build_expert_routing_sharing.py','cache_source'),
        ('lean','build_lean_prefill_cache_capacity.py','cache_source'),('output-Q8','build_output_q8_screen.py','cache_source')):
        keep(label,function(name,symbol,text))
    keep('cache1253',inline('build_cache_capacity_1125.py',text,SLOTS=1253))
    keep('cache1381',inline('build_shared_cache_capacity.py',text,slots=1381))
    cold=inline('build_cold_request_variant.py',text)
    keep('cold-prefill',cold.replace(',160>',',320>'))
    keep('cold-streaming',inline('build_cold_composition.py',text))
    keep('cache3072',inline('build_resident_cache3072.py',text,SLOTS=3072))
    keep('retention-normal',inline('build_weight_followup_normal.py',text))
    keep('speed-protection',inline('build_speed_followup.py',text))
    keep('cache3712',inline('build_next_five_Q4_cache.py',text,SLOTS=3712))
    keep('scheduler',inline('build_scheduler_slot_map_model.py',text))
    native=load(a.current/'provenance/native-link.receipt.private.json');expected=native['expert_q2_model']['actual_cache']
    need(history[-1]['source']['sha256']==expected['sha256'] and history[-1]['source']['bytes']==expected['bytes'],
        'Recovered source must match the complete selected source hash; compilation alone cannot qualify it')
    save(a.out/'result.private.json',dict(completed=True,source=history[-1]['source'],expected=expected,history=history,
        source_bytes_exact=True,old_host_or_native_model_tests_replayed=0,PS5_operations=0))
    print(dict(completed=True,source_bytes_exact=True,source=history[-1]['source'],PS5_operations=0))


if __name__=='__main__':main()
