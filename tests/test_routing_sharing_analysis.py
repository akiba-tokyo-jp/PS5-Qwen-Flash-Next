# SPDX-License-Identifier: MIT
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_expert_routing_sharing import quality,decode_interval,whole_request,aggregate
class MeasurementTests(unittest.TestCase):
 def test_raw_format_and_answer_contents_are_separate(self):
  value=quality(2,'```json\n{"city":"Tokyo","count":3}\n```')
  self.assertTrue(value['answer_content_passed']);self.assertFalse(value['strict_format_passed']);self.assertFalse(value['output_normalized_in_application'])
  self.assertFalse(quality(1,'143')['answer_content_passed']);self.assertTrue(quality(1,'43')['strict_format_passed'])
 def test_prefill_and_EOS_are_not_decode(self):
  def counters(v):return dict(source_chunks=v,source_completed_windows=v,source_physical_read_calls=v,individual_read_calls=v,source_physical_read_bytes=v*1000,individual_read_bytes=v*1000,individual_read_errors=0,source_read_ns=v*100,process_ns=v*200,process_calls=v,individual_read_wall_ns=v*150)
  request=dict(ordinal=2,token_ids=[1,2],metrics=dict(generated_tokens=2,decode_tokens_per_second=2,total_ms=12000),completed_performance=dict(delta=counters(104)))
  points=[dict(token_id=1,generated_tokens=1,elapsed_ms=10000,completed_performance=counters(100)),dict(token_id=2,generated_tokens=2,elapsed_ms=10500,completed_performance=counters(103))]
  value=decode_interval(request,points);self.assertEqual(value['physical_bytes'],3000);self.assertEqual(value['read_calls'],3);self.assertEqual(value['accepted_transitions'],1)
  value['whole_request']=whole_request(request);summary=aggregate([value])
  self.assertEqual(summary['decode_tok_s'],2);self.assertEqual(summary['whole_request']['generated_tok_s'],2/12)
  self.assertEqual(summary['whole_request']['read_calls_per_request'],104)
  points[1]['completed_performance']['individual_read_bytes']+=1
  with self.assertRaises(ValueError):decode_interval(request,points)
if __name__=='__main__':unittest.main()
