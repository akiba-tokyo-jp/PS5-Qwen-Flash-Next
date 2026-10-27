# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from predictive_cache_result import validate_predictive_cache
class PredictiveResultTests(unittest.TestCase):
    def fixture(self):
        owner=dict(pid=123,run_id='a'*32)
        report=dict(schema='ps5-qwen-predictive-cache-result-v1',**owner,all_read_jobs_completed=True,
            actual_bank_leases_retired=True,all_model_owners_retired=True,device_ledger_live_bytes=0,speedup_qualified=False,
            proposals=4,loads=3,ineligible=1,useful_next_layer=2,unused_next_layer=1,logical_bytes=3*9830400,
            foreground_wait_ns=1,worker_read_ns=10)
        return report,owner
    def test_exercised_is_not_speed_qualification(self):
        report,owner=self.fixture();out=validate_predictive_cache(report,owner)
        self.assertTrue(out['native_predictions_exercised']);self.assertFalse(out['speedup_qualified'])
    def test_ownership_missing_traffic_and_unknown_completion_refuse(self):
        report,owner=self.fixture()
        for key in report:
            bad=copy.deepcopy(report);bad.pop(key)
            with self.assertRaises(ValueError):validate_predictive_cache(bad,owner)
        for key in ('loads','unused_next_layer','logical_bytes','ineligible'):
            bad=copy.deepcopy(report);bad[key]+=1
            with self.assertRaises(ValueError):validate_predictive_cache(bad,owner)
    def test_zero_attempt_is_explicitly_unexercised(self):
        report,owner=self.fixture()
        for key in ('proposals','loads','ineligible','useful_next_layer','unused_next_layer','logical_bytes','foreground_wait_ns','worker_read_ns'):
            report[key]=0
        self.assertFalse(validate_predictive_cache(report,owner)['native_predictions_exercised'])
if __name__=='__main__':unittest.main()
