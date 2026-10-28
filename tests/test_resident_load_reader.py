# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resident_load_reader import generate
from build_resident_comparison import specialize


class ReaderTests(unittest.TestCase):
    def test_distinct_type_and_exact_one_changed_window(self):
        source=(ROOT/'native/app/mapped_source.h').read_text();text=generate(source)
        self.assertIn('class ResidentMappedSourceReader {',text)
        self.assertNotIn('class MappedSourceReader {',text)
        self.assertEqual(text.count('resident_load_limit_ - skip'),1)
        self.assertIn('return {fd,scratch_,model_read_window,0}',text)
        native=(ROOT/'native/app/native_main.cpp').read_text();tail=(ROOT/'native/app/resident_comparison_tail.inc').read_text()
        model=specialize(native,tail,reuse_launch_integrity=True,incremental_tables=True,
                         delegate_shader=True,phase_local_model=True,model_load_window_bytes=1<<20)
        self.assertIn('require_resident_load_window(policy)',model)
        self.assertIn('last_model_load_error',model)
        existing=specialize(native,tail,reuse_launch_integrity=True,incremental_tables=True,
            delegate_shader=True,phase_local_model=True,model_load_window_bytes=1<<20,existing_window_pricing=True)
        self.assertIn('require_resident_existing_source_VM(after_fixture)',existing)
        self.assertIn('context_floor+43',existing)
        self.assertIn('require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)',existing)
        self.assertIn('require_resident_source_VM(qwen_app::admit_native_system_memory())',
            specialize(native,tail,reuse_launch_integrity=True,incremental_tables=True,delegate_shader=True,
                phase_local_model=True,postloader_integrity=True,existing_window_pricing=True))
        with self.assertRaises(ValueError):specialize(native,tail,model_load_window_bytes=1<<20)


if __name__=='__main__':unittest.main()
