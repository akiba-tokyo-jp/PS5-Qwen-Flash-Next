# SPDX-License-Identifier: MIT
import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from analyze_apr_recheck import analyze
from build_apr_title_probe import title_visible_path
class RecheckTests(unittest.TestCase):
    def fixture(self):
        lines=['BEGIN nonce=x','END nonce=x success=1 APR_read_submits=0 GPU_calls=0','RETURN result=0 ordinary_exit=1']
        for i in range(3):
            lines +=[f'POSIX_ACCESS index={i} opened=1 read_bytes=16 close_rc=0 control_bytes_exact=1',
                f'RESOLVE index={i} rc=-1 errno=25 canaries=1 errno_measured=1']
        lines+=['WRITER backend=public_source exact=1 commands=2 bytes=32 synthetic_ID=1'];return'\n'.join(lines)
    def test_readable_ENOTTY_is_not_a_speed_or_hardware_absence_result(self):
        r=analyze(self.fixture());self.assertTrue(r['readable_files_rejected_with_ENOTTY'])
        self.assertFalse(r['native_IO_speed_measured']);self.assertFalse(r['hardware_absence_proven']);self.assertEqual(r['APR_read_submissions'],0)
    def test_invisible_Expert_is_not_reported_as_APR_only_failure(self):
        s=self.fixture().replace('POSIX_ACCESS index=2 opened=1 read_bytes=16','POSIX_ACCESS index=2 opened=0 read_bytes=-1')
        self.assertFalse(analyze(s)['readable_files_rejected_with_ENOTTY'])
    def test_no_normal_return_is_not_complete(self):
        with self.assertRaises(ValueError):analyze(self.fixture().replace('RETURN result=0 ordinary_exit=1',''))
    def test_missing_errno_is_not_ENOTTY_evidence(self):
        with self.assertRaises(ValueError):analyze(self.fixture().replace('errno_measured=1','errno_measured=0',1))
    def test_title_mount_rebase_is_explicit(self):
        self.assertEqual(title_visible_path('/data/ai/native-moss-image-sft/PPSA99190/weights/part.bin'),'/app0/weights/part.bin')
        for path in('/data/other/part.bin','/data/ai/native-moss-image-sft/PPSA99190/../part.bin'):
            with self.assertRaises(ValueError):title_visible_path(path)
if __name__=='__main__':unittest.main()
