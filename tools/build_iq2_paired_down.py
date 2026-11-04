#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the640-column paired IQ2 shader and validate all original sample rows."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def table(text,kind,name,count):
    match=re.search(r'GGML_TABLE_BEGIN\('+kind+', '+name+', '+str(count)+r'\)(.*?)GGML_TABLE_END\(\)',text,re.S)
    need(match is not None,'Pinned IQ2 table declaration required')
    values=[int(value.strip(),0) for value in match[1].strip().strip(',').split(',')]
    need(len(values)==count,'Complete pinned table required');return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','samples','output-reference','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--buffer-tables',action='store_true',help='Use one explicit2560-byte readonly codebook descriptor')
    a=p.parse_args();os.environ['OPENBLAS_NUM_THREADS']='6';import numpy as np
    up=a.cache/('upstream/llama.cpp-'+REVISION);source=up/'ggml/src/ggml-common.h';text=source.read_text(encoding='utf-8')
    grid=table(text,'uint64_t','iq2xxs_grid',256);signs=table(text,'uint8_t','ksigns_iq2xs',128)
    samples=load(a.samples);reference=load(a.output_reference)
    need(samples['completed'] and samples['Down_paired_row_component'] and samples['requires_custom_640_column_GPU_operator'] and
        record(samples['pack']['path'])==samples['pack'] and reference['completed'] and reference['all_actual_operand_moments_independently_reproduced'] and
        record(a.samples) in reference['samples'],'Complete original paired-row samples and actual operand outputs required')
    need(all(record(row['path'])==row for row in reference['outputs']),'Actual reference outputs changed')
    a.out.mkdir(parents=True,exist_ok=False);shutil.copyfile(ROOT/'native/app/iq2_paired_down.h',a.out/'iq2_paired_down.h')
    shutil.copyfile(ROOT/'native/app/iq2_paired_down.comp',a.out/'iq2_paired_down.comp')
    notice='// Tables from pinned llama.cpp ggml-common.h (MIT). See third_party/notices/ggml-quantization/LICENSE.\n'
    h=a.out/'paired_iq2_tables.h';h.write_text(notice+'#pragma once\n#include <cstdint>\ninline constexpr std::uint64_t paired_grid[]={'+','.join(hex(v)+'ull' for v in grid)+'};\ninline constexpr std::uint8_t paired_signs[]={'+','.join(map(str,signs))+'};\n',encoding='utf-8',newline='\n')
    glsl=a.out/'paired_iq2_tables.glsl';glsl.write_text(notice+'const uvec2 iq2_grid[256]=uvec2[256]('+','.join('uvec2('+hex(v&0xffffffff)+'u,'+hex(v>>32)+'u)' for v in grid)+');\nconst uint iq2_signs[128]=uint[128]('+','.join(str(v)+'u' for v in signs)+');\n',encoding='utf-8',newline='\n')
    bridge=a.out/'decoder.cpp';bridge.write_text('''// SPDX-License-Identifier: MIT
#include "iq2_paired_down.h"
#include "paired_iq2_tables.h"
#if defined(_WIN32)
#define QWEN_EXPORT __declspec(dllexport)
#else
#define QWEN_EXPORT __attribute__((visibility("default")))
#endif
extern "C" QWEN_EXPORT int qwen_paired_down_decode(const unsigned char*input,std::size_t bytes,float*output,std::size_t count){
    using D=qwen_app::PairedIQ2Down;
    if(!input||!output||bytes!=D::matrix_bytes||count!=std::size_t(D::rows)*D::columns)return -1;
    for(unsigned row=0;row<D::rows;++row)for(unsigned col=0;col<D::columns;++col)output[row*D::columns+col]=D::decode(input,row,col,paired_grid,paired_signs);
    return 0;
}
''',encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';dll=a.out/'paired-down-decode.dll'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared',str(bridge),'-o',str(dll)],
        [str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
         '-std=c++17','-O2','-ffp-contract=off','-fPIC','-fno-stack-protector','-c',str(bridge),'-o',str(a.out/'paired-down-decode.o')]]
    shaders=[]
    compiler=a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslangValidator.exe';validator=host/'spirv-val.exe'
    for workgroup in (64,128):
        path=a.out/('paired-down-'+str(workgroup)+'.spv')
        commands.extend([[str(compiler),'-V','--target-env','vulkan1.2','-S','comp','-DQWEN_DOWN_WORKGROUP='+str(workgroup),*(['-DQWEN_DOWN_BUFFER_TABLES=1'] if a.buffer_tables else []),'-I'+str(a.out),str(a.out/'iq2_paired_down.comp'),'-o',str(path)],
            [str(validator),'--target-env','vulkan1.2',str(path)]]);shaders.append(dict(workgroup=workgroup,path=path))
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')[-3500:])
    package=types.ModuleType('gguf');package.__path__=[str(up/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.quants import IQ2_XXS
    directory=os.add_dll_directory(str(host));library=ctypes.CDLL(str(dll));decode=library.qwen_paired_down_decode
    decode.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];decode.restype=ctypes.c_int
    encoded={};checks=[]
    for row in samples['matrices']:
        part=row['IQ2_XXS'];need((row['columns'],row['rows'],row['encoded_columns'],row['encoded_rows'],part['bytes'])==(640,2560,1280,1280,422400),'Exact Down geometry required')
        with Path(samples['pack']['path']).open('rb') as stream:stream.seek(part['offset']);raw=stream.read(part['bytes'])
        need(hashlib.sha256(raw).hexdigest()==part['sha256'],'Whole encoded extent changed')
        data=np.frombuffer(raw,np.uint8);actual=np.empty(640*2560,np.float32);need(decode(data.ctypes.data,data.nbytes,actual.ctypes.data,actual.size)==0,'Paired decoder refused its exact geometry')
        expected=IQ2_XXS.dequantize(data.reshape(-1,66)).reshape(-1)
        need(actual.tobytes()==expected.tobytes() and np.isfinite(actual).all(),'Every paired-row F32 byte must match the independent pinned decoder')
        checks.append(dict(layer=row['layer'],expert=row['expert'],decoded_values=actual.size,all_F32_bytes_exact=True));encoded[(row['layer'],row['expert'])]=raw
    directory.close();cases=[]
    for layer in (0,23,47):
        matrices=[row for row in samples['matrices'] if row['layer']==layer];need(len(matrices)==3,'Three original Experts per group required')
        weights=a.out/('layer-'+str(layer)+'-planes.bin')
        weights.write_bytes(b''.join(encoded[(layer,matrices[2 if plane==9 else plane%3]['expert'])] for plane in range(10)))
        operands=[]
        for row in matrices:
            path=Path(reference['outputs'][0]['path']).parent/('layer-'+str(layer).zfill(2)+'-down-Expert-'+str(row['expert'])+'.npz')
            need(record(path) in reference['outputs'],'Exact real input/output fixture required');operands.append(np.load(path))
        for width in (1,2,30,32):
            selected=2 if width<=2 else 10;ids=np.empty((width,selected),np.uint32);inputs=np.empty((width,selected,640),np.float32);outputs=np.empty((width,selected,2560),np.float64)
            for token in range(width):
                for slot in range(selected):
                    plane=(0,4,9)[(slot+token)%3] if selected==2 else (slot+token)%10
                    index=2 if plane==9 else plane%3;data=operands[index];sample=(slot+token)%len(data['input'])
                    ids[token,slot]=plane;inputs[token,slot]=data['input'][sample];outputs[token,slot]=data['IQ2_XXS_output_F64'][sample]
            tag='layer-'+str(layer)+'-width-'+str(width);values={}
            for label,data in (('inputs',inputs),('ids',ids),('expected',outputs)):
                path=a.out/(tag+'-'+label+'.bin');path.write_bytes(data.tobytes());values[label]=record(path)
            cases.append(dict(layer=layer,width=width,selected=selected,planes=10,rows=2560,columns=640,weights=record(weights),**values,
                actual_operands_repeated_for_component_geometry=True,original_Experts=[row['expert'] for row in matrices]))
    tables=a.out/'paired-IQ2-codebooks.bin';tables.write_bytes(struct.pack('<256Q128I',*grid,*signs))
    save(a.out/'GPU-cases.private.json',dict(completed=True,cases=cases,shader=[dict(workgroup=row['workgroup'],artifact=record(row['path'])) for row in shaders],
        source=record(a.out/'iq2_paired_down.comp'),buffer_tables=a.buffer_tables,tables=record(tables),reference=record(a.output_reference),PS5_operations=0))
    save(a.out/'result.private.json',dict(completed=True,source_inputs=[record(a.out/'iq2_paired_down.h'),record(a.out/'iq2_paired_down.comp'),record(source)],
        table_bytes_sha256=hashlib.sha256(struct.pack('<256Q128B',*grid,*signs)).hexdigest(),upstream_revision=REVISION,
        samples=record(a.samples),reference=record(a.output_reference),decoder_checks=checks,all14745600_decoded_F32_values_byte_exact=True,buffer_tables=a.buffer_tables,
        shaders=[dict(workgroup=row['workgroup'],artifact=record(row['path']),SPIRV_validation_passed=True) for row in shaders],
        PS5_decoder_object=record(a.out/'paired-down-decode.o'),GPU_cases=record(a.out/'GPU-cases.private.json'),commands=commands,
        native_GPU_execution=False,PC_GPU_execution=False,model_integration=False,whole_speed_qualified=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,all14745600_F32_values_byte_exact=True,SPIRV_profiles=2,prepared_GPU_cases=len(cases),PS5_operations=0)))


if __name__=='__main__':main()
