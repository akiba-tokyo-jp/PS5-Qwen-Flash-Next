#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze closed native Q2 latency histograms and exact planner fill traces."""
import argparse, collections, json, math, os, subprocess
from pathlib import Path
from expert_q4 import record, require, write_json
from analyze_expert_q2_measurements import decode_phase

ROOT = Path(__file__).resolve().parents[1]

def quantile_interval(histogram, probability, bin_ns=128000):
    rank = math.ceil(sum(histogram) * probability)
    require(rank > 0, 'A nonempty latency sample is required')
    cumulative = 0
    for index, count in enumerate(histogram):
        cumulative += count
        if cumulative >= rank:
            return dict(lower_ms=index*bin_ns/1e6,
                        upper_ms=(index+1)*bin_ns/1e6 if index+1<len(histogram) else None,
                        rank=rank, samples=sum(histogram))
    raise ValueError('Histogram does not contain the requested rank')

def concentration(trace, fills, selected):
    require(len(trace['records']) == len(fills), 'Every native route row must be replayed')
    misses=collections.Counter(); demands=collections.Counter(); repeats=collections.Counter()
    seen=set(); layer_demands=collections.Counter(); phase=collections.Counter()
    phase_misses=collections.defaultdict(collections.Counter);phase_demands=collections.defaultdict(collections.Counter)
    merged=collections.Counter(); graph=-1; decode_calls_saved=0
    for route, row in zip(trace['records'], fills):
        require((route['layer'],route['tokens']) == (row['layer'],row['tokens']), 'Replay row changed')
        layer=row['layer']
        if layer==0: graph+=1
        # Counting prompt has exactly 30 tokens in eight prefill graphs.
        stage='prefill' if graph<8 else ('decode' if graph<29 else 'final_EOS')
        ids=set(route['ids']); demanded={(layer,expert) for expert in ids}
        demands.update(demanded);layer_demands[layer]+=len(ids)
        keys=[(layer,item[0]) for item in row['fills']]
        misses.update(keys);phase[stage]+=len(keys)
        phase_misses[stage].update(keys);phase_demands[stage].update(demanded)
        for key in keys:
            if key in seen:repeats[key]+=1
        seen.update(demanded)
        # Only adjacent physical bundle indices demanded by this same graph/layer.
        indices=sorted(selected[key] for key in keys if key in selected)
        cursor=0
        while cursor<len(indices):
            count=1
            while cursor+count<len(indices) and count<5 and indices[cursor+count]==indices[cursor]+count:
                count+=1
            merged[count]+=1
            if stage=='decode':decode_calls_saved+=count-1
            cursor+=count
    total=sum(misses.values()); unique=sum(demands.values())
    require(total==trace['cache_misses'] and unique==trace['unique_selected_experts'], 'Native counters must match exact replay')
    layers=[]
    for layer in range(48):
        count=sum(v for (l,e),v in misses.items() if l==layer)
        layers.append(dict(layer=layer,misses=count,demands=layer_demands[layer],miss_rate=count/layer_demands[layer],share_of_misses=count/total))
    top=[dict(layer=k[0],expert=k[1],misses=v,demands=demands[k],repeat_misses=repeats[k])for k,v in misses.most_common(30)]
    ordered=sorted(misses.values(),reverse=True)
    return dict(misses=total,unique_demands=unique,miss_rate=total/unique,phases=dict(phase),
        distinct_demanded_keys=len(demands),distinct_missed_keys=len(misses),
        compulsory_first_seen_misses=total-sum(repeats.values()),repeat_misses=sum(repeats.values()),
        layers=layers,top_Experts=top,top_10_Expert_miss_share=sum(ordered[:10])/total,
        top_100_Expert_miss_share=sum(ordered[:100])/total,
        top_1000_Expert_miss_share=sum(ordered[:1000])/total,
        phase_detail={stage:dict(
            layers=[dict(layer=layer,misses=sum(v for (l,e),v in phase_misses[stage].items()if l==layer),
                demands=sum(v for (l,e),v in phase_demands[stage].items()if l==layer))for layer in range(48)],
            top_Experts=[dict(layer=key[0],expert=key[1],misses=count,demands=phase_demands[stage][key])for key,count in phase_misses[stage].most_common(20)])for stage in phase},
        current_bundle_reads=sum(merged.values())+sum((n-1)*v for n,v in merged.items()),
        adjacent_bundle_group_sizes=dict(merged),merged_bundle_reads=sum(merged.values()),
        bundle_calls_saved=sum((n-1)*v for n,v in merged.items()),
        decode_bundle_calls_saved=decode_calls_saved,
        merge_requires_no_extra_read_bytes=True,maximum_combined_read_bytes=5*1540096)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','workspace','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    parent=json.loads((a.cache/'build/Expert-all-Q2-IO-8872/receipt.private.json').read_text())
    cache=parent['expert_q2_model']['actual_cache'];require(record(cache['path'])==cache,'Closed actual planner source changed')
    source=Path(cache['path']).read_text();start=source.index('struct moe_cache_slru {');end=source.index('// gate, up, down or gate_up, down',start)
    plan=source[start:end]
    for name,policy in [('control','qwen_app::ExpertPolicy'),('candidate','qwen_app::Q2ScreenPolicy'),('implementation','qwen_app::QualifiedProbationPolicy')]:
        (a.out/f'q2-{name}-plan.h').write_text(plan.replace('qwen_app::ExpertPolicy',policy),newline='\n')
    test=(ROOT/'tests/expert_q2_policy_screen.cpp').read_text().split('int main(int argc,char**argv)')[0]
    test+='''int main(int argc,char**argv){try{if(argc!=3)throw std::runtime_error("Two paths required");std::ifstream in(argv[1]);Json traces;in>>traces;Json out=Json::array();
    for(unsigned i=0;i<traces.size();++i){qwen_app::q2_screen_mode=i?qwen_app::Q2PolicyMode::probation:qwen_app::Q2PolicyMode::control;auto r=replay<candidate::moe_cache_slru>(traces[i],true);
    if(r["hits"]!=traces[i]["cache_hits"]||r["misses"]!=traces[i]["cache_misses"]||r["unique"]!=traces[i]["unique_selected_experts"])throw std::runtime_error("Native counters differ");out.push_back(r);}
    std::ofstream f(argv[2]);f<<out.dump()<<'\\n';}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
'''
    cpp=a.out/'replay.private.cpp';cpp.write_text(test,newline='\n')
    frozen=[record(cache['path']),record(ROOT/'native/app/expert_policy.h'),record(ROOT/'native/app/expert_q2_policy_screen.h'),record(ROOT/'tests/expert_q2_policy_screen.cpp')]
    traces=[]
    for case,ordinal in [(8900,1),(9180,2)]:
        root=a.cache/f'hardware-first-generation-{case}'
        terminal=json.loads((root/'native-model-terminal.private.json').read_text());close=json.loads((root/'restored-complete.private.json').read_text())
        require(terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and close['completed'] and not close['unknown_completion'],'Closed native evidence required')
        path=root/f'native-arm{ordinal}.routes.private.json';trace=json.loads(path.read_text())
        require(trace['complete'] and trace['cache_reset_before_request'] and trace['cache_slots']==867 and trace['sidecar_written_after_model_and_source_retirement'],'Exact cold native routes required')
        traces.append(trace);frozen.extend(record(x)for x in (path,root/'native-model-terminal.private.json',root/'restored-complete.private.json'))
    inputs=a.out/'inputs.private.json';write_json(inputs,traces)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'replay.exe';raw=a.out/'fills.private.json'
    upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(a.out),'-I',str(upstream/'vendor'),str(cpp),'-o',str(exe)],[str(exe),str(inputs),str(raw)]]
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
    replay=json.loads(raw.read_text());selection=ROOT/'.local/q2-bundle-selection-9070/selection.private.json';frozen.append(record(selection))
    selected={(r['layer'],r['expert']):i for i,r in enumerate(json.loads(selection.read_text())['Experts'])}
    policies={name:concentration(t,r['fill_records'],selected)for name,t,r in zip(('aged_lfu','two_touch_probation'),traces,replay)}
    latency={}
    for name,case,ordinals in [('aged_lfu',8900,[1,4]),('probation_no_bundle',9180,[1,4]),('probation_with_bundle',9180,[2,3])]:
        result=decode_phase(a.cache/f'hardware-first-generation-{case}',ordinals)
        histogram=[sum(r['individual_read_latency_histogram'][i]for r in result['requests'])for i in range(65)]
        latency[name]=dict(result,quantiles={f'P{int(q*100)}':quantile_interval(histogram,q)for q in (.5,.95,.99)},histogram=histogram)
    require(all(record(r['path'])==r for r in frozen),'Immutable evidence changed')
    report=dict(schema='ps5-qwen-Q2-IO-distribution-v1',completed=True,policies=policies,latency=latency,inputs=frozen,
        latency_unit='individual pread syscall wall time; overlapping calls are not SSD hardware service times',
        percentile_resolution_ns=128000,PS5_operations=0,CI_runs=0,production_changed=False)
    write_json(a.out/'receipt.private.json',report)
    print(json.dumps(dict(completed=True,policies={k:{x:v[x]for x in ('misses','miss_rate','bundle_calls_saved','decode_bundle_calls_saved','top_100_Expert_miss_share')}for k,v in policies.items()},latency={k:v['quantiles']for k,v in latency.items()}),indent=2))
if __name__=='__main__':main()
