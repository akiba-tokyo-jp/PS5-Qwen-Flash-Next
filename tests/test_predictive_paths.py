# SPDX-License-Identifier: MIT
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_predictive_paths import (CrossLayerForecast, PredictiveCache,
    cache_screen, choose_cost_width, past_draft, speculative_screen,conditional_width_two_traffic)
from replay_expert_routes import RouteCache


class PredictivePathsTests(unittest.TestCase):
    def test_baseline_and_selected_set(self):
        native,independent=RouteCache(),PredictiveCache()
        for n in range(240):
            row=dict(layer=n%48,tokens=1,ids=[(n*7+j)%512 for j in range(10)])
            actual=native.step(row)
            self.assertEqual({k:actual[k]for k in ('hits','misses','unique')},independent.step(row))
            self.assertEqual(native.mapping,independent.mapping)
            self.assertTrue({row['layer']*512+e for e in row['ids']}<=independent.mapping.keys())

    def test_prefetch_preserves_pinned_and_counts_load(self):
        cache=PredictiveCache()
        for layer in range(5):cache.step(dict(layer=layer,tokens=1,ids=list(range(10))))
        pinned={4*512+e for e in range(10)}
        loaded=cache.prefetch(5,[40,41],pinned)
        self.assertEqual(len(loaded),2)
        self.assertTrue(pinned<=cache.mapping.keys())
        with self.assertRaises(ValueError):cache.prefetch(5,[1,2,3],pinned)
        with self.assertRaises(ValueError):cache.prefetch(5,[1,1],pinned)

    def test_predict_then_observe_and_bounded_contexts(self):
        predictor=CrossLayerForecast()
        previous=dict(layer=0,tokens=1,ids=list(range(10)))
        actual=dict(layer=1,tokens=1,ids=list(range(40,50)))
        self.assertEqual(predictor.predict(previous,1,{},2),[])
        predictor.observe(previous,actual)
        self.assertEqual(predictor.predict(previous,1,{},2),[])
        predictor.observe(previous,actual)
        before=copy.deepcopy(predictor.table)
        self.assertEqual(predictor.predict(previous,1,{},2),[40,41])
        self.assertEqual(predictor.table,before)
        self.assertEqual(predictor.predict(previous,1,{512+40:0},2),[41,42])
        for n in range(600):
            p=dict(layer=0,tokens=1,ids=[n%512,n//512,*range(2,10)])
            predictor.observe(p,actual)
        self.assertLessEqual(len(predictor.table),512)
        self.assertTrue(all(len(v['counts'])<=16 for v in predictor.table.values()))

    def test_wrong_predictions_count_as_traffic(self):
        rows=[]
        for token in range(8):
            rows.extend([dict(layer=layer,tokens=1,ids=list(range(10))) for layer in range(48)])
        traces=[dict(records=rows)]*3
        measured=cache_screen(traces,prefetch=2)
        for row in measured:
            self.assertEqual(row['total_deliveries'],row['misses']+row['speculative_loads'])
            self.assertEqual(row['speculative_loads'],row['useful_at_next_layer']+row['unused_at_next_layer'])

    def test_cost_includes_all_widths_and_keeps_ties_small(self):
        def candidates(seconds):
            return [dict(width=w,expected_committed=w,seconds=s,available=True)for w,s in zip((1,2,4),seconds)]
        self.assertEqual(choose_cost_width(candidates((1,2,4))),1)
        self.assertEqual(choose_cost_width(candidates((1,1,4))),2)
        self.assertEqual(choose_cost_width(candidates((1,2,1))),4)
        for value in (0,-1,math.inf,math.nan):
            bad=candidates((1,2,4));bad[1]['seconds']=value
            with self.assertRaises(ValueError):choose_cost_width(bad)

    def test_future_suffix_cannot_change_selector(self):
        ids=[1,2,1,2,1,2,1,2,1,2,1,2]
        groups=[]
        for i in range(len(ids)+1):
            groups.extend(dict(layer=l,tokens=4 if i==0 else 1,ids=list(range(10))*(4 if i==0 else 1))for l in range(48))
        trace=dict(records=groups)
        result=dict(token_ids=ids,metrics=dict(prompt_tokens=4))
        original=speculative_screen([trace],[result])[0]
        modified=copy.deepcopy(trace);changed=copy.deepcopy(result)
        changed['token_ids'][7:]=[90,91,92,93,94]
        for row in modified['records'][(7+1)*48:]:row['ids']=[x+40 for x in row['ids']]
        alternate=speculative_screen([modified],[changed])[0]
        self.assertEqual(original['decisions'][:7],alternate['decisions'][:7])

    def test_drafts_use_only_supplied_history(self):
        self.assertEqual(past_draft([1,2,3,1,2,3,1,2],1),[3])
        self.assertEqual(past_draft([1,2,3,1,2],1),[])
        with self.assertRaises(ValueError):past_draft([1,-1],1)

    def test_unknown_rejected_branch_is_never_an_ordinary_route(self):
        ids=[1,2,3,1,2,3,1,99,0]
        rows=[]
        for i in range(len(ids)+1):
            rows.extend(dict(layer=l,tokens=4 if i==0 else 1,ids=list(range(10))*(4 if i==0 else 1))for l in range(48))
        trace=dict(records=rows,uploaded_bytes=1)
        result=dict(token_ids=ids,metrics=dict(prompt_tokens=4))
        report=conditional_width_two_traffic([trace],[result])
        self.assertFalse(report['complete_counterfactual'])
        self.assertTrue(report['rejected_branch_routes_unknown'])
        self.assertIsNone(report['aggregate_bytes'])


if __name__=='__main__':unittest.main()
