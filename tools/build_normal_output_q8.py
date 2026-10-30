#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the measured output-only Q8/997-slot winner into the normal app."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_output_q8_screen import cache_source,force_float_inputs
from relink_output_q8_inspection import inspect_source
from build_expert_q2_probation_monitor import SCOPE as OLD_PROBATION
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
literal=lambda v:json.dumps(json.dumps(v,separators=(',',':')))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','publication','analysis','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());publication=json.loads(a.publication.read_text());analysis=json.loads(a.analysis.read_text())
 require(analysis['completed']and analysis['eligible_for_normal_integration'],'Closed Q8/997-slot physical winner required')
 require(publication['completed']and publication['native_whole_SHA256_EOF_identities_passed'],'Whole immutable Q8 publication required')
 a.out.mkdir(parents=True,exist_ok=False)
 parent=a.cache/'Expert-all-Q2-receipt-8652.json';raw=parent.read_text();header=a.out/'output_Q8_parent.private.h'
 require(record(parent)['sha256']=='efd101c3661e6eb81f17306c43fc41b361f94aa58495f2025401659228163191','Exact original parent required')
 header.write_text('#pragma once\ninline constexpr const char*output_Q8_parent_raw='+json.dumps(raw)+';\n',newline='\n')
 budget=a.out/'device_buffer_budget.h';budget.write_text((ROOT/'native/app/device_buffer_budget.h').read_text()
  .replace('model_postload_device_budget = 1792ull << 20','model_postload_device_budget = (1792ull << 20) + 199680000ull')
  .replace('model_internal_workspace_budget = 256ull << 20','model_internal_workspace_budget = 248ull << 20'),newline='\n')
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-normal-performance-output-Q8-v1',
  active_cache_slots=997,cache_budget_bytes=1533419520,output_weight_type='Q8_0',original_weight_precision_and_driver_preserved=False,
  original_except_output_weight_precision_and_driver_preserved=True,output_only_Q8_exception=True,integer_activation_quantization_disabled=True,
  saved_resident_payload_bytes=595968000,transferred_postload_quota_bytes=199680000)
 model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-normal-output-Q8-model-v1',expected_active_Q2_slots=997,
  cache_budget_bytes=1533419520,non_Expert_precision_preserved=False,non_Expert_except_output_precision_preserved=True,output_only_Q8_exception=True)
 probation=dict(OLD_PROBATION,schema='ps5-qwen-output-Q8-probation-v1',active_cache_slots=997,cache_budget_bytes=1533419520,
  original_GPU_math_unchanged=False,Expert_GPU_math_unchanged=True,output_only_Q8_exception=True)
 cmd=prior['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
 text='#include "resident_output_q8_source.h"\n#include "resident_output_q8_profile.h"\n#include "output_Q8_parent.private.h"\n'+text
 for before,after in ((prior['all_Q2_optimized_monitor']['scope'],scope),(prior['expert_q2_model']['scope'],model_scope),(OLD_PROBATION,probation)):
  text=once(text,literal(before),literal(after))
 text=once(text,'std::optional<qwen_app::ExpertAllQ2Receipt>','std::optional<qwen_app::ResidentOutputQ8Receipt>')
 text=once(text,'Expert_Q2_manifest.emplace(receipt);','Expert_Q2_manifest.emplace(receipt,output_Q8_parent_raw);')
 text=once(text,'qwen_app::expert_all_q2_source_integrity(policy.at("native_first_generation_validation"),receipt,Expert_Q2_root,expected_mapped_files)',
  'qwen_app::resident_output_Q8_source_integrity(policy.at("native_first_generation_validation"),receipt,Json::parse(output_Q8_parent_raw),Expert_Q2_root,expected_mapped_files)')
 text=once(text,'qwen_app::validate_expert_all_q2_footprint(footprint,expected_mapped_files);','qwen_app::validate_resident_output_Q8_footprint(footprint,expected_mapped_files);')
 oldseal=json.loads((a.cache/'build/Expert-all-Q2-seal-8650/source-integrity.private.json').read_text())
 text=once(text,'if(Expert_Q2_receipt)return qwen_app::expert_q2_logical_path(*Expert_Q2_receipt,Expert_Q2_root,name);',
  'if(Expert_Q2_receipt)return qwen_app::expert_q2_logical_path(*Expert_Q2_receipt,\n        name==Expert_Q2_receipt->at("files").back().at("path")?Expert_Q2_root:'+json.dumps(oldseal['source_directory'])+',name);')
 text=once(text,'        const auto buffer_type=ggml_backend_dev_buffer_type(device);','        memory_budget.expert_cache=qwen_app::resident_output_Q8_cache_budget;\n        const auto buffer_type=ggml_backend_dev_buffer_type(device);')
 text=once(text,'reset.slots!=867','reset.slots!=997')
 text=text.replace('{"active_cache_slots",867}','{"active_cache_slots",997}')
 text=once(text,'{"non_Expert_precision_preserved",true}','{"non_Expert_precision_preserved",false},{"non_Expert_except_output_precision_preserved",true},{"output_weight_type","Q8_0"}')
 text=text.replace('GATE UP Q2_K / DOWN Q2_0 MSE / OTHER BF16 F32 / TOP6 CACHE','EXPERT Q2_K Q2_0 / OUTPUT Q8 / OTHER BF16 F32 / TOP6 CACHE')
 text=force_float_inputs(inspect_source(text))
 cache_cmd=prior['routing_sharing']['commands'][1];engine_cmd=prior['all_Q2_optimized_monitor']['commands'][2];owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1]
 engine=Path(engine_cmd[engine_cmd.index('-c')+1]).read_text();engine='#include "resident_output_q8_profile.h"\n'+once(engine,
  '(prefill_tokens > 1 && expert_cache_bytes != selected_padded_cache_geometry().cache_bytes())',
  '(prefill_tokens > 1 && expert_cache_bytes != resident_output_Q8_cache_budget)')
 variants={'entry':(cmd,text),'cache':(cache_cmd,cache_source(Path(cache_cmd[cache_cmd.index('-c')+1]).read_text())),
  'engine':(engine_cmd,engine),'owner':(owner_cmd,Path(owner_cmd[owner_cmd.index('-c')+1]).read_text())}
 result,commands,sources=link(a.parent,a.out,variants,[Path(__file__),a.publication,a.analysis,header,budget,parent,
  ROOT/'native/app/resident_output_q8_receipt.h',ROOT/'native/app/resident_output_q8_source.h',ROOT/'native/app/resident_output_q8_cache_reset.h',ROOT/'native/app/resident_output_q8_profile.h'])
 result['expert_q2_model']['scope']=model_scope
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_engine=sources['engine'],commands=[commands[k]for k in ('entry','owner','engine')])
 result['routing_sharing'].update(scope=scope,model_scope=model_scope);result['routing_winners_normal'].update(scope=scope,model_scope=model_scope,actual_entry=sources['entry'])
 result['normal_performance'].update(scope=scope,model_scope=model_scope);result['normal_performance']['actual_sources'].update(sources);result['normal_performance']['commands'].update(commands)
 result['output_Q8_normal']=dict(scope=scope,model_scope=model_scope,probation_scope=probation,actual_sources=sources,commands=commands,
  publication=record(a.publication),source_integrity=publication['source_integrity'],candidate_receipt=publication['candidate'],
  comparison=record(a.analysis),normal_validation_pending=True,PS5_operations=0,production_adopted=False)
 seal(result,a.workspace,a.cache,a.out);print('Measured output-only Q8/997-slot normal composition built; final actual API qualification remains.')

if __name__=='__main__':main()
