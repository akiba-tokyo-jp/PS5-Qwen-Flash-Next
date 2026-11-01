# SPDX-License-Identifier: MIT
"""Prevent unsupported APIs and host codec results becoming false speed claims."""
import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('analysis',Path(__file__).resolve().parents[1]/'tools/analyze_ampr_kraken.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class AnalysisTests(unittest.TestCase):
    def test_SDK_success_is_not_erased_by_failed_module_lookup(self):
        names=('pread','sceKernelAioSubmitReadCommands',*a.APR,*('writer'+str(i)for i in range(6)))
        log='\n'.join('SYMBOL name='+n+' SDK_found='+str(int(i<8))+' kernel_found=0 kernel_web_found=0 AMPR_found=0'for i,n in enumerate(names))
        log+='\n'+'\n'.join('MODULE index='+str(i)+' name=module present=0 rc=-1 errno=22'for i in range(3))+'\nEND nonce=x success=1 current_file_hashes=6 '
        r=a.capability(log);self.assertTrue(r['all_APR_symbols_resolved']);self.assertTrue(r['module_handle_lookup_inconclusive'])
        self.assertFalse(r['symbol_presence_proves_callable_backend'])
    def test_three_unsupported_paths_are_context_qualified(self):
        log='\n'.join(f'APR_RESOLVE index={i} rc=-1 errno=45 canaries=1'for i in range(3))+'\nEND nonce=x success=1 samples=16 '
        r=a.paths(log);self.assertTrue(r['current_path_backend_unsupported']);self.assertFalse(r['system_wide_hardware_absence_proven'])
        with self.assertRaises(ValueError):a.paths(log.replace('canaries=1','canaries=0',1))
    def test_missing_completion_is_rejected(self):
        with self.assertRaises(ValueError):a.paths('APR_RESOLVE index=0 rc=0 errno=0 canaries=1')
    def test_host_byte_gain_is_not_model_speed(self):
        row=dict(sample=0,round_trip_exact=True,hardware_decoder_tested=False,original_padded_bytes=1540096,
            padded_bytes=1474560,logical_bytes=1536000,compressed_payload_bytes=1465000,chunk=65536,
            block_count=24,independent_Expert_read_commands=1,host_decode_ms=10)
        r=a.chunks([row]);self.assertAlmostEqual(r['physical_saving_percent'],4.25531914893617)
        self.assertEqual(r['proposed_Expert_read_commands'],1);self.assertFalse(r['PS5_decode_or_model_speed_measured'])
if __name__=='__main__':unittest.main()
