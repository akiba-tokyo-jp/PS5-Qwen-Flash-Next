# SPDX-License-Identifier: MIT
"""A request without adjacent misses must not strand a completed native owner."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from observe_routing_winners_monitor import validate_retained_io_cohort,observer_source

class Applicability(unittest.TestCase):
 def row(self,adjacent=0,extra=0,quad=0,depth=4,flags=5):
  return dict(adjacent_calls_saved=adjacent,extra_bundled_Experts=extra,quad_batches=quad,maximum_lifetime_quad_inflight=depth,flags=flags)
 def test_completed_low_miss_request(self):
  validate_retained_io_cohort([self.row(113,125,1919),self.row(0,7,58)])
 def test_missing_execution_is_still_refused(self):
  for rows in ([],[self.row(0,7,58)],[self.row(113,0,1919)],[self.row(113,125,0)],[self.row(113,125,1919,5)],[self.row(113,125,1919,4,0)]):
   with self.subTest(rows=rows),self.assertRaises(ValueError):validate_retained_io_cohort(rows)
 def test_generated_protocol_calls_the_check_before_finish(self):
  source=observer_source();compile(source,'<finite-observer>','exec')
  self.assertLess(source.index('validate_retained_io_cohort(retained_io)'),source.index("post('/api/validation/finish'"))
if __name__=='__main__':unittest.main()
