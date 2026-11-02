#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconstruct the exact selected model source and compile a post-trunk crop."""
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_frontier_HC import transform as join_hc
from build_performance_quantizer import record
from prepare_shared_q4 import REVISION,load

ROOT=Path(__file__).resolve().parents[1]


def once(source,old,new):
    if source.count(old)!=1:raise RuntimeError('Expected exactly one source anchor')
    return source.replace(old,new,1)


def post_trunk_crop(source):
    start=source.index('        if (il == n_layer - 1 && crop_before_nextn(inp_out_ids)) {')
    end=source.index('        res_hc = build_hc_combine(res_hc, cur, inject, il);',start)
    source=source[:start]+'''        // Keep the full final FFN and its Expert-cache dependencies. Output
        // selection occurs only after the complete trunk has been constructed.
'''+source[end:]
    source=once(source,'    // the MTP head reads the hc-wide residual, before the final mixer',
                '''    const bool crop_hidden = inp_out_ids && (!cparams.embeddings_nextn || cparams.embeddings_nextn_masked);
    // The full residual keeps every trunk/cache dependency in the graph.
    // the MTP head reads the hc-wide residual, before the final mixer''')
    source=once(source,'    cb(res->t_h_nextn, "h_nextn", -1);',
                '    cb(res->t_h_nextn, crop_hidden ? "h_nextn_full" : "h_nextn", -1);')
    source=once(source,'    if (crop_after_nextn(inp_out_ids)) {','    if (inp_out_ids) {')
    marker='''        res_hc = ggml_reshape_3d(ctx0, res_hc, n_embd, hc, res_hc->ne[1]);
    }

    // the final mixer is the output norm: there is no separate one'''
    source=once(source,marker,'''        res_hc = ggml_reshape_3d(ctx0, res_hc, n_embd, hc, res_hc->ne[1]);
        if (crop_hidden) {
            res->t_h_nextn = ggml_reshape_2d(ctx0, res_hc, n_embd*hc, res_hc->ne[2]);
            cb(res->t_h_nextn, "h_nextn", -1);
            ggml_build_forward_expand(gf, res->t_h_nextn);
        }
    }

    // the final mixer is the output norm: there is no separate one''')
    return source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    receipt=load(args.cache/'current/provenance/native-link.receipt.private.json')
    up=args.cache/('upstream/llama.cpp-'+REVISION)
    original=up/'src/models/qwen4exp.cpp';raw=original.read_text()
    assert record(original)['sha256']==receipt['GDN_model_graph_order']['original_model']['sha256']
    tree=ast.parse((ROOT/'tools/build_gdn_graph_order_comparison.py').read_text())
    additions=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)
               and 'Schedule the two independent normalizations before either head repeat.' in n.value]
    assert len(additions)==1
    needle='    k_conv = build_gdn_l2_norm(ctx0, k_conv, eps_norm);'
    ordered=once(raw,needle,needle+'\n'+additions[0])
    assert hashlib.sha256(ordered.encode()).hexdigest()==receipt['GDN_model_graph_order']['actual_model']['sha256']
    baseline=join_hc(ordered)
    assert hashlib.sha256(baseline.encode()).hexdigest()==receipt['frontier_HC']['model_part']['sha256']
    control=args.out/'qwen4exp.control.cpp';control.write_text(baseline,encoding='utf-8',newline='\n')
    candidate=args.out/'qwen4exp.post-trunk.cpp';changed=post_trunk_crop(baseline)
    candidate.write_text(changed,encoding='utf-8',newline='\n')
    (args.out/'post-trunk.patch').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),changed.splitlines(True),
                                          fromfile='qwen4exp.control.cpp',tofile='qwen4exp.post-trunk.cpp')),
                                          encoding='utf-8',newline='\n')
    compiler=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    common=[str(compiler),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
            '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-femulated-tls',
            '-fexceptions','-fcxx-exceptions','-fno-stack-protector','-fno-plt','-fPIC',
            '-fdenormal-fp-math=ieee','-Oz','-ffunction-sections','-fdata-sections','-DNDEBUG',
            '-I',str(ROOT/'native/app'),'-I',str(up/'src/models'),'-I',str(up/'src'),
            '-I',str(up/'include'),'-I',str(up/'ggml/include'),'-I',str(up/'ggml/src')]
    commands=[]
    env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out))
    for name,path in (('control',control),('candidate',candidate)):
        job=common+['-c',str(path),'-o',str(args.out/(name+'.o'))];commands.append(job)
        result=subprocess.run(job,capture_output=True,timeout=120,env=env)
        (args.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    result=dict(completed=True,exact_selected_GDN_HC_source_reconstructed=True,
                control_source=record(control),candidate_source=record(candidate),
                PS5_target_objects=[record(args.out/(name+'.o')) for name in ('control','candidate')],
                commands=commands,full_final_FFN_preserved=True,output_selection_after_trunk=True,
                engine_selection_integrated=False,native_relink=False,native_model_validation=False,
                native_speed_measured=False,production_adopted=False,PS5_operations=0,
                required_boundary_lengths=[1,2,31,32,33,63,64,65],
                required_native_controls=['full F32 logits','ordered routes','all recurrent and KV state',
                                          'continuation','exact-prefix restore','speculative acceptance and rejection'])
    (args.out/'result.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','control_source','candidate_source','PS5_target_objects')}))


if __name__=='__main__':main()
