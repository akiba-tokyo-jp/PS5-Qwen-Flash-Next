#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a three-representation numerical/cost slice; never load a model."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from build_post_top2_submission import gpu_source
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-shared-basis-fixture-v1',model_loads=0,requests=0,GPU_graphs=180,cases=5,
 representations=['original_Q2_K','flat_TQ1_0','shared_rank32_Q8_plus_TQ1_residual'],same_layer_actual_Experts=3,
 token_shapes=[1,2,1,2,30],selected_shapes=[2,2,2,2,6],duplicate_ids_tested=True,
 every_output_F64_reference=True,input_and_output_canaries=True,NMSE_limit=0.0005,
 whole_model_speed_claim=False,answer_quality_claim=False,maximum_seconds=600,automatic_retries=0,CI_runs=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','dataset','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--remote',required=True);a=p.parse_args();n=json.loads(a.parent.read_text());d=json.loads(a.dataset.read_text());require(d['completed']and record(d['artifact']['path'])==d['artifact'],'Exact compressed weight fixture required');require(a.remote.startswith(('/app0/','/data/'))and '..'not in a.remote,'New absolute data input required');a.out.mkdir(parents=True,exist_ok=False)
 names=['base_gate','base_up','flat_gate','flat_up','residual_gate','residual_up','factor_gate','factor_up','basis_gate','basis_up'];by={v['name']:v for v in d['sections']};require(set(by)==set(names),'Exact ten tensor representations required')
 assets=a.out/'shared_basis_assets.private.h';s='#pragma once\ninline constexpr const char*shared_basis_path='+json.dumps(a.remote)+';\ninline constexpr const char*shared_basis_sha='+json.dumps(d['artifact']['sha256'])+';\ninline constexpr size_t shared_basis_bytes='+str(d['artifact']['bytes'])+';\nstruct SharedBasisSection{ggml_type type;long long ne[3];size_t offset,bytes;};\ninline constexpr SharedBasisSection shared_basis_sections[]={\n'
 for key in names:
  v=by[key];ne=v['ne']+[1]*(3-len(v['ne']));s+='{GGML_TYPE_'+v['type_name']+',{'+','.join(map(str,ne))+'},'+str(v['offset'])+','+str(v['bytes'])+'},\n'
 assets.write_text(s+'};\n',newline='\n');ec=n['compile_commands'][0];entry='#include "shared_basis_fixture.h"\n'+Path(ec[ec.index('-c')+1]).read_text()
 branch='''        {if(policy.at("native_GDN_conv_normalization_fixture")!=Json::parse(SCOPE_LITERAL))throw std::runtime_error("Exact shared-basis fixture scope required");
        qwen_app::enforce_native_model_compute_limits();if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty shared-basis ledger required");
        auto result=qwen_app::shared_basis_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_app_conv_norm_trial_release();qwen_native_driver_complete();qwen_app::stop_native_model_sources();const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live)throw std::runtime_error("Shared-basis resources not fully retired");const auto&owner=policy.at("native_first_generation_validation");
        result.update({{"schema","ps5-qwen-shared-basis-fixture-result-v1"},{"completed",true},{"pid",getpid()},{"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
          {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},{"device_ledger_live_bytes",ledger.live},{"device_ledger_peak_bytes",ledger.peak},
          {"additional_shader_verified",qwen_app_additional_shaders_verified()},{"all_model_source_device_owners_positively_retired",true}});
        write_fresh_report(startup.admission_report,result);qwen_native_stage("shared_basis_fixture_complete_waiting_for_ordinary_close");for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));}
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";');gc=n['io_gpu_comparison']['GPU_command'];gpu=gpu_source(Path(gc[gc.index('-c')+1]).read_text(),40,256,256)
 quant_dirs=[Path(v[2:]if v.startswith('-I')else v)for v in gc if not v.startswith('-')or v.startswith('-I')];quant_dir=next(v for v in quant_dirs if (v/'ggml-quants.h').is_file())
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app'),'-I',str(quant_dir)],entry),gpu=(gc,gpu)),[Path(__file__),a.dataset,assets,ROOT/'native/app/shared_basis_fixture.h',ROOT/'tools/build_post_top2_submission.py'])
 r['GDN_conv_normalization_fixture']=dict(scope=SCOPE,actual_sources=sources,commands=jobs,dataset=record(a.dataset),remote_input=a.remote,additional_shaders_added=0)
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 seed=a.out/'linked-seed.private.json';write_json(seed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),scope=SCOPE,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
