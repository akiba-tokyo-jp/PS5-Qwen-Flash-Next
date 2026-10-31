#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price a 3072-slot cache from the completed resident-Q8 payload saving."""
import argparse
import copy
import json
from pathlib import Path
from build_cache_capacity_1125 import recipes, literal
from build_speculative_batch_probe import once
from expert_q4 import require, record, write_json
from scoped_native_variant import link, seal

ROOT = Path(__file__).resolve().parents[1]
SLOTS = 3072
EXTRA = (SLOTS - 1381) * 1536000
TRANSFER = 601284608 + EXTRA + (8 << 20)
CACHE = 2123243520 + EXTRA
SINGLE = 1600 << 20


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('parent', 'workspace', 'cache', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    prior = json.loads(a.parent.read_text())
    require(prior['resident_all_Q8']['additional_weight_saved_bytes'] == 3163852800,
            'Exact completed resident-Q8 saving required')
    require(EXTRA + (8 << 20) + (16 << 20) < 3163852800,
            'Preserve payload saving and alignment margin')
    require((SLOTS + 1) * 537600 < SINGLE < (2 << 30),
            'Each bank must fit the observed native 2 GiB limit')
    a.out.mkdir(parents=True, exist_ok=False)
    owner_cmd = prior['all_Q2_optimized_monitor']['commands'][1]
    owner_path = Path(owner_cmd[owner_cmd.index('-c') + 1])
    shared = a.cache / 'build/Shared-cache1381-checkpoint-10700'
    budget = (owner_path.parent / 'device_buffer_budget.h').read_text()
    budget = once(budget, '+ 601284608ull', '+ ' + str(TRANSFER) + 'ull')
    budget = once(budget, 'model_postload_single_buffer = 716ull << 20',
                  'model_postload_single_buffer = 1600ull << 20')
    (a.out / 'device_buffer_budget.h').write_text(budget, newline='\n')
    profile = (shared / 'resident_output_q8_profile.h').read_text()
    profile = once(profile, 'cache_transfer=601284608', 'cache_transfer=' + str(TRANSFER))
    profile = once(profile, 'cache_budget=2123243520', 'cache_budget=' + str(CACHE))
    profile = once(profile, '+221184000ull-(16ull<<20)',
                   '+221184000ull+3163852800ull-(16ull<<20)')
    (a.out / 'resident_output_q8_profile.h').write_text(profile, newline='\n')
    reset = (shared / 'resident_output_q8_cache_reset.h').read_text()
    reset = reset.replace('997', '1381').replace('!=1381&&', '!=3072&&')
    # Both old and new metadata geometries are permitted within the new banks.
    require('selected!=3072&&selected!=1381' in reset and
            'lru.n_slots!=3072&&lru.n_slots!=1381' in reset,
            'Exact two-capacity reset required')
    reset = reset.replace('keeps 1382 planes', 'keeps 3073 planes')
    (a.out / 'resident_output_q8_cache_reset.h').write_text(reset, newline='\n')
    scope = dict(prior['all_Q2_optimized_monitor']['scope'], active_cache_slots=SLOTS,
                 cache_budget_bytes=CACHE, transferred_postload_quota_bytes=TRANSFER,
                 postload_single_buffer_bytes=SINGLE, resident_weight_retention_available=True)
    model = dict(prior['expert_q2_model']['scope'], expected_active_Q2_slots=SLOTS,
                 cache_budget_bytes=CACHE)
    probation = dict(prior['output_Q8_normal']['probation_scope'],
                     active_cache_slots=SLOTS, cache_budget_bytes=CACHE)
    resident = dict(prior['resident_all_Q8']['scope'], active_cache_slots=SLOTS,
                    cache_budget_bytes=CACHE, cache_redistribution=True)
    cold_scope=dict(prior['cold_request']['scope'],active_cache_slots=SLOTS,device_ledger_cap_increased=True)
    ec = prior['compile_commands'][0]
    entry = Path(ec[ec.index('-c') + 1]).read_text()
    for old, new in ((prior['all_Q2_optimized_monitor']['scope'], scope),
                     (prior['expert_q2_model']['scope'], model),
                     (prior['output_Q8_normal']['probation_scope'], probation),
                     (prior['resident_all_Q8']['scope'], resident)):
        entry = once(entry, literal(old), literal(new))
    entry=once(entry,literal(prior['cold_request']['scope']),literal(cold_scope))
    entry = ('extern "C" bool qwen_app_weight_retention_selected();\n'
             'extern "C" unsigned qwen_app_output_Q8_slots();\n') + entry
    entry = once(entry, 'reset.slots!=1381||reset.occupied_after||',
                 'reset.slots!=qwen_app_output_Q8_slots()||'
                 '(qwen_app_weight_retention_selected()?reset.occupied_after!=reset.occupied_before:reset.occupied_after!=0)||')
    entry = once(entry, '{"occupied_before",reset.occupied_before}',
                 '{"weights_retained",qwen_app_weight_retention_selected()},'
                 '{"occupied_before",reset.occupied_before}')
    entry = entry.replace('{"active_cache_slots",1381}', '{"active_cache_slots",3072}')
    cc = prior['routing_sharing']['commands'][1]
    cache = Path(cc[cc.index('-c') + 1]).read_text()
    cache = '#include "resident_weight_retention.h"\n' + cache
    cache = cache.replace('output_Q8_selected_slots=1381', 'output_Q8_selected_slots=3072')
    cache = cache.replace('g.n_slots < 1381', 'g.n_slots < 3072')
    cache = cache.replace('groups[0].n_slots!=997&&groups[0].n_slots!=1381',
                          'groups[0].n_slots!=1381&&groups[0].n_slots!=3072')
    cache = cache.replace('slots!=997&&slots!=1381', 'slots!=1381&&slots!=3072')
    cache = once(cache, 'namespace {unsigned output_Q8_selected_slots=3072;}',
                 'namespace {unsigned output_Q8_selected_slots=3072;bool keep_weight_cache=false;}\n'
                 'extern "C" bool qwen_app_weight_retention_selected(){return keep_weight_cache;}\n'
                 'extern "C" void qwen_app_select_weight_retention(bool keep){\n'
                 ' if(!resident_reuse_enabled||!resident_reuse_owner||resident_reuse_thread!=std::this_thread::get_id())'
                 'throw std::runtime_error("Live cache owner required for weight retention");\n'
                 ' qwen_app_complete_predictive_expert();keep_weight_cache=keep;\n}\n')
    old = 'result.occupied_before+=(g.ref[0]->type==GGML_TYPE_Q2_K?'
    cache = once(cache, old, 'result.occupied_before+=(keep_weight_cache?'
                 'qwen_app::validate_retained_weight_cache(g.slru,unsigned(g.layers.size()),output_Q8_selected_slots):'
                 'g.ref[0]->type==GGML_TYPE_Q2_K?')
    cache = once(cache, 'for(auto &g:groups)g.slru.policy.set_eviction_policy(',
                 'if(!keep_weight_cache)for(auto &g:groups)g.slru.policy.set_eviction_policy(')
    cache = once(cache, '||result.occupied_after)',
                 '||(keep_weight_cache?result.occupied_after!=result.occupied_before:result.occupied_after!=0))')
    en = prior['routing_sharing']['commands'][2]
    pc = next(c for c in recipes(prior) if c[c.index('-c') + 1].endswith('padding.private.cpp'))
    padding = once(Path(pc[pc.index('-c') + 1]).read_text(), '716ull<<20', '1600ull<<20')
    variants = dict(entry=(ec, entry), cache=(cc, cache), owner=(owner_cmd, owner_path.read_text()),
                    engine=(en, Path(en[en.index('-c') + 1]).read_text()), padding=(pc, padding))
    inputs = [Path(__file__), ROOT / 'native/app/resident_weight_retention.h',
              *[a.out / n for n in ('device_buffer_budget.h', 'resident_output_q8_profile.h',
                                    'resident_output_q8_cache_reset.h')]]
    result, jobs, sources = link(a.parent, a.out, variants, inputs)
    for key in ('normal_performance', 'output_Q8_normal'):
        result[key]['actual_sources'].update(sources)
        result[key]['commands'].update(jobs)
        result[key].update(scope=scope, model_scope=model)
    result['output_Q8_normal']['probation_scope'] = probation
    result['expert_q2_model']['scope'] = model
    result['all_Q2_optimized_monitor'].update(scope=scope, actual_entry=sources['entry'],
        actual_engine=sources['engine'], actual_owner=sources['owner'],
        commands=[jobs[k] for k in ('entry', 'owner', 'engine')])
    result['routing_sharing'].update(scope=scope, model_scope=model)
    result['routing_winners_normal'].update(scope=scope, model_scope=model, actual_entry=sources['entry'])
    for key in ('resident_all_Q8', 'resident_shared_Q8'):
        result[key].update(scope=resident if key=='resident_all_Q8' else scope,
                           model_scope=model, cache_capacity_unchanged=False)
        result[key].setdefault('actual_sources', {}).update(sources)
        result[key].setdefault('commands', {}).update(jobs)
    result['cold_request']['actual_sources'].update(sources)
    result['cold_request']['commands'].update(jobs)
    result['cold_request']['scope']=cold_scope
    result['cold_request']['device_ledger_cap_bytes'] = (1792 << 20) + TRANSFER
    result['resident_cache3072'] = dict(scope=scope, active_slots=SLOTS, control_slots=1381,
        physical_planes=SLOTS+1, cache_budget_bytes=CACHE, payload_growth_bytes=EXTRA,
        additional_rounding_allowance_bytes=8<<20, transferred_postload_quota_bytes=TRANSFER,
        postload_single_buffer_bytes=SINGLE, largest_bank_bytes=(SLOTS+1)*537600,
        saving_used_bytes=EXTRA+(8<<20), verified_additional_payload_saving_bytes=3163852800,
        physical_reserves_and_kernel_owner_completion_guards_preserved=True,
        retained_weights_default=False, request_state_retention=False,
        actual_sources=sources, commands=jobs, native_verification_pending=True)
    seal(result, a.workspace, a.cache, a.out)
    write_json(a.out/'core-safety.private.json', dict(completed=True,
        kind='resident_Q8_saving_cache3072_explicit_quota_transfer',
        original_physical_and_kernel_guards_preserved=True, CPU_heap_limit_bytes=512<<20,
        workspace_bytes=48<<20, cache_slots=SLOTS, Expert_Q2_payloads_unchanged=True,
        driver_unchanged=True, candidate=record(a.out/'receipt.private.json'), PS5_operations=0, CI_runs=0))


if __name__ == '__main__': main()
