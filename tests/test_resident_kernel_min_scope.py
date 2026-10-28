# SPDX-License-Identifier: MIT
"""Verify the actual minimum-plus-metadata experiment without changing OS values."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from resident_kernel_min_scope import SCOPE, entry, implementation, system_header


class KernelMinimum(unittest.TestCase):
    def test_actual_guard_and_scope_activation(self):
        retained=os.environ.get('QWEN_FROZEN_BUILD_DIR')
        if not retained:
            self.skipTest('Set QWEN_FROZEN_BUILD_DIR to retained native build evidence')
        cache=Path(retained)
        original=cache/'resident-CPU-scope-4748/app-view'
        header=system_header((original/'system_memory.h').read_text())
        phase=implementation((original/'system_memory.cpp').read_text())
        phase=phase[phase.index('#include <atomic>'):phase.index('\nnamespace qwen_app')]
        code='#include "system_memory.h"\n#include <cassert>\n'+phase+r'''
int main(){
 qwen_app::SystemMemoryObservation s{1ull<<30,16384,138739,1153,898,2974,206};
 auto refuse=[&](){try{qwen_app::qualified_system_headroom(s);return false;}catch(const std::runtime_error&){return true;}};
 assert(refuse());s.kernel_free=1154;assert(!refuse());
 bool wrong=false;try{qwen_app_activate_resident_GPU_OS_reserve();}catch(const std::runtime_error&){wrong=true;}assert(wrong);
 qwen_app_select_resident_CPU_metadata_scope(true);s.kernel_free=919;assert(!refuse());s.kernel_free=918;assert(refuse());
 qwen_app_select_resident_CPU_metadata_scope(false);s.kernel_free=1030;assert(refuse());
 qwen_app_activate_resident_GPU_OS_reserve();assert(!refuse());
 s.kernel_free=961;assert(refuse());s.kernel_free=962;assert(!refuse());
 assert(s.kernel_minimum==898&&s.kernel_reserved==206);
 s.kernel_reserved=899;assert(refuse());s.kernel_reserved=206;
 s.flexible_available=0;assert(refuse());
 wrong=false;try{qwen_app_activate_resident_GPU_OS_reserve();}catch(const std::runtime_error&){wrong=true;}assert(wrong);
 wrong=false;try{qwen_app_select_resident_CPU_metadata_scope(true);}catch(const std::runtime_error&){wrong=true;}assert(wrong);
}
'''
        temporary_root=ROOT/'.local/host-kernel-minimum-tests'
        temporary_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            folder=Path(temporary)
            self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            (folder/'system_memory.h').write_text(header)
            (folder/'resident_CPU_metadata_scope.h').write_text((original/'resident_CPU_metadata_scope.h').read_text()+
                '\nextern "C" bool qwen_app_resident_GPU_OS_reserve_active();\nextern "C" void qwen_app_activate_resident_GPU_OS_reserve();\n')
            source=folder/'scope.cpp';source.write_text(code);binary=folder/'scope.exe'
            compiler=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin/clang++.exe'
            env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(folder),TEMP=str(folder))
            subprocess.run([str(compiler),'-std=c++17','-O1',str(source),'-o',str(binary)],capture_output=True,check=True,env=env)
            subprocess.run([str(binary)],capture_output=True,check=True,env=env)
        text=entry((cache/'independent-prefix-5062/resident-comparison-independent.private.cpp').read_text())
        self.assertLess(text.index('context_floor+43'),text.index('qwen_app_activate_resident_GPU_OS_reserve();'))
        self.assertIn('OS_scope_memory.kernel_free<962',text)
        self.assertNotIn('206ull*16384',text)
        self.assertFalse(SCOPE['universal_peak_bound_established'])
        self.assertEqual(SCOPE['selected_post_context_free_pages'],962)


if __name__=='__main__':unittest.main()
