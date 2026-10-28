# SPDX-License-Identifier: MIT
"""Execute the actual table permit logic at the observed failed CPU boundary."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resident_table_admission import incremental_header
from resident_postload_pricing import entry


class CPUAdmission(unittest.TestCase):
    def test_actual_incremental_permit_and_postload_order(self):
        original=(ROOT/'native/app/resident_incremental_tables.h').read_text()
        generated=incremental_header(original)
        start=generated.index('struct ResidentTableMemory {')
        end=generated.index('\nstatic voidpf resident_table_allocate',start)
        actual=generated[start:end]
        code=r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <cassert>
static bool CPU=true;
static bool qwen_app_resident_CPU_metadata_scope_active(){return CPU;}
namespace qwen_app {
struct KernelMemoryPressure:std::runtime_error{KernelMemoryPressure():std::runtime_error("pressure") {}};
struct Memory{uint64_t kernel_free=1152,kernel_minimum=898,kernel_reserved=206,page_size=16384,flexible_available=436207616;}memory;
static Memory admit_native_system_memory(){return memory;}
'''+actual+r'''
}
int main(){using namespace qwen_app;
 ResidentTableMemory s;assert(s.permit()&&!s.memory_refused&&!s.fault);
 memory.kernel_free=938;s={};assert(!s.permit()&&s.memory_refused&&!s.fault);
 s={};assert(s.permit(19));memory.kernel_free=937;s={};assert(!s.permit(19)&&s.memory_refused);
 CPU=false;memory.kernel_free=1152;s={};assert(!s.permit()&&s.memory_refused);
 memory.kernel_free=1174;s={};assert(s.permit());
 CPU=true;memory.kernel_free=1152;memory.flexible_available=(264ull<<20)-1;s={};assert(!s.permit()&&s.fault);
}
'''
        temp_root=ROOT/'.local/host-table-admission-tests';temp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root)as temporary:
            folder=Path(temporary);self.assertTrue(folder.resolve().is_relative_to(temp_root.resolve()))
            source=folder/'test.cpp';source.write_text(code);binary=folder/'test.exe'
            compiler=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin/clang++.exe'
            env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(folder),TEMP=str(folder))
            subprocess.run([str(compiler),'-std=c++17','-O1',str(source),'-o',str(binary)],capture_output=True,check=True,env=env)
            subprocess.run([str(binary)],capture_output=True,check=True,env=env)
        cache=Path('D:/PS5-AI/qwen-flash-next/build')
        for kind,number in (('prefix',5062),('predictive',5064)):
            text=entry((cache/f'independent-{kind}-{number}/resident-comparison-independent.private.cpp').read_text())
            self.assertLess(text.index('qwen_app_release_completed_upload_staging();'),text.index('qwen_app_activate_resident_GPU_OS_reserve();'))
            self.assertLess(text.index('qwen_app_activate_resident_GPU_OS_reserve();'),text.index('context_floor+43'))
            self.assertIn('OS_scope_memory.kernel_free<1005',text)
        self.assertIn('std::memcmp(digest,t.sha256',generated)
        self.assertIn('result.protection_rc=mprotect(p.begin,end-begin,PROT_READ)',generated)


if __name__=='__main__':unittest.main()
