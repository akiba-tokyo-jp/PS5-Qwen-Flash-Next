# SPDX-License-Identifier: MIT
"""Exercise independent entries and the actual staging retirement function."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from resident_independent_scopes import bound_reference, release_completed_upload_entry, release_completed_upload_source, separate_combined


class IndependentScopes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained = os.environ.get('QWEN_FROZEN_BUILD_DIR')
        if not retained:
            raise unittest.SkipTest('Set QWEN_FROZEN_BUILD_DIR to retained native build evidence')
        cls.cache = Path(retained)
        cls.combined = (cls.cache / 'resident-combined-retained-CPU-4840/resident-comparison-retained-CPU.private.cpp').read_text()
        cls.upload = (cls.cache / 'resident-refill-GPU-upload-3990/vulkan-buffer-upload.private.cpp').read_text()

    def test_original_cohorts_have_separate_complete_retirement(self):
        for kind, requests in (('predictive', 10), ('prefix', 9)):
            generated = release_completed_upload_entry(bound_reference(separate_combined(self.combined, kind)))
            main = generated[generated.index('int main(int argc, char ** argv)'):]
            self.assertEqual(main.count('llama_model_load_from_file('), 1)
            self.assertEqual(main.count('std::vector<float> reference_logits('), 1)
            self.assertIn('resident_reference_rows=23', main)
            self.assertIn('all_model_source_device_owners_positively_retired', main)
            self.assertNotIn('retained_prefix_', main)
            self.assertIn('context_floor+43', main)
            self.assertIn('GPU_or_ordinary_floor_changes', main)
            self.assertIn('qwen_native_driver_begin();\n        const auto upload_retired_bytes=', main)
            self.assertIn('qwen_app_release_completed_upload_staging();\n        qwen_native_driver_complete();', main)
            self.assertIn('256,32', main)
            self.assertEqual('forced_rejection_passed' in main, kind == 'predictive')
            self.assertEqual('prefix_comparison=true' in main, kind == 'prefix')
            self.assertIn('std::array<CompletedRouteEvidence,' + str(requests) + '>', main)
        for transform, source in ((bound_reference, self.combined + self.combined),
                (release_completed_upload_entry, self.combined + self.combined),
                (release_completed_upload_source, self.upload + self.upload)):
            with self.assertRaises(ValueError):
                transform(source)

    def test_actual_destructor_requires_positive_exclusive_completed_owner(self):
        generated = release_completed_upload_source(self.upload)
        begin = generated.index('static vk_device_ref resident_completed_upload_device;')
        end = generated.index('static void * portable_aligned_malloc', begin)
        function = generated[begin:end]
        stub = r'''
#include <atomic>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <cstdint>
#include <cassert>
static unsigned destructions=0;
struct vk_buffer_struct {uint64_t size; explicit vk_buffer_struct(uint64_t n):size(n){} ~vk_buffer_struct(){++destructions;}};
struct vk_device_struct {std::recursive_mutex mutex;std::shared_ptr<vk_buffer_struct> sync_staging;};
using vk_device_ref=std::weak_ptr<vk_device_struct>;
static std::atomic<uint64_t> resident_upload_calls{0};
static void ggml_vk_destroy_buffer(std::shared_ptr<vk_buffer_struct>&v){v.reset();}
'''
        checks = r'''
int main(){
    auto refuses=[](){try{(void)qwen_app_release_completed_upload_staging();return false;}catch(const std::runtime_error&){return true;}};
    assert(refuses());
    resident_upload_started=2;resident_upload_calls=1;assert(refuses());
    resident_upload_calls=2;assert(refuses());
    auto device=std::make_shared<vk_device_struct>();resident_completed_upload_device=device;
    assert(refuses());
    device->sync_staging=std::make_shared<vk_buffer_struct>(64u<<20);
    auto shared=device->sync_staging;assert(refuses());assert(destructions==0);shared.reset();
    device->sync_staging->size=0;assert(refuses());assert(destructions==0);
    device->sync_staging->size=(64u<<20)+1;assert(refuses());assert(destructions==0);
    device->sync_staging->size=64u<<20;
    assert(qwen_app_release_completed_upload_staging()==(64u<<20));
    assert(!device->sync_staging&&destructions==1&&resident_upload_calls==2);
    assert(refuses());assert(destructions==1);
}
'''
        compiler = ROOT.parents[1] / 'toolchain/msys-clang64/clang64/bin/clang++.exe'
        temporary_root = ROOT / '.local/host-upload-retirement-tests'
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(temporary_root.resolve()))
            source = Path(temporary) / 'retire.cpp'
            binary = Path(temporary) / 'retire.exe'
            source.write_text(stub + function + checks)
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''),
                TMP=temporary, TEMP=temporary)
            subprocess.run([str(compiler), '-std=c++17', '-O1', str(source), '-o', str(binary)], check=True, capture_output=True, env=env)
            subprocess.run([str(binary)], check=True, capture_output=True, env=env)
        # The original fenced upload remains before the registered completion.
        upload = generated[generated.index('void ggml_vk_buffer_write_2d('):]
        self.assertLess(upload.index('waitForFences('), upload.index('resident_completed_upload_device=dst->device'))
        self.assertLess(upload.index('ggml_vk_queue_command_pools_cleanup('), upload.index('resident_completed_upload_device=dst->device'))


if __name__ == '__main__':
    unittest.main()
