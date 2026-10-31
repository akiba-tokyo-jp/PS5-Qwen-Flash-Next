#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare exact current-miss bundles and a device-owned GDN specialization."""
import argparse,json,re,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

GPU_STATE_V1=r'''
namespace {
struct QwenGDNTrial { vk_device device; std::array<vk_pipeline,2> pipelines; };
std::unique_ptr<QwenGDNTrial> qwen_gdn_trial;
bool qwen_gdn_selected=false;
std::uint64_t qwen_gdn_selections=0;
}
extern "C" void qwen_app_gdn_trial_select(bool enabled){
 if(!qwen_gdn_trial||!qwen_gdn_trial->pipelines[0]||!qwen_gdn_trial->pipelines[1])
  throw std::runtime_error("Owned GDN comparison pipelines required");
 qwen_gdn_selected=enabled;
}
extern "C" std::uint64_t qwen_app_gdn_trial_selections(){return qwen_gdn_selections;}
extern "C" void qwen_app_gdn_trial_release(){qwen_gdn_selected=false;qwen_gdn_trial.reset();}
'''
GPU_STATE=r'''
namespace {
struct QwenGDNTrial { vk_device device; std::array<vk_pipeline,2> pipelines; };
std::array<std::unique_ptr<QwenGDNTrial>,8> qwen_gdn_trials;
std::mutex qwen_gdn_registry_mutex;
bool qwen_gdn_selected=false;
std::uint64_t qwen_gdn_selections=0;
QwenGDNTrial* qwen_gdn_find(const vk_device&device){
 for(auto&row:qwen_gdn_trials)if(row&&row->device==device)return row.get();return nullptr;
}
}
static void ggml_app_phase(const char*);
void ggml_vk_destroy_pipeline(vk::Device&,vk_pipeline&);
extern "C" void qwen_app_gdn_trial_select(bool enabled){
 bool ready=false;for(auto&row:qwen_gdn_trials)if(row){if(!row->pipelines[0]||!row->pipelines[1])throw std::runtime_error("Complete device-owned GDN pipelines required");ready=true;}
 if(!ready)throw std::runtime_error("Owned GDN comparison pipelines required");qwen_gdn_selected=enabled;
}
extern "C" std::uint64_t qwen_app_gdn_trial_selections(){return qwen_gdn_selections;}
extern "C" void qwen_app_gdn_trial_release(){
 std::lock_guard<std::mutex>lock(qwen_gdn_registry_mutex);qwen_gdn_selected=false;
 // Called inside the original final epoch after context/model retirement.
 // Device all_pipelines entries are weak; destroy compiled Vulkan handles
 // before dropping our strong pipeline owners, then let those weak entries expire.
 for(auto&row:qwen_gdn_trials)if(row){for(auto&root:row->pipelines){
  unsigned count=0;for(auto pipe=root;pipe;pipe=pipe->next){
   if(++count>2||pipe->compile_pending)throw std::runtime_error("GDN compilation ownership remains pending");
   if(pipe->compiled){ggml_vk_destroy_pipeline(row->device->device,pipe);pipe->compiled=false;}
  }
 }row.reset();}ggml_app_phase("Qwen_GDN_owned_pipelines_retired");
}
'''

