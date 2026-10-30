#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run four fixed quality tasks twice each with the current native providers."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_expert_quality_cohort import PROMPTS
from build_cache_capacity_1125 import literal
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--only-task',type=int,choices=range(4))
 a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);requests=2 if a.only_task is not None else 8
 cmd=prior['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
 scopes=[]
 for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
  new=dict(original,maximum_requests=requests,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
  text=once(text,literal(original),literal(new));scopes.append(new)
 scope,model,probation=scopes
 text=once(text,'const bool prefix_comparison=true;','const bool prefix_comparison=false;')
 text=once(text,'const unsigned request_count=3;','const unsigned request_count='+str(requests)+';')
 header=a.out/'memory-quality.private.h'
 header.write_text('#pragma once\ninline const std::array<const char*,3>memory_quality_prompts={'+','.join(json.dumps(x,ensure_ascii=False)for x in PROMPTS)+'};\n'+r'''
inline bool memory_quality_answer(unsigned task,const std::vector<unsigned char>&bytes){
 std::string v(bytes.begin(),bytes.end());auto first=v.find_first_not_of(" \t\r\n");if(first==std::string::npos)return false;
 v=v.substr(first,v.find_last_not_of(" \t\r\n")-first+1);
 if(task==1)return v=="猫"||v=="ねこ"||v=="ネコ";
 if(task==2)return v=="42";
 if(task!=3)return false;
 try{auto j=Json::parse(v);return j.is_object()&&j.size()==2&&j.at("city")=="Tokyo"&&j.at("count").is_number_integer()&&j.at("count")==3;}catch(...){return false;}
}
'''.replace('\\"','"'),encoding='utf-8',newline='\n')
 text=once(text,'using Json = nlohmann::json;','using Json = nlohmann::json;\n#include "memory-quality.private.h"')
 start=text.index('        const auto run_all_Q2_request=');end=text.index('        run_all_Q2_request(0,',start);part=text[start:end]
 part=once(part,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;','            const bool second=false;const bool repeat=ordinal%2;const unsigned task='+('ordinal/2'if a.only_task is None else str(a.only_task))+';if(!repeat)reference_rows=0;')
 part=once(part,'            const bool reuse=ordinal>0;','            const bool reuse=false;')
 part=part.replace('if(!ordinal)','if(!repeat)').replace('if(ordinal==1','if(repeat').replace('ordinal==1&&','repeat&&').replace('else if(ordinal==1)','else if(repeat)')
 part=once(part,'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32','qwen_app::render_bounded_user_prompt(chat_template,task?memory_quality_prompts[task-1]:qwen_app::demo_prompt),256,32')
 part=once(part,'try{qwen_app::require_demo_sequence(result.output_bytes);}catch(const std::exception&){counting_quality=false;}',
  'if(task)counting_quality=memory_quality_answer(task,result.output_bytes);else try{qwen_app::require_demo_sequence(result.output_bytes);}catch(const std::exception&){counting_quality=false;}')
 part=once(part,'const auto&a=routes[0],&b=routes[ordinal];','const auto&a=routes[ordinal-1],&b=routes[ordinal];')
 part=once(part,'            if(repeat)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);','')
 part=once(part,'            row["counting_quality_passed"]=counting_quality;','            row["quality_task"]=task;row["independent_repeat"]=repeat;row["counting_quality_passed"]=counting_quality;')
 part=once(part,'{"full_F32_logit_rows_compared",ordinal?rows:0}','{"full_F32_logit_rows_compared",repeat?rows:0}')
 part=once(part,'            if(!counting_quality)throw std::runtime_error("Completed all-Expert Q2 counting response failed normal-app quality");','            // Record raw-format quality failures; numerical and completion guards remain mandatory.')
 # Retain token publishing as a no-op, but remove only native frame capture.
 marker='            if(ordinal){\n                if(!result.metrics.decode_tokens_per_second'
 at=part.index(marker);tail=part.index('            return row;',at);part=part[:at]+part[tail:]
 text=text[:start]+part+text[end:]
 start=text.index('        run_all_Q2_request(0,');end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',start)
 text=text[:start]+'''        for(unsigned ordinal=0;ordinal<request_count;++ordinal)run_all_Q2_request(ordinal,[]{return true;},[](const Json&){});
        const Json demo={{"headless_fixed_quality",true}};
'''+text[end:]
 text=once(text,'{"HTTP_requests",2},{"VideoOut_starts",1},{"passive_monitor_and_API_completed",true},{"optimized_delivery_and_final_prefix_handoff_completed",true}',
  '{"HTTP_requests",0},{"VideoOut_starts",0},{"headless_fixed_quality_completed",true},{"optimized_delivery_and_final_prefix_handoff_completed",false}')
 result,commands,sources=link(a.parent,a.out,{'entry':(cmd,text)},[Path(__file__),header])
 for key in ('normal_performance','output_Q8_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands);result[key].update(scope=scope,model_scope=model)
 result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=commands['entry']
 result['routing_sharing'].update(scope=scope,model_scope=model);result['routing_winners_normal'].update(scope=scope,model_scope=model,actual_entry=sources['entry'])
 result['memory_quality_cohort']=dict(scope=scope,model_scope=model,actual_sources=sources,commands=commands,independent_pairs=requests//2,requests=requests,only_task=a.only_task,HTTP_requests=0,VideoOut_starts=0,raw_format_failures_recorded_without_aborting=True,original_physical_and_completion_guards_preserved=True,production_adopted=False)
 seal(result,a.workspace,a.cache,a.out);print('Four fixed native quality pairs built with exact same-policy F32 and ordered-route comparisons.')
if __name__=='__main__':main()
