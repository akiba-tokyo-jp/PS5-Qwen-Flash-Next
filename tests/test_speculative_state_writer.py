# SPDX-License-Identifier: MIT
"""Execute the actual bounded state writer with synthetic host tensors."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class StateWriterTests(unittest.TestCase):
    def test_exact_payload_hash_and_pre_read_refusals(self):
        retained=os.environ.get('QWEN_FROZEN_BUILD_DIR')
        if not retained:self.skipTest('Set QWEN_FROZEN_BUILD_DIR to the retained native build directory')
        upstream=Path(retained).parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
        source=(ROOT/'native/app/speculative_batch_probe.cpp').read_text()
        writer=source[source.index('class StateWriter final:'):source.index('\nbool same(')]
        header=(ROOT/'native/app/speculative_batch_probe.h').read_text()
        state=header[header.index('struct ProbeStateDigest {'):header.index('\nclass SpeculativeBatchProbe')]
        code=r'''
#include <array>
#include <algorithm>
#include <cstdint>
#include <cstddef>
#include <vector>
#include <stdexcept>
#include <cassert>
extern "C" {
#include "hash/sha256/sha256.h"
}
enum {GGML_TYPE_F32=0,GGML_TYPE_F16=1};
struct ggml_tensor{int type;std::size_t size;};
static std::size_t reads=0,maximum_read=0;
static std::size_t ggml_nbytes(ggml_tensor*t){return t->size;}
static void ggml_backend_tensor_get(ggml_tensor*t,void*p,std::size_t offset,std::size_t count){
 assert(count&&count<=65536&&offset<=t->size&&count<=t->size-offset);++reads;maximum_read=std::max(maximum_read,count);
 for(std::size_t i=0;i<count;++i)static_cast<unsigned char*>(p)[i]=static_cast<unsigned char>((offset+i)&255);
}
using llama_memory_t=void*;
static int llama_memory_seq_pos_min(llama_memory_t,int){return 0;}
static int llama_memory_seq_pos_max(llama_memory_t,int){return 31;}
class llama_io_write_i{public:virtual ~llama_io_write_i()=default;virtual void write(const void*,std::size_t)=0;
 virtual void write_tensor(ggml_tensor*,std::size_t,std::size_t)=0;virtual std::size_t n_bytes()=0;};
''' + state + writer + r'''
int main(){
 StateWriter writer;std::uint32_t metadata=31;writer.write(&metadata,sizeof(metadata));
 ggml_tensor tensor{GGML_TYPE_F32,65556};writer.write_tensor(&tensor,16,65540);
 auto result=writer.finish(nullptr);assert(reads==2&&maximum_read==65536);
 assert(result.tensor_bytes==65540&&result.tensor_sections==1&&result.metadata_bytes==4);
 assert(result.minimum==0&&result.maximum==31&&writer.n_bytes()==65544);
 std::vector<unsigned char> expected(65540);for(std::size_t i=0;i<expected.size();++i)expected[i]=static_cast<unsigned char>((16+i)&255);
 std::array<unsigned char,32> digest{};sha256_hash(digest.data(),expected.data(),expected.size());assert(digest==result.tensors);
 auto refuse=[&](auto fn){const auto before=reads;bool failed=false;try{fn();}catch(const std::runtime_error&){failed=true;}assert(failed&&reads==before);};
 refuse([&]{writer.write_tensor(nullptr,0,4);});
 tensor.type=GGML_TYPE_F16;refuse([&]{writer.write_tensor(&tensor,0,4);});tensor.type=GGML_TYPE_F32;
 refuse([&]{writer.write_tensor(&tensor,0,0);});refuse([&]{writer.write_tensor(&tensor,0,3);});
 refuse([&]{writer.write_tensor(&tensor,tensor.size,4);});refuse([&]{writer.write(nullptr,4);});
 refuse([&]{writer.write(&metadata,(1u<<20)+1);});
 tensor.size=(136u<<20)+4;refuse([&]{writer.write_tensor(&tensor,0,tensor.size);});
}
'''
        temporary_root=ROOT/'.local/state-writer-host-check';temporary_root.mkdir(parents=True,exist_ok=True)
        compiler=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin/clang++.exe'
        with tempfile.TemporaryDirectory(dir=temporary_root)as temporary:
            folder=Path(temporary);self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            cpp=folder/'check.cpp';cpp.write_text(code);binary=folder/'check.exe'
            env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(folder),TEMP=str(folder))
            compiled=subprocess.run([str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(upstream/'vendor'),
                '-I',str(upstream/'vendor/hash'),str(cpp),str(ROOT/'native/app/sha256_backend.cpp'),'-o',str(binary)],env=env,capture_output=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr.decode(errors='replace'))
            subprocess.run([str(binary)],env=env,check=True,capture_output=True)

if __name__=='__main__':unittest.main()
