# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from preservation_batches import partition_closed_artifacts
from build_preservation_integrity import MAX_FILE,MAX_TOTAL
class PreservationTests(unittest.TestCase):
 def test_real_growing_rollback_inventory_keeps_original_bounds(self):
  sizes=[17500087,17495415,589,701789,4516,2727,2486,17515623,17540407,17597111,17625783,17370183,17412119,17433879,17468775,107911351]
  rows=[dict(remote_path=f'/data/ai/moss-test-{i}',capture=dict(bytes=n))for i,n in enumerate(sizes)]
  parts=partition_closed_artifacts(rows)
  self.assertEqual(sum(sizes),283582840);self.assertEqual([len(v)for v in parts],[15,1])
  self.assertEqual([v for part in parts for v in part],rows)
  self.assertTrue(all(sum(v['capture']['bytes']for v in part)<=MAX_TOTAL for part in parts))
 def test_invalid_global_inventory_is_not_silently_accepted(self):
  row=dict(remote_path='/data/ai/moss-test',capture=dict(bytes=1))
  with self.assertRaises(ValueError):partition_closed_artifacts([row,row])
  with self.assertRaises(ValueError):partition_closed_artifacts([dict(remote_path='x',capture=dict(bytes=MAX_FILE+1))])
  with self.assertRaises(ValueError):partition_closed_artifacts([])
if __name__=='__main__':unittest.main()