def registry_fix(text):
    text=once(text,GPU_STATE_V1,GPU_STATE)
    old='        if(qwen_gdn_trial)throw std::runtime_error("Only one device-owned GDN trial allowed");\n        qwen_gdn_trial=std::make_unique<QwenGDNTrial>();qwen_gdn_trial->device=device;'
    replacement='''        std::lock_guard<std::mutex>lock(qwen_gdn_registry_mutex);
        auto*qwen_gdn_trial=qwen_gdn_find(device);
        if(!qwen_gdn_trial){
        auto free=std::find_if(qwen_gdn_trials.begin(),qwen_gdn_trials.end(),[](const auto&row){return !row;});
        if(free==qwen_gdn_trials.end())throw std::runtime_error("Bounded GDN device registry exhausted");
        *free=std::make_unique<QwenGDNTrial>();qwen_gdn_trial=free->get();qwen_gdn_trial->device=device;
        ggml_app_phase("Qwen_GDN_owned_device_pipelines_created");
        }
        // Revisit the existing placeholders on every requested shader walk:
        // ggml_vk_create_pipeline below owns the original lazy compile protocol.'''
    text=once(text,old,replacement)
    return once(text,'if(qwen_gdn_selected&&si==3){if(!qwen_gdn_trial||qwen_gdn_trial->device!=ctx->device)throw std::runtime_error("GDN comparison device differs");++qwen_gdn_selections;return qwen_gdn_trial->pipelines[kda];}',
       'if(qwen_gdn_selected&&si==3){auto*trial=qwen_gdn_find(ctx->device);if(!trial)throw std::runtime_error("GDN comparison device differs");++qwen_gdn_selections;return trial->pipelines[kda];}')

