#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile the deployed composition's closed native measurements without relaunching it."""
import argparse,collections,json,math,statistics
from pathlib import Path
from analyze_current_speed import accepted_phase_bounds,fingerprint,latency,load,need,replay_geometry,save,token_analysis
from resident_all_q8 import placement
ROOT=Path(__file__).resolve().parents[1]
TRIPLET=1536000

def analyze(cache,previous_replay):
 inst=load(ROOT/'config/production-installation.json');adopt=load(ROOT/inst['qualification_report'])
 number=inst['normal_validation_case'];case=cache/f'hardware-first-generation-{number}'
 n=load(case/'native-model-terminal.private.json');closed=load(case/'restored-complete.private.json')
 need(number==45100 and inst['qualification_report']=='docs/post-top2-adoption-20261101.json'and adopt['completed']and adopt['placement']['completed'],'Current deployed post-Top2 composition required')
 need(n['completed']and closed['completed']and not closed['unknown_completion']and n['all_model_source_device_owners_positively_retired']and n['device_ledger_live_bytes']==0,'Closed positive native measurement required')
 need(n['candidate_SELF_sha256']==inst['application_SELF']['sha256']and n['model_receipt_sha256']==inst['model_receipt_SHA256'],'Current program and model must match the measured cohort')
 package=load(case/'candidate-package.private.json');native_record=package['native_link_receipt'];need(fingerprint(native_record['path'])=={k:native_record[k]for k in('bytes','sha256')},'Exact actual linked receipt required')
 native=load(native_record['path']);model_record=load(case/'case-inputs.private.json')['model_receipt'];need(model_record['sha256']==inst['model_receipt_SHA256']and fingerprint(model_record['path'])=={k:model_record[k]for k in('bytes','sha256')},'Exact measured model inventory required');model=load(model_record['path'])
 source=native['resident_weight_normal']['actual_sources']['cache'];need(fingerprint(source['path'])=={k:source[k]for k in('bytes','sha256')},'Exact selected cache source required')
 text=Path(source['path']).read_text();a=text.index('struct moe_cache_slru {');b=text.index('// gate, up, down or gate_up, down',a)
 need(text[a:b]==(previous_replay/'actual-planner.private.h').read_text(),'Reused deterministic planner must be byte-identical')
 replay=load(previous_replay/'analysis.private.json');need(replay['completed']and replay['exact_frozen_native_planner_replayed'],'Positive previous deterministic replay required')
 traces=[load(case/f'native-arm{i}.routes.private.json')for i in range(3)]
 oldcase=cache/'hardware-first-generation-30200';old=load(oldcase/'native-model-terminal.private.json')
 for i,t in enumerate(traces):
  p=load(oldcase/f'native-arm{i}.routes.private.json');need(t['complete']and t['pid']==n['pid']and t['run_id']==n['run_id']and t['cache_slots']==3712,'Complete measured routes and actual geometry required')
  need(t['records']==p['records']and all(t[k]==p[k]for k in('cache_hits','cache_misses','uploaded_bytes','process_calls','unique_selected_experts')),'Reusing old planner results requires every ordered route and counter to match')
 fills=load(previous_replay/'fills.private.json');bounds=accepted_phase_bounds(case,n,traces,fills);geometry=replay_geometry(traces,fills,bounds)
 rows=[];comparisons=[]
 for row,t,g,bound,previous,fill in zip(n['requests'],traces,geometry,bounds,old['requests'],fills):
  m=row['metrics'];d=row['completed_performance']['delta'];whole=m['total_ms']/1000;process=d['process_ns']/1e9;wait=d['source_read_ns']/1e9
  need(0<wait<process<whole and row['full_F32_finite']and d['source_chunks']==d['source_completed_windows'],'Positive nested time and complete source windows required')
  parts=dict(source_producer_wait=wait,model_process_other=process-wait,outside_model_process=whole-process)
  need(math.isclose(sum(parts.values()),whole,abs_tol=1e-12),'Nonoverlapping partition must reconcile')
  evaluated=sum(x['tokens']for x in t['records'])//48;other=d['source_bytes']-t['uploaded_bytes'];need(other==evaluated*10240,'Logical indexed row accounting must reconcile')
  profile=latency(row);initial_occupied=sum(x>=0 for x in fill['initial_residents']);evictions=g['cache_misses']-(g['occupied_slots_after_request']-initial_occupied);need(evictions==0,'Every fill must occupy a previously empty slot for a no-eviction conclusion')
  q=dict(ordinal=row['ordinal'],condition=('cold_Expert_cache','retained_weights_empty_KV','exact_prefix_replay')[row['ordinal']],metrics=m,whole_generated_tokens_per_second=m['generated_tokens']/whole,
   nonoverlapping_wall_seconds=parts,nonoverlapping_wall_percent={k:100*v/whole for k,v in parts.items()},EOS_tail_ms=m['total_ms']-m['TTFT_ms']-m['decode_ms'],
   physical_read_GB=d['source_physical_read_bytes']/1e9,physical_read_calls=d['source_physical_read_calls'],whole_physical_GB_per_generated_token=d['source_physical_read_bytes']/1e9/m['generated_tokens'],
   physical_read_alignment_and_envelope_bytes=d['source_physical_read_bytes']-d['source_bytes'],logical_Expert_bytes=t['uploaded_bytes'],logical_non_Expert_indexed_row_bytes=other,evaluated_model_tokens_including_prompt_EOS=evaluated,
   non_Expert_share_of_logical_source_percent=100*other/d['source_bytes'],read_latency=profile,cache=dict(g,evictions=evictions,remaining_slots=3712-g['occupied_slots_after_request']),process_boundaries=bound,
   diagnostic_timer_ms={k:d[k]/1e6 for k in('checkpoint_ns','stage_observer_ns','work_guard_ns','synchronize_ns','source_consumer_ns','source_handle_ns','source_headroom_ns')},
   planner_ms=row['cold_request_timing']['plan_wall_ns']/1e6,routing_rank_ms=row['routing_policy']['rank_CPU_ns']/1e6,
   streaming=row['streaming_delivery'],speculation=row['speculation'],prefix=row['prefix'],counting_correct=row['counting_quality_passed'],cross_cache_maximum_logit_error=row['maximum_absolute_logit_error'])
  if row['ordinal']:
   q['accepted_decode']=token_analysis(case,row);need(q['accepted_decode']['cache_misses']==g['phase_misses']['decode'],'Current token timing and replay phase misses must agree')
  pd=previous['completed_performance']['delta'];previous_parts=dict(source_producer_wait=pd['source_read_ns']/1e9,model_process_other=(pd['process_ns']-pd['source_read_ns'])/1e9,outside_model_process=previous['metrics']['total_ms']/1000-pd['process_ns']/1e9)
  comparisons.append(dict(ordinal=row['ordinal'],previous_case=30200,current_case=number,matched_ABBA=False,all_ordered_routes_and_physical_bytes_and_calls_identical=True,
   whole_time_saved_ms=previous['metrics']['total_ms']-m['total_ms'],nonoverlapping_time_saved_ms={k:1000*(previous_parts[k]-parts[k])for k in parts},decode_change_percent=100*(m['decode_tokens_per_second']/previous['metrics']['decode_tokens_per_second']-1)))
  need(math.isclose(sum(comparisons[-1]['nonoverlapping_time_saved_ms'].values()),comparisons[-1]['whole_time_saved_ms'],abs_tol=1e-6),'Every before/after timing difference must reconcile')
  need(d['source_physical_read_bytes']==pd['source_physical_read_bytes']and d['source_physical_read_calls']==pd['source_physical_read_calls'],'Exact unchanged source traffic required')
  rows.append(q)
 inventory=collections.defaultdict(lambda:dict(tensors=0,bytes=0));roles=collections.defaultdict(lambda:dict(tensors=0,bytes=0))
 for t in model['tensors']:
  loc=placement(t['name']);v=inventory[(loc,t['type'])];v['tensors']+=1;v['bytes']+=t['bytes']
  if loc=='device_weights':
   role=t['name'].split('.',2)[-1]if t['name'].startswith('blk.')else t['name'];v=roles[(role,t['type'])];v['tensors']+=1;v['bytes']+=t['bytes']
 startup=load(case/'native-startup-memory.private.json')['samples'];times={x['phase']:x['ns']for x in startup};start=startup[0]['ns'];ready=times['original_model_context_completed']
 startup_parts=dict(recorded_CPU_preflight=(times['CPU_preflight_complete']-start)/1e9,
  pre_settle_gap=(times['phase_local_before_startup_settle']-times['CPU_preflight_complete'])/1e9,
  observed_settle=(times['phase_local_after_startup_settle']-times['phase_local_before_startup_settle'])/1e9,
  model_loading=(times['phase_local_original_model_loaded_before_context']-times['phase_local_after_startup_settle'])/1e9,
  context_creation=(ready-times['phase_local_original_model_loaded_before_context'])/1e9)
 need(math.isclose(sum(startup_parts.values()),(ready-start)/1e9,abs_tol=1e-9),'Startup stages must reconcile')
 submission=n['post_top2_submission_counters'];retained=rows[1];whole=retained['metrics']['total_ms']/1000;wait=retained['nonoverlapping_wall_seconds']['source_producer_wait']
 gpu_record=native['io_gpu_comparison']['GPU_source'];need(fingerprint(gpu_record['path'])=={k:gpu_record[k]for k in('bytes','sha256')},'Exact actual GPU provider source required');gpu=Path(gpu_record['path']).read_text();entry_record=native['post_top2_normal']['actual_sources']['entry'];need(fingerprint(entry_record['path'])=={k:entry_record[k]for k in('bytes','sha256')},'Exact actual selected entry required');entry=Path(entry_record['path']).read_text()
 need('setenv("GGML_VK_SERIALIZE_SUBMISSIONS", "1", 1)'in entry and 'device->serialize_submissions = getenv("GGML_VK_SERIALIZE_SUBMISSIONS") != nullptr;'in gpu,'Exact selected serialized mode source required')
 need('} else if (almost_ready && !ctx->almost_ready_fence_pending) {'in gpu and gpu.count('ctx->almost_ready_fence_pending = true;')==1 and '(almost_ready && !ctx->almost_ready_fence_pending);'in gpu,'Only the nonserialized branch may set the almost-ready fence pending flag')
 need(gpu.count('submit_after(')==2 and submission[9]==0,'Two classified batch-boundary callsites and zero node-cap boundaries required')
 tail_lower_bound=max(0,submission[11]-submission[7]-submission[1])
 tail=dict(selected_serialization_enabled=True,almost_ready_pending_true_assignment_only_in_nonserialized_branch=True,
  software_batch_boundary_calls=submission[11],node_cap_boundary_events=submission[9],flop_boundary_events=submission[7],graph_calls=submission[1],
  conservative_repeated_tail_boundary_lower_bound=tail_lower_bound,conservative_tail_boundary_fraction=tail_lower_bound/submission[11],
  bound_derivation='Every boundary is FLOP preflush or node/FLOP/end/almost-ready. Node boundaries=0; at most one final nonempty compute node per graph. Subtract all FLOP events and all graph calls, allowing overlaps, for a conservative tail lower bound.',
  counter_is_submit_after_call_not_independently_measured_vkQueueSubmit=True,per_request_or_kernel_time_not_measured=True,speedup_not_proven=True,
  candidate='Gate only the almost-ready splitting predicate by !serialize_submissions; retain serialized fence waits, final graph flush, node256 and original FLOP cap.',
  required_validation='Fresh matched native comparison with complete F32/routes/tokens/bytes exactness, actual boundary/fence/queue-submit counts and positive retirement/ordinary close. This analysis performs no runtime change.')
 # Source/process timers are nested. The ceiling below removes only the visible
 # producer stall, with every other measured activity held fixed.
 scenarios=dict(retained_zero_source_wait_whole_seconds=whole-wait,retained_zero_source_wait_whole_throughput_gain_percent=100*(whole/(whole-wait)-1),retained_half_source_wait_whole_seconds=whole-wait/2,
  retained_half_source_wait_whole_throughput_gain_percent=100*(whole/(whole-wait/2)-1),hypotheses_not_causal_forecasts=True,decode_specific_wait_not_measured=True)
 evidence=[case/'native-model-terminal.private.json',case/'restored-complete.private.json',case/'native-startup-memory.private.json',ROOT/'config/production-installation.json',ROOT/inst['qualification_report'],Path(native_record['path']),Path(source['path']),Path(model_record['path']),Path(gpu_record['path']),Path(native['post_top2_normal']['actual_sources']['entry']['path']),previous_replay/'analysis.private.json',previous_replay/'actual-planner.private.h',previous_replay/'fills.private.json',*[case/f'native-arm{i}.routes.private.json'for i in range(3)],*[case/'passive-observer'/f'request-{i}.stream.private.log'for i in(1,2)]]
 return dict(schema='ps5-qwen-post-top2-current-load-analysis-v1',completed=True,source_case=number,production_case=inst['production_placement_case'],application_SELF=inst['application_SELF'],application_source_revision=inst['application_source_revision'],model_receipt_SHA256=inst['model_receipt_SHA256'],driver=inst['driver'],
  new_PS5_operations=0,production_changed=False,CI_runs=0,learned_host_inference=False,prior_planner_replay_reused_after_exact_source_and_all_routes_proof=True,rows=rows,sequential_comparison=comparisons,
  weight_inventory=[dict(placement=k[0],type=k[1],**v)for k,v in inventory.items()],resident_roles=sorted([dict(role=k[0],type=k[1],**v)for k,v in roles.items()],key=lambda x:x['bytes'],reverse=True),
  resident_weight_payload_bytes=sum(v['bytes']for(k,t),v in inventory.items()if k=='device_weights'),startup=dict(recorded_stage_span_seconds=(ready-start)/1e9,parts_seconds=startup_parts,stage_span_plus_first_request_seconds=(ready-start)/1e9+rows[0]['metrics']['total_ms']/1000,OS_loader_and_unrecorded_gaps_excluded=True,snapshots=startup),
  aggregate_native_cohort_backend=dict(control_and_candidate_counters=submission,selected_graph_calls=submission[1],selected_graph_caller_wall_seconds=submission[3]/1e9,selected_nodes=submission[5],selected_flop_boundary_events=submission[7],selected_node_boundary_events=submission[9],selected_software_batch_boundaries=submission[11],selected_maximum_nodes=submission[13],selected_sync_wall_seconds=submission[19]/1e9,selected_sync_calls=submission[21],per_request_split_not_available=True,initialization_and_cleanup_may_be_included=True,caller_wall_is_not_pure_CPU_or_pure_GPU=True),
  serialized_tail_split_investigation=tail,
  memory=dict(resident_model_excluded_from_postload_ledger=True,CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],CPU_heap_limit_bytes=inst['CPU_heap_limit_bytes'],postload_device_ledger_peak_bytes=n['device_ledger_peak_bytes'],postload_device_ledger_limit_bytes=inst['postload_device_budget_bytes'],actual_workspace_peak_bytes=n['actual_workspace_capacity_peak_bytes'],workspace_accounting_reservation_bytes=n['workspace_fixed_reservation_bytes'],Expert_cache_bytes=inst['expert_cache_bytes'],kernel_inference_minimum_pages=n['limit_margin_probe']['phases'][2]['minimum_free_pages'],OS_minimum_pages=898,kernel_page_bytes=16384,these_are_qualification_measurements_not_current_idle_free_memory=True),
  latency_scenarios=scenarios,measured_limits=['No current-production GPU timestamp/kernel-class timings: the process remainder includes CPU/backend/GPU and cannot be called pure GPU time.','Source syscall wall, consumer metadata, graph caller wall and synchronization timers overlap parent intervals and are not additive partitions.','Read latency quantiles are histogram ranges across prefill/decode/EOS, not exact percentiles or raw NAND latency.','Streaming busy-period occupancy, device queue depth, decode-only physical bytes and source wait were not captured.','Only one30-token prompt with22 generated tokens and three reuse conditions; this is not sustained/different-input qualification.','Exact-prefix counting still ends7 instead of8. No broad answer-quality or correct-answer throughput claim.'],
  evidence=[dict(artifact=p.name,**fingerprint(p))for p in evidence])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--previous-replay',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=analyze(a.cache,a.previous_replay);save(a.out,r);print(json.dumps(dict(completed=True,current_case=r['source_case'],new_PS5_operations=0,rows=[dict(condition=x['condition'],wall=x['nonoverlapping_wall_seconds'],read_GB=x['physical_read_GB'])for x in r['rows']])))
if __name__=='__main__':main()
