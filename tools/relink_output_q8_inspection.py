#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit only the pinned Q8 output tensor through the original GGUF inspection."""
import argparse,json,os,subprocess
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def inspect_source(text):
 text=once(text,'        const auto type = gguf_get_tensor_type(metadata.get(), i);',
  '        const auto type = gguf_get_tensor_type(metadata.get(), i);\n        const auto * name=gguf_get_tensor_name(metadata.get(),i);')
 text=once(text,'type != GGML_TYPE_Q2_K && type != GGML_TYPE_Q2_0)',
  'type != GGML_TYPE_Q2_K && type != GGML_TYPE_Q2_0 &&\n            !(type==GGML_TYPE_Q8_0&&name&&!std::strcmp(name,"output.weight")))')
 text=once(text,'        const auto * name=gguf_get_tensor_name(metadata.get(),i);\n        const auto bytes=', '        const auto bytes=')
 text=once(text,'type==GGML_TYPE_Q2_K?"Q2_K":','type==GGML_TYPE_Q8_0?"Q8_0":type==GGML_TYPE_Q2_K?"Q2_K":')
 return once(text,'Only original BF16 or lossless F32 widening is accepted','Only the admitted original, Expert Q2 and output-only Q8 types are accepted')

def host_test(entry,cache,folder):
 upstream=cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
 host=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin'
 source=(ROOT/'tests/resident_output_q8_receipt.cpp').read_text()
 source='#include "ggml.h"\n#include <cstring>\n'+source
 a=entry.index('        if (type != GGML_TYPE_BF16',entry.index('static void inspect_container('));b=entry.index('        const auto bytes=',a)
 guard=entry[a:b]
 declaration='static void actual_inspection_guard(ggml_type type,const char*name){\n'+guard+'}\n'
 source=once(source,'int main(int argc,char**argv){try{',declaration+'int main(int argc,char**argv){try{')
 marker='    require(checked==1256);unsigned refused=0;'
 source=once(source,marker,'''    require(checked==1256);
    for(const auto&t:candidate.at("tensors")){
      const auto kind=t.at("type").get<std::string>(),name=t.at("name").get<std::string>();
      const auto type=kind=="Q8_0"?GGML_TYPE_Q8_0:kind=="Q2_K"?GGML_TYPE_Q2_K:kind=="Q2_0"?GGML_TYPE_Q2_0:kind=="BF16"?GGML_TYPE_BF16:GGML_TYPE_F32;
      actual_inspection_guard(type,name.c_str());
    }
    unsigned guard_refusals=0;
    for(const char*name:{"token_embd.weight","blk.0.attn_q.weight","blk.0.ffn_gate_exps.weight"}){
      try{actual_inspection_guard(GGML_TYPE_Q8_0,name);}catch(const std::exception&){++guard_refusals;}
    }
    require(guard_refusals==3);unsigned refused=0;''')
 test=folder/'actual-output-Q8-inspection.private.cpp';test.write_text(source,newline='\n')
 exe=folder/'actual-output-Q8-inspection.exe';sha=upstream/'vendor/hash/sha256/sha256.c';sha_obj=folder/'host-sha256.o'
 commands=[[str(host/'clang.exe'),'-O2','-I',str(upstream/'vendor/hash'),'-c',str(sha),'-o',str(sha_obj)],
   [str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(ROOT/'native/app'),'-I',str(upstream/'ggml/include'),'-I',str(upstream/'vendor'),str(test),str(sha_obj),'-o',str(exe)],
   [str(exe),str(cache/'resident-output-Q8-9193/model-receipt.json'),str(cache/'Expert-all-Q2-receipt-8652.json')]]
 env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
 for i,cmd in enumerate(commands):
  r=subprocess.run(cmd,capture_output=True,timeout=180,env=env);(folder/f'inspection-host-{i}.private.log').write_bytes(r.stdout+r.stderr)
  require(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3000:])
 return dict(completed=True,actual_GGUF_guard_extracted_from_compiled_entry=True,complete_receipt_tensors=1256,
  non_output_Q8_names_refused=3,receipt_mutations_refused=13,commands=commands,PS5_operations=0)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());cmd=prior['compile_commands'][0]
 text=inspect_source(Path(cmd[cmd.index('-c')+1]).read_text());a.out.mkdir(parents=True,exist_ok=False)
 proof=host_test(text,a.cache,a.out);write_json(a.out/'actual-inspection-host.private.json',proof)
 result,commands,sources=link(a.parent,a.out,{'entry':(cmd,text)},[Path(__file__),ROOT/'tests/resident_output_q8_receipt.cpp',a.out/'actual-inspection-host.private.json'])
 result['output_Q8_screen']['actual_sources']['entry']=sources['entry'];result['output_Q8_screen']['commands']['entry']=commands['entry']
 result['output_Q8_screen']['actual_inspection_host']=record(a.out/'actual-inspection-host.private.json')
 seal(result,a.workspace,a.cache,a.out);print('Actual output-only Q8 inspection and 1256 receipt tensors passed before relink.')

if __name__=='__main__':main()
