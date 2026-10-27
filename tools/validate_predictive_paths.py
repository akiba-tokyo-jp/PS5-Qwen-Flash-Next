#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Causal original-route screens; never execute a learned model or a PS5 call."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from expert_route_result import validate_routes
from replay_expert_routes import RouteCache

EXPERT_BYTES = 9830400
LAYERS = 48
EXPERTS = 512


def record(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def bound(row):
    path = Path(row['path'])
    if record(path) != row or path.stat().st_size > 2 << 20:
        raise ValueError('Immutable bounded original evidence is required')
    return path


class PredictiveCache(RouteCache):
    """Fixed-size causal metadata; not connected to actual bank ownership."""
    def __init__(self, deadline=False):
        super().__init__()
        self.deadline = deadline
        self.last = [0] * (LAYERS * EXPERTS)
        self.gap = [48.0] * (LAYERS * EXPERTS)
        self.repeats = [0] * (LAYERS * EXPERTS)

    def victim(self, protected):
        available = [n for n, key in enumerate(self.keys) if key not in protected]
        if not available:
            raise ValueError('No victim preserves all live actual selections')
        if not self.deadline:
            return min(available, key=lambda n: (self.counts[self.keys[n]], self.recency[self.keys[n]]))
        def rank(n):
            key = self.keys[n]
            due = self.last[key] + self.gap[key]
            # An expired forecast is stale. It is not automatically moved into
            # the future using the current evaluation's next actual demand.
            return (due <= self.tick, due if due > self.tick else self.tick-due,
                    -self.counts[key], -self.recency[key])
        return max(available, key=rank)

    def insert(self, key, protected):
        if key in self.mapping:
            return False
        slot = self.keys.index(-1) if -1 in self.keys else self.victim(protected)
        if self.keys[slot] != -1:
            del self.mapping[self.keys[slot]]
        self.keys[slot] = key
        self.mapping[key] = slot
        return True

    def prefetch(self, layer, experts, pinned):
        if len(experts) > 2 or len(set(experts)) != len(experts):
            raise ValueError('At most two distinct speculative slots are allowed')
        keys = [layer * EXPERTS + e for e in experts]
        if any(not 0 <= e < EXPERTS for e in experts) or not 0 <= layer < LAYERS:
            raise ValueError('Original layer/expert bounds are required')
        protected = set(pinned)
        loaded = []
        for key in keys:
            if self.insert(key, protected):
                loaded.append(key)
            protected.add(key)
        return loaded

    def step(self, row):
        selected = sorted(set(row['ids']))
        layer = row['layer']
        if not 0 <= layer < LAYERS or not 10 <= len(selected) <= 40 or any(not 0 <= e < EXPERTS for e in selected):
            raise ValueError('Complete original active selections are required')
        active = {layer * EXPERTS + e for e in selected}
        self.tick += 1
        for key in active:
            if self.last[key]:
                distance = self.tick - self.last[key]
                self.gap[key] = (3 * self.gap[key] + distance) / 4
                self.repeats[key] += 1
            self.last[key] = self.tick
            self.counts[key] = min(self.counts[key] + 1, 2**32-1)
            self.recency[key] = self.tick
        self.routes += 1
        if self.routes == 4096:
            self.counts = [n // 2 for n in self.counts]
            self.routes = 0
        hits = sum(key in self.mapping for key in active)
        for e in selected:
            self.insert(layer * EXPERTS + e, active)
        assert active <= self.mapping.keys()
        assert len(self.mapping) <= 53 and all(self.keys[s] == k for k, s in self.mapping.items())
        return dict(hits=hits, misses=len(active)-hits, unique=len(active))


class CrossLayerForecast:
    """Past-only two-anchor transition table, capped at 512 contexts/16 targets."""
    def __init__(self):
        self.table = {}
        self.tick = 0

    @staticmethod
    def key(previous, layer):
        if previous is None or previous['tokens'] != 1 or previous['layer']+1 != layer:
            return None
        return (layer, *previous['ids'][:2])

    def predict(self, previous, layer, resident, limit):
        if limit not in (0, 1, 2):
            raise ValueError('A bounded speculative slot count is required')
        entry = self.table.get(self.key(previous, layer))
        if not limit or entry is None or entry['seen'] < 2:
            return []
        ranked = sorted(entry['counts'], key=lambda e: (-entry['counts'][e], e))
        return [e for e in ranked if entry['counts'][e] * 4 >= entry['seen'] * 3
                and layer * EXPERTS + e not in resident][:limit]

    def observe(self, previous, row):
        key = self.key(previous, row['layer'])
        if key is None or row['tokens'] != 1:
            return
        self.tick += 1
        if key not in self.table:
            if len(self.table) == 512:
                del self.table[min(self.table, key=lambda k: (self.table[k]['at'], k))]
            self.table[key] = dict(seen=0, counts={}, at=self.tick)
        entry = self.table[key]
        if entry['seen'] >= 1024:
            entry['seen'] //= 2
            entry['counts'] = {e: n//2 for e, n in entry['counts'].items() if n//2}
        entry['seen'] += 1
        entry['at'] = self.tick
        for e in row['ids']:
            entry['counts'][e] = entry['counts'].get(e, 0) + 1
        # Deterministic fixed storage; eviction affects only predictions.
        keep = sorted(entry['counts'], key=lambda e: (-entry['counts'][e], e))[:16]
        entry['counts'] = {e: entry['counts'][e] for e in keep}


def cache_screen(records, *, deadline=False, prefetch=0):
    cache = predictor = None
    result = []
    for ordinal, trace in enumerate(records):
        if ordinal < 2:
            cache, predictor = PredictiveCache(deadline), CrossLayerForecast()
        previous = None
        sums = dict(hits=0, misses=0, unique=0, speculative_loads=0,
                    useful_at_next_layer=0, unused_at_next_layer=0, speculative_victims=0)
        for row in trace['records']:
            choices = predictor.predict(previous, row['layer'], cache.mapping, prefetch) if row['tokens']==1 else []
            pinned = set() if previous is None else {previous['layer']*EXPERTS+e for e in previous['ids']}
            before = set(cache.mapping)
            loaded = cache.prefetch(row['layer'], choices, pinned)
            sums['speculative_loads'] += len(loaded)
            sums['speculative_victims'] += len(before-set(cache.mapping))
            useful = sum(key % EXPERTS in row['ids'] for key in loaded)
            sums['useful_at_next_layer'] += useful
            sums['unused_at_next_layer'] += len(loaded)-useful
            step = cache.step(row)
            for key in ('hits','misses','unique'):
                sums[key] += step[key]
            # The first access to this actual row by the predictor is AFTER its
            # prediction, speculative fills and scored demand have completed.
            predictor.observe(previous, row)
            previous = row
        sums['total_deliveries'] = sums['misses']+sums['speculative_loads']
        sums['logical_expert_bytes'] = sums['total_deliveries']*EXPERT_BYTES
        result.append(sums)
    return result


def past_draft(history, count, consistent=True):
    """Look up a bounded continuation in committed history; no target suffix."""
    if count not in (1,3) or len(history)>32 or any(type(t)is not int or not 0<=t<262144 for t in history):
        raise ValueError('Bounded original token history is required')
    if not history:
        return []
    for n in range(min(4,len(history)-1),0,-1):
        matches = [i for i in range(len(history)-n) if history[i:i+n]==history[-n:]]
        if not matches:
            continue
        next_ids = [history[i+n] for i in matches]
        if consistent and (len(matches)<2 or len(set(next_ids))!=1):
            continue
        start = matches[-1]+n
        return history[start:min(start+count,len(history))]
    return []


def choose_cost_width(candidates):
    best = 0.0
    width = 1
    for expected,row in zip((1,2,4),candidates):
        if (row['width']!=expected or not math.isfinite(row['expected_committed']) or
                not math.isfinite(row['seconds']) or not 1<=row['expected_committed']<=expected or row['seconds']<=0):
            raise ValueError('Finite bounded candidate costs are required')
        if not row['available']:
            if expected==1:raise ValueError('Ordinary control is required')
            continue
        rate=row['expected_committed']/row['seconds']
        if rate>best:
            best,width=rate,expected
    return width


def process_groups(trace):
    rows=trace['records']
    return [rows[n:n+48] for n in range(0,len(rows),48)]


def conditional_width_two_traffic(records,results):
    """Full trace regrouping, conditional on unchanged routes in target batches.

    Unknown rejected-token routes terminate the calculation rather than being
    replaced with the ordinary greedy route. This never performs model math.
    """
    cache=None;requests=[]
    for ordinal,(trace,result)in enumerate(zip(records,results)):
        if ordinal<2:cache=RouteCache()
        groups=process_groups(trace);prefill=(result['metrics']['prompt_tokens']+3)//4
        ids=result['token_ids'];decode=groups[prefill:]
        misses=0;decode_misses=0;attempts=0;i=0;decisions=[]
        for group in groups[:prefill]:misses+=sum(cache.step(r)['misses']for r in group)
        while i<len(decode):
            draft=past_draft(ids[:i+1],1)if i+1<len(ids)else[]
            decisions.append(dict(position=i,draft=draft))
            if draft:
                attempts+=1
                if draft[0]!=ids[i+1]:
                    return dict(complete_counterfactual=False,rejected_branch_routes_unknown=True,
                                first_unknown_request=ordinal,position=i,aggregate_bytes=None,
                                native_batch_arithmetic_qualified=False)
            width=2 if draft else 1
            if i+width>len(decode):raise ValueError('Counterfactual target process is missing')
            for layer in range(48):
                row=dict(layer=layer,tokens=width,ids=sum((decode[n][layer]['ids']for n in range(i,i+width)),[]))
                count=cache.step(row)['misses'];misses+=count;decode_misses+=count
            i+=width
        requests.append(dict(ordinal=ordinal,attempts=attempts,decisions=decisions,
            all_drafts_match_saved_greedy_tokens=True,total_expert_deliveries=misses,
            decode_expert_deliveries=decode_misses,logical_expert_bytes=misses*EXPERT_BYTES))
    external=sum(r['logical_expert_bytes']for r in requests[1:])
    reference=sum(r['uploaded_bytes']for r in records[1:])
    return dict(complete_counterfactual=True,rejected_branch_routes_unknown=False,requests=requests,
        external_logical_expert_bytes=external,reference_external_bytes=reference,
        external_byte_reduction_fraction=(1-external/reference)if reference else None,
        assumes_original_per_token_routes_under_batching=True,
        excludes_checkpoint_and_verification_time=True,native_batch_arithmetic_qualified=False,
        native_speed_qualified=False)


def speculative_screen(records, results):
    """Metadata opportunities only; rejected-branch target routes are unknown."""
    summaries=[]
    cache=None
    for ordinal,(trace,result) in enumerate(zip(records,results)):
        ids=result['token_ids']
        groups=process_groups(trace)
        prefill=(result['metrics']['prompt_tokens']+3)//4
        decode=groups[prefill:]
        if len(decode) not in (len(ids),len(ids)-1):
            raise ValueError('Saved ordinary target processes do not bind emitted tokens')
        # Reproduce the ordinary cold arithmetic/cold external/retained external
        # cache lifetimes. Only local candidate costs are evaluated here.
        if ordinal<2:cache=RouteCache()
        for group in groups[:prefill]:
            for row in group:cache.step(row)
        known={}
        totals=dict(eligible_positions=0, fixed_two_proposals=0, fixed_two_matches=0,
                    adaptive_widths={'1':0,'2':0,'4':0}, unknown_rejected_branch_routes=0,
                    correct_windows=0, local_serial_deliveries=0, local_union_deliveries=0,
                    local_source_bytes_saved=0, predicted_route_observations=0)
        choices=[]
        for i,actual in enumerate(decode):
            pending=ids[i] if i<len(ids) else None
            history=ids[:i+1]
            available=i+1<len(ids)
            drafts={2:past_draft(history,1),4:past_draft(history,3)}
            # Decisions can consult only known route associations from earlier
            # processed committed tokens, not the current actual row or suffix.
            candidates=[]
            for width in (1,2,4):
                tokens=[pending]+drafts.get(width,[])
                ready=all(t in known for t in tokens) and len(tokens)==width and available
                base=1.0
                if ready:
                    misses=0
                    for layer in range(48):
                        union=set().union(*(set(known[t][layer])for t in tokens))
                        misses+=sum(layer*512+e not in cache.mapping for e in union)
                    # Zero checkpoint overhead is an explicitly optimistic
                    # initial screen. Expected acceptance uses only duplicate
                    # historical n-gram evidence, not a future match test.
                    seconds=max(1,misses)*EXPERT_BYTES/1939000000 + .18*width
                else:seconds=base
                expected=1 if width==1 else 1+sum(.5**j for j in range(1,width))
                candidates.append(dict(width=width,expected_committed=expected,seconds=seconds,
                    available=width==1 or ready))
            # A repeated token supplies an ordinary route estimate too.
            if pending in known:
                miss=sum(layer*512+e not in cache.mapping for layer in range(48)for e in set(known[pending][layer]))
                candidates[0]['seconds']=max(1,miss)*EXPERT_BYTES/1939000000+.18
            selected=choose_cost_width(candidates)
            totals['adaptive_widths'][str(selected)]+=1
            if available:
                totals['eligible_positions']+=1
                draft=drafts[2]
                if draft:
                    totals['fixed_two_proposals']+=1
                    matches=draft[0]==ids[i+1]
                    totals['fixed_two_matches']+=matches
                    if not matches:totals['unknown_rejected_branch_routes']+=1
                # Correct-width-two local union is an opportunity, not an
                # executed candidate cache lifetime or target batch arithmetic.
                if draft and draft[0]==ids[i+1] and i+1<len(decode):
                    serial=copy.deepcopy(cache);joint=copy.deepcopy(cache)
                    serial_misses=sum(serial.step(row)['misses']for group in decode[i:i+2]for row in group)
                    joint_misses=0
                    for layer in range(48):
                        row=dict(layer=layer,tokens=2,ids=decode[i][layer]['ids']+decode[i+1][layer]['ids'])
                        joint_misses+=joint.step(row)['misses']
                    totals['correct_windows']+=1
                    totals['local_serial_deliveries']+=serial_misses
                    totals['local_union_deliveries']+=joint_misses
                    totals['local_source_bytes_saved']+=(serial_misses-joint_misses)*EXPERT_BYTES
            choices.append(dict(position=i,pending=pending,drafts=drafts,selected_width=selected,
                                predicted_costs=candidates))
            if pending is not None:
                known[pending]=[row['ids'][:]for row in actual]
            for row in actual:cache.step(row)
            totals['predicted_route_observations']+=1
        summaries.append(dict(ordinal=ordinal,**totals,decisions=choices,
            checkpoint_overhead_in_selector_seconds=0,
            fixed_compute_per_target_seconds_assumption=.18,
            historical_effective_source_bytes_per_second_assumption=1939000000,
            local_windows_overlap_and_cannot_be_summed_as_request_savings=True,
            rejected_branch_IO_and_eviction_cost_unknown=True,
            actual_width_two_or_four_arithmetic_qualified=False,native_speed_qualified=False))
    return summaries


def run(manifest):
    records=[];results=[];inputs=[]
    for ordinal,row in enumerate(manifest['requests']):
        rp,tp=bound(row['routes']),bound(row['result']);inputs.extend((row['routes'],row['result']))
        r,t=json.loads(rp.read_text()),json.loads(tp.read_text())
        validate_routes(r,t,width=4,pid=t['pid'],run_id=t['run_id'],cold=ordinal<2)
        records.append(r);results.append(t)
    if len(records)!=3:raise ValueError('Complete arithmetic/cold/retained source evidence is required')
    variants=[]
    for deadline,prefetch in ((False,0),(True,0),(False,1),(False,2),(True,1),(True,2)):
        rows=cache_screen(records,deadline=deadline,prefetch=prefetch)
        if not variants:
            for row,native in zip(rows,records):
                if any(row[k]!=native['cache_'+k]for k in ('hits','misses')) or row['unique']!=native['unique_selected_experts']:
                    raise ValueError('Independent baseline differs from completed native cache counters')
        baseline=sum(r['logical_expert_bytes']for r in variants[0]['requests'][1:])if variants else sum(r['logical_expert_bytes']for r in rows[1:])
        external=sum(r['logical_expert_bytes']for r in rows[1:])
        variants.append(dict(deadline=deadline,prefetch_slots=prefetch,requests=rows,
            external_logical_expert_bytes=external,external_byte_reduction_fraction=1-external/baseline))
    return dict(schema='ps5-qwen-causal-predictive-paths-screen-v1',inputs=inputs,
        cache_variants=variants,speculation=speculative_screen(records,results),
        conditional_width_two_traffic=conditional_width_two_traffic(records,results),
        original_native_baseline_counters_exact=True,causal_decisions_before_observation=True,
        fixed_cache_slots=53,maximum_prefetch_slots=2,all_actual_selected_experts_retained=True,
        future_routes_used_by_selector=False,trace_only_no_model_arithmetic=True,
        actual_backing_leases_and_prefetch_lead_time_qualified=False,
        native_speed_qualified=False,production_adopted=False,PS5_operations=0,CI_runs=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    inputs=record(args.manifest)
    report=run(json.loads(args.manifest.read_text()))
    if record(args.manifest)!=inputs or any(record(r['path'])!=r for r in report['inputs']):
        raise ValueError('A frozen metadata input changed')
    report['manifest']=inputs
    report['implementation']=record(Path(__file__))
    (args.out/'complete.private.json').write_text(json.dumps(report,indent=2)+'\n')
    summary=dict(cache_variants=[{k:v for k,v in x.items()if k!='requests'}for x in report['cache_variants']],
        speculation=[{k:v for k,v in x.items()if k!='decisions'}for x in report['speculation']],
        conditional_width_two_traffic={k:v for k,v in report['conditional_width_two_traffic'].items()if k!='requests'},
        native_speed_qualified=False,PS5_operations=0,CI_runs=0)
    print(json.dumps(summary))


if __name__=='__main__':main()
