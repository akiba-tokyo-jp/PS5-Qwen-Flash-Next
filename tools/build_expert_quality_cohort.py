"""Prepare a finite per-prompt quality cohort without console operations."""
import argparse,copy,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from expert_q4 import record,require,write_json
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
from build_speculative_batch_probe import once
PROMPTS=[
 '説明は書かず、英単語 cat を日本語に訳してください。訳語だけを答えてください。',
 'Compute 19 + 23. Reply with digits only.',
 'Extract the city and number from "Tokyo has 3 keys". Reply with only a JSON object with keys city and count.',
]
QUALITY=dict(schema='ps5-qwen-Expert-quality-cohort-v1',enabled=True,prompts=PROMPTS,
 cases=['Japanese_instruction','arithmetic','extraction_JSON'],requests_per_prompt=3,maximum_requests=9,
 maximum_output_tokens=32,context_tokens=256,same_format_per_prompt_full_F32_and_routes=True,
 cross_format_logit_equality_required=False,retain_every_Q4_correct_answer=True,automatic_retries=0)

def derive(text,oldscope):
 scope=dict(oldscope,maximum_requests=9,warmup_requests=3,timed_requests=6)
 old='Json::parse('+json.dumps(json.dumps(oldscope,separators=(',',':')))+')'
 new='Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+')'
 text=once(text,old,new)
 text=once(text,'using Json = nlohmann::json;','using Json = nlohmann::json;\n#include "expert-quality-cohort.private.h"')
 marker='        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);'
 text=once(text,marker,'        if(policy.at("native_Expert_quality_cohort")!=Json::parse('+json.dumps(json.dumps(QUALITY,separators=(',',':')))+'))\n'
  '            throw std::runtime_error("Exact finite quality cohort required");\n'+marker)
 text=once(text,'        const unsigned request_count=3;','        const unsigned request_count=9;')
 text=once(text,'        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {',
  '        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {\n            if(ordinal%3==0){reference_rows=0;reference_ids.clear();reference_bytes.clear();}')
 text=once(text,'const unsigned group=ordinal?((ordinal-1)/2):0;','const unsigned group=ordinal/3;')
 text=once(text,'const char *arm=ordinal==0?','const char *arm=ordinal%3==0?')
 text=once(text,'if(ordinal==0){std::copy','if(ordinal%3==0){std::copy')
 text=once(text,'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32',
  'qwen_app::render_bounded_user_prompt(chat_template,expert_quality_prompts[group]),256,32')
 text=once(text,'(ordinal&&rows!=reference_rows)','(ordinal%3&&rows!=reference_rows)')
 text=once(text,'if(!ordinal){reference_ids=','if(ordinal%3==0){reference_ids=')
 text=once(text,'if(ordinal){const auto&a=routes[0],&b=routes[ordinal];',
  'if(ordinal%3){const auto&a=routes[ordinal-ordinal%3],&b=routes[ordinal];')
 text=once(text,'{"full_F32_logit_rows_compared",ordinal?rows:0}','{"full_F32_logit_rows_compared",ordinal%3?rows:0}')
 text=once(text,'try{qwen_app::require_demo_sequence(result.output_bytes);}catch(const std::exception&){counting_quality=false;}',
  'counting_quality=expert_quality_answer(group,result.output_bytes);')
 text=once(text,'row["counting_quality_passed"]=counting_quality;',
  'row["quality_passed"]=counting_quality;row["quality_case"]=group;row["reference_request"]=ordinal-ordinal%3;')
 text=once(text,'{"requests",completed},{"model_loads",1}',
  '{"quality_cohort",true},{"quality_prompts",expert_quality_prompts},{"requests",completed},{"model_loads",1}')
 return text,scope

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--kind',choices=('Q4','Q2'),required=True);a=p.parse_args();prior=json.loads(a.parent.read_text())
 key='expert_'+a.kind.lower()+'_model';parent=Path(prior[key]['actual_entry']['path'])
 frozen=active_link_inputs(prior)+[record(a.parent),record(__file__),record(parent)]
 for row in frozen:require(record(row['path'])==row,'Qualified quality-cohort parent changed')
 text,scope=derive(parent.read_text(),prior[key]['scope'])
 a.out.mkdir();(a.out/'tmp').mkdir();header=a.out/'expert-quality-cohort.private.h'
 h='#pragma once\ninline const std::array<const char*,3>expert_quality_prompts={'+','.join(json.dumps(x,ensure_ascii=False)for x in PROMPTS)+'};\n'
 h+='''inline bool expert_quality_answer(unsigned index,const std::vector<unsigned char>&bytes){
    std::string value(bytes.begin(),bytes.end());const auto first=value.find_first_not_of(" \\t\\r\\n");
    if(first==std::string::npos)return false;value=value.substr(first,value.find_last_not_of(" \\t\\r\\n")-first+1);
    if(index==0)return value=="猫"||value=="ねこ"||value=="ネコ";
    if(index==1)return value=="42";
    if(index!=2)return false;
    try{const auto j=Json::parse(value);return j.is_object()&&j.size()==2&&j.at("city")=="Tokyo"&&j.at("count").is_number_integer()&&j.at("count")==3;}
    catch(const std::exception&){return false;}
}
'''
 header.write_text(h,encoding='utf-8',newline='\n');source=a.out/'Expert-quality-entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
 cmd=prior['compile_commands'][0].copy();obj=a.out/'entry.o';oldobj=cmd[cmd.index('-o')+1]
 cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
 if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'entry.private.d')
 cmd[1:1]=['-I',str(a.out)];cmd+=['-I',str(parent.parent)]
 require(prior['link_command'].count(oldobj)==1,'One exact entry-object replacement required')
 link=[str(obj)if x==oldobj else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen +=[record(source),record(header)]
 for i,command in enumerate((cmd,link)):
  x=subprocess.run(command,cwd=R,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(x.stdout+x.stderr);require(x.returncode==0,x.stderr.decode(errors='replace')[-5000:])
  print(json.dumps(dict(quality_cohort_build_step=i+1,total=2,kind=a.kind)),flush=True)
 for row in frozen:require(record(row['path'])==row,'A frozen quality-cohort input changed')
 result=copy.deepcopy(prior);result.update(artifact=record(image),compile_commands=[cmd],link_command=link,
  source_parent=record(a.parent),inputs_before=prior['inputs_before']+frozen+[record(obj)],
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 result[key].update(actual_entry=record(source),scope=scope)
 result['expert_quality_cohort']=dict(scope=QUALITY,precision=a.kind,actual_entry=record(source),header=record(header),model_execution_pending=True)
 write_json(a.out/'receipt.private.json',result)
 result['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
 result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Quality-cohort native audit failed')
 write_json(a.out/'receipt.private.json',result);print(json.dumps(dict(quality_cohort_native_build_complete=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
