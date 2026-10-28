# SPDX-License-Identifier: MIT
"""Exercise the actual isolated reserve selector and irreversible phases."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from resident_OS_reserve_scope import entry, implementation, source_header, system_header


class OSReserve(unittest.TestCase):
    def test_actual_header_keeps_setup_and_complete_OS_reserve(self):
        cache = Path('D:/PS5-AI/qwen-flash-next/build')
        view = cache / 'resident-CPU-scope-4748/app-view'
        generated = system_header((view / 'system_memory.h').read_text())
        phase = implementation((view / 'system_memory.cpp').read_text())
        phase = phase[phase.index('#include <atomic>'):phase.index('\nnamespace qwen_app')]
        code = r'''
#include "system_memory.h"
#include <cassert>
''' + phase + r'''
int main(){
    qwen_app::SystemMemoryObservation s{1ull<<30,16384,138739,1153,898,2974,206};
    auto refuses=[&](){try{qwen_app::qualified_system_headroom(s);return false;}catch(const qwen_app::KernelMemoryPressure&){return true;}};
    assert(refuses());
    bool wrong=false;try{qwen_app_activate_resident_GPU_OS_reserve();}catch(const std::runtime_error&){wrong=true;}assert(wrong);
    qwen_app_select_resident_CPU_metadata_scope(true);s.kernel_free=919;assert(!refuses());s.kernel_free=918;assert(refuses());
    qwen_app_select_resident_CPU_metadata_scope(false);s.kernel_free=1153;assert(refuses());s.kernel_free=1154;assert(!refuses());
    qwen_app_activate_resident_GPU_OS_reserve();s.kernel_free=1103;assert(refuses());s.kernel_free=1104;assert(!refuses());
    s.kernel_reserved=300;s.kernel_free=1197;assert(refuses());s.kernel_free=1198;assert(!refuses());
    wrong=false;try{qwen_app_activate_resident_GPU_OS_reserve();}catch(const std::runtime_error&){wrong=true;}assert(wrong);
    wrong=false;try{qwen_app_select_resident_CPU_metadata_scope(true);}catch(const std::runtime_error&){wrong=true;}assert(wrong);
    s.page_size=4096;wrong=false;try{qwen_app::qualified_system_headroom(s);}catch(const std::runtime_error&){wrong=true;}assert(wrong);
}
'''
        temporary_root = ROOT / '.local/host-OS-reserve-tests'
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder:
            folder = Path(folder)
            self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            (folder / 'system_memory.h').write_text(generated)
            (folder / 'resident_CPU_metadata_scope.h').write_text((view / 'resident_CPU_metadata_scope.h').read_text() +
                '\nextern "C" bool qwen_app_resident_GPU_OS_reserve_active();\nextern "C" void qwen_app_activate_resident_GPU_OS_reserve();\n')
            source = folder / 'scope.cpp'
            binary = folder / 'scope.exe'
            source.write_text(code)
            compiler = ROOT.parents[1] / 'toolchain/msys-clang64/clang64/bin/clang++.exe'
            env = dict(os.environ, PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''), TMP=str(folder), TEMP=str(folder))
            subprocess.run([str(compiler), '-std=c++17', '-O1', str(source), '-o', str(binary)], check=True, capture_output=True, env=env)
            subprocess.run([str(binary)], check=True, capture_output=True, env=env)
        prefix = (cache / 'independent-prefix-5062/resident-comparison-independent.private.cpp').read_text()
        specialized = entry(prefix)
        self.assertLess(specialized.index('context_floor+43'), specialized.index('qwen_app_activate_resident_GPU_OS_reserve();'))
        self.assertIn('universal_peak_bound_established', specialized)
        self.assertIn('qwen_app_resident_GPU_OS_reserve_active()', source_header((view/'resident_phase_vm.h').read_text()))


if __name__ == '__main__':
    unittest.main()
