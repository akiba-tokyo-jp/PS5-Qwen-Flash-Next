# SPDX-License-Identifier: MIT
"""Keep the production model path and the compact capacity entry distinct."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_resident_comparison import specialize


class EntryTests(unittest.TestCase):
    def test_compact_source_excludes_model_calls(self):
        source=(ROOT/'native/app/native_main.cpp').read_text()
        tail=(ROOT/'native/app/resident_comparison_tail.inc').read_text()
        ordinary=specialize(source,tail)
        self.assertIn('llama_model_load_from_file(',ordinary[ordinary.index('int main('):])
        compact=specialize(source,tail,reuse_launch_integrity=True,incremental_tables=True,
                           delegate_shader=True,gpu_initializer_calibration=True,gpu_capacity_only=True)
        main=compact[compact.index('int main('):]
        for name in ('llama_model_load_from_file(', 'engine.release()', 'llama_log_set(', 'start_native_model_sources('):
            self.assertNotIn(name,main)
        self.assertIn('#define QWEN_RESIDENT_COMPACT_GPU 1',compact)
        self.assertIn('policy.value("native_resident_GPU_capacity_only",false)!=true',main)
        self.assertIn('restore_resident_tables_incrementally()',main)
        self.assertIn('verify_resident_launch_integrity(',main)
        self.assertIn('bind_resident_shader_integrity(',main)
        self.assertIn('#include "resident_gpu_calibration.inc"',main)
        with self.assertRaises(ValueError):specialize(source,tail,gpu_capacity_only=True)

    def test_phase_local_model_keeps_actual_model_and_qualified_fixture(self):
        source=(ROOT/'native/app/native_main.cpp').read_text();tail=(ROOT/'native/app/resident_comparison_tail.inc').read_text()
        model=specialize(source,tail,reuse_launch_integrity=True,incremental_tables=True,delegate_shader=True,phase_local_model=True)
        main=model[model.index('int main('):]
        self.assertIn('llama_model_load_from_file(',main)
        self.assertIn('admit_indexed_vectors(',main)
        self.assertIn('require_resident_source_VM(after_fixture)',main)
        self.assertNotIn('admit_native_startup_memory()',main)
        self.assertIn('enable_resident_source_VM()',main)
        self.assertIn('context_floor+245',main)


if __name__=='__main__':unittest.main()