def gpu_variant(text):
    text=once(text,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n'+GPU_STATE_V1)
    start=text.index('    {\n        const uint32_t gdn_sizes[]');end=text.index('\n    if (device->subgroup_arithmetic',start)
    block=text[start:end]
    require(block.endswith('    }\n'),'Exact existing GDN pipeline scope required')
    trial=once(block,'for (uint32_t si = 0; si < 4; si++)','for (uint32_t si = 3; si < 4; si++)')
    trial=once(trial,'        const uint32_t gdn_sizes[]',
       '        if(qwen_gdn_trial)throw std::runtime_error("Only one device-owned GDN trial allowed");\n        qwen_gdn_trial=std::make_unique<QwenGDNTrial>();qwen_gdn_trial->device=device;\n        const uint32_t gdn_sizes[]')
    trial=once(trial,'            // gated_delta_net.comp relies on',
       '            lanes_per_column=std::max(1u,gdn_subgroup_size/4u);\n            // gated_delta_net.comp relies on')
    trial=once(trial,'device->pipeline_gated_delta_net[si][kda]','qwen_gdn_trial->pipelines[kda]')
    trial=once(trial,'gdn_names[si][kda], gdn_len','kda?"qwen_gdn_cols4_kda":"qwen_gdn_cols4", gdn_len')
    text=text[:end]+trial+text[end:]
    return registry_fix(once(text,'            return ctx->device->pipeline_gated_delta_net[si][kda];',
       '            if(qwen_gdn_selected&&si==3){if(!qwen_gdn_trial||qwen_gdn_trial->device!=ctx->device)throw std::runtime_error("GDN comparison device differs");++qwen_gdn_selections;return qwen_gdn_trial->pipelines[kda];}\n            return ctx->device->pipeline_gated_delta_net[si][kda];'))

def pack_header(pack,original):
    pairs=sorted((int(r['layer']),int(r['Expert']),int(r['index']))for r in pack['bundles']);old=re.search(r'Q2_current_keys\[\]\s*=\s*\{(.*?)\};',original,re.S)
    require(old is not None and len(pairs)==256,'Sealed256 pack and original28 table required')
    row=pack['output'];path='/app0/'+row['path'].split('/PPSA99190/',1)[1]
    return '#pragma once\n#include <array>\n#include <cstdint>\n'+''.join('inline constexpr const char*'+k+'='+json.dumps(v)+';\n'for k,v in [('Q2_current_path',path),('Q2_current_SHA256',row['sha256'])])+\
      'inline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\n'+\
      'inline constexpr std::array<unsigned,2>Q2_current_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e,i in pairs)+'};\n'+\
      'inline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\n'+\
      'inline constexpr std::array<unsigned,2>Q2_original_keys[]={'+old[1]+'};\ninline bool Q2_current_mode=false,Q2_trial_mode=false;\n'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired'],'Positive sealed CPU pack required');a.out.mkdir(parents=True,exist_ok=False)
 ec=prior['compile_commands'][0];oc=prior['all_Q2_optimized_monitor']['commands'][1]
 entry=Path(ec[ec.index('-c')+1]).read_text();owner=Path(oc[oc.index('-c')+1]).read_text()
 folders=[Path(oc[oc.index('-c')+1]).parent]+[Path(oc[i+1])for i,x in enumerate(oc[:-1])if x=='-I'];old=next(d/'current_bundle.private.h'for d in folders if(d/'current_bundle.private.h').is_file())
 header=a.out/'io-current-bundle.private.h';header.write_text(pack_header(pack,old.read_text()),newline='\n')
 owner=once(owner,'#include "current_bundle.private.h"','#include "io-current-bundle.private.h"')
 owner=once(owner,'current!=std::end(Q2_current_keys)&&*current==key','current!=std::end(Q2_current_keys)&&*current==key&&(Q2_trial_mode||std::binary_search(std::begin(Q2_original_keys),std::end(Q2_original_keys),key))')
 owner+='\nextern "C" void qwen_app_io_trial_select(bool enabled){required().require_completed_window();ops.require_metadata_idle();if(!Q2_current_verified||Q2_current_fd<0)throw std::runtime_error("Sealed trial pack required");Q2_trial_mode=enabled;}\n'
 manifest_path=Path(prior['bounded_model_source_manifest']['path']);manifest=json.loads(manifest_path.read_text());item=next(x for x in manifest['objects']if x['source'].endswith('ggml-vulkan.cpp'))
 require(item['object']==prior['lossless_shader_storage']['vulkan_object'],'Actual selected Vulkan object required')
 gc=shlex.split(item['command'],posix=False)if isinstance(item['command'],str)else item['command'].copy();gc=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in gc];gp=Path(gc[gc.index('-c')+1])
 # Sixteen requests are eight separately cleared cold/retained pairs. The
 # initial pair warms pipelines; A/B/B/A orders share the same immutable pack.
 scopes=[]
 for key in('all_Q2_optimized_monitor','expert_q2_model'):
  before=prior[key]['scope'];after=dict(before,maximum_requests=16,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True);entry=once(entry,literal(before),literal(after));scopes.append(after)
 before=prior['output_Q8_normal']['probation_scope'];probation=dict(before,maximum_requests=16);entry=once(entry,literal(before),literal(probation))
 entry=once(entry,'const unsigned phase=ordinal/4,task=ordinal%4;const unsigned arm=phase==1?2:phase==3?0:1;const unsigned hash_arm=arm==2?1:0;const bool compare=phase>=2;const bool keep=task>0;',
  'const unsigned phase=ordinal/2,task=0;constexpr unsigned order[]={0,0,1,1,0,2,2,0};const unsigned arm=order[phase],hash_arm=ordinal%2;const bool compare=ordinal>=2,keep=hash_arm!=0;')
 entry=once(entry,'std::array<std::array<std::vector<std::string>,4>,2>speed_hashes;',
  'std::array<std::vector<float>,2>io_reference;for(auto&v:io_reference)v.resize(resident_reference_rows*columns);std::array<std::size_t,2>io_rows{};double io_max_error=0;')
 entry=once(entry,'qwen_app_row_cache_select(arm>0,!keep);qwen_app_protection_begin(arm==2,!keep);',
  'qwen_app_row_cache_select(true,!keep);qwen_app_protection_begin(true,!keep);qwen_app_io_trial_select(arm==1);qwen_app_gdn_trial_select(arm==2);')
 entry=once(entry,'const char *arm_name=arm==0?"control":arm==1?"owned-row-cache":"row-cache-and-decode-protection";',
  'const char *arm_name=arm==0?"control-original448-keys":arm==1?"current-miss676-keys":"GDN-four-columns";io_max_error=0;')
 begin=entry.index('                try{const auto hash=qwen_app::sha256_metadata_bytes');end=entry.index('++rows;',begin)+len('++rows;')
 entry=entry[:begin]+'''                auto&ref=io_reference[hash_arm];for(std::size_t i=0;i<count;++i){if(!compare)ref[rows*columns+i]=v[i];else io_max_error=std::max(io_max_error,std::abs(double(v[i])-ref[rows*columns+i]));}++rows;
'''+entry[end:]
 entry=once(entry,'(compare&&rows!=speed_hashes[hash_arm][task].size())','(compare&&rows!=io_rows[hash_arm])')
 entry=once(entry,'            if(!compare){speed_ids[hash_arm][task]=result.token_ids;',
  '            if(compare&&arm!=2&&io_max_error!=0)throw std::runtime_error("Exact byte-placement full vocabulary differs");\n            if(!compare)io_rows[hash_arm]=rows;\n            if(!compare){speed_ids[hash_arm][task]=result.token_ids;')
 entry=once(entry,'const auto current_hits_before=qwen_app_current_bundle_hits();','const auto current_hits_before=qwen_app_current_bundle_hits();const auto gdn_before=qwen_app_gdn_trial_selections();')
 entry=once(entry,'row["maximum_absolute_logit_error"]=max_error;','row["maximum_absolute_logit_error"]=io_max_error;row["GDN_candidate_pipeline_selections"]=qwen_app_gdn_trial_selections()-gdn_before;') if 'row["maximum_absolute_logit_error"]=max_error;'in entry else entry
 entry=once(entry,'row["candidate_arm"]=arm;','row["candidate_arm"]=arm;row["GDN_candidate_pipeline_selections"]=qwen_app_gdn_trial_selections()-gdn_before;row["maximum_absolute_logit_error"]=io_max_error;')
 entry=once(entry,'{"cache_reset_before_request",i%4==0}','{"cache_reset_before_request",i%2==0}')
 entry=once(entry,'{"enabled",arm>0}','{"enabled",true}')
 entry=once(entry,'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_native_driver_complete();',
  'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_app_gdn_trial_release();qwen_native_driver_complete();')
 entry='''#include <cstdint>
extern "C" void qwen_app_io_trial_select(bool);
extern "C" void qwen_app_gdn_trial_select(bool);
extern "C" std::uint64_t qwen_app_gdn_trial_selections();
extern "C" void qwen_app_gdn_trial_release();
'''+entry
 result,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc,owner),GPU=(gc,gpu_variant(gp.read_text()))),[Path(__file__),a.pack,header,old,gp,manifest_path])
 scope,model=scopes
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
 for key in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):result[key].update(scope=scope,model_scope=model)
 result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_owner=sources['owner']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][1]=jobs['owner']
 result['routing_winners_normal']['actual_entry']=sources['entry'];result['memory_quality_cohort'].update(requests=16,scope=scope,model_scope=model,actual_sources=sources,commands=jobs)
 result['io_gpu_comparison']=dict(requests=16,pairs=8,order=[0,0,1,1,0,2,2,0],warmup_pairs=1,prompt='compiled_counting_only',current_bundle_keys=448,candidate_bundle_keys=676,shared_sealed_pack=record(a.pack),GPU_source=sources['GPU'],GPU_command=jobs['GPU'],all_original_reserves=True,production_adopted=False)
 from build_model_io import validate_overrides
 item['object']=record(a.out/'GPU.o');item['command']=jobs['GPU'];manifest['sources'][item['source']]['patched_sha256']=sources['GPU']['sha256']
 mp=a.out/'model-io.private.json';write_json(mp,manifest);result['bounded_model_source_manifest']=record(mp);result['bounded_model_source_overrides']=validate_overrides(mp,Path(result['engine_receipt']['path']));result['lossless_shader_storage']['vulkan_object']=item['object'];result['inputs_before'].append(record(mp))
 seal(result,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_io_gpu_comparison',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
