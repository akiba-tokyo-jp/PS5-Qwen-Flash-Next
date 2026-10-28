# SPDX-License-Identifier: MIT
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from resident_upload_copy import generate


class UploadTests(unittest.TestCase):
    def test_positive_fence_and_cleanup_precede_accounting_and_checkpoint(self):
        source='''PREFIX
void ggml_vk_buffer_write_2d(vk_buffer& dst, X) {
    // Buffer is already mapped
    if(dst->memory_property_flags & vk::MemoryPropertyFlagBits::eHostVisible) {
        ORIGINAL_HOST_VISIBLE_BODY;
    }else {
        ORIGINAL_LOCK_AND_BEGIN;
        bool ret = ggml_vk_buffer_write_2d_async(subctx, dst, offset, src, spitch, dpitch, width, height, true);
        GGML_ASSERT(ret);
        ORIGINAL_END_SUBMIT_WAIT_RESET;
        ggml_vk_queue_command_pools_cleanup(dst->device);
    }
}
bool ggml_vk_buffer_read_2d_async(X) { ORIGINAL_READ; }
SUFFIX
'''
        text=generate(source)
        self.assertEqual(text.count('ORIGINAL_HOST_VISIBLE_BODY;'),1)
        self.assertEqual(text.count('ORIGINAL_END_SUBMIT_WAIT_RESET;'),1)
        self.assertIn('eHostVisible)&&!resident_copy)',text)
        self.assertLess(text.index('ORIGINAL_END_SUBMIT_WAIT_RESET;'),text.index('qwen_app_resident_GPU_upload_completed(width*height)'))
        self.assertLess(text.index('ggml_vk_queue_command_pools_cleanup(dst->device);'),text.index('++resident_upload_calls'))
        self.assertIn('staging->buffer,dst->buffer,copies',text)
        self.assertIn('resident_copy){++resident_upload_calls',text)
        self.assertEqual(text[text.index('\nbool ggml_vk_buffer_read_2d_async('):],source[source.index('\nbool ggml_vk_buffer_read_2d_async('):])
        self.assertNotIn('memcpy(dst',text)
        with self.assertRaises(ValueError):generate(source.replace('        GGML_ASSERT(ret);',''))

if __name__=='__main__':unittest.main()
