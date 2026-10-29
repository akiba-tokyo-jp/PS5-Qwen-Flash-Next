// SPDX-License-Identifier: MIT
#include "expert_all_q2_source_integrity.h"
#include <fstream>
#include <iostream>
using Json=nlohmann::json;
static std::string raw_file(const char*p){std::ifstream f(p,std::ios::binary);return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){
 if(argc!=8&&argc!=9)return 2;const auto model=Json::parse(raw_file(argv[1])),gate=Json::parse(raw_file(argv[2]));
 const std::string mixed=raw_file(argv[3]),mixedseal=raw_file(argv[4]),q4=raw_file(argv[5]),q4seal=raw_file(argv[6]),q4layout=raw_file(argv[7]);
 const auto metadata=[&](const std::string&path,const Json&record,const qwen_app::SourceIdentity&,std::string*out){
  const auto&raw=path.find("retained-mixed-proof.json")!=std::string::npos?mixedseal:path.find("retained-Q4-proof.json")!=std::string::npos?q4seal:
   path.find("retained-Q4-layout.json")!=std::string::npos?q4layout:path.find("expert-q4-")!=std::string::npos?q4:mixed;
  if(raw.size()!=record.at("bytes")||qwen_app::sha256_metadata_bytes(raw)!=record.at("sha256"))throw std::runtime_error("Immutable metadata fixture hash differs");
  if(out)*out=raw;return Json::parse(raw);
 };
 const auto proof=Json::parse(gate.at("Expert_all_Q2_source_integrity").at("raw").get<std::string>());const std::string root=proof.at("source_directory");
 qwen_app::ExpertAllQ2Receipt admitted(model);auto sources=qwen_app::expert_all_q2_source_integrity(gate,model,root,admitted.mapped_bytes,metadata);
 if(sources.logical.size()!=76||qwen_app::expert_q2_pending_segments.size()!=74||sources.physical.size()>1024)return 3;
 std::vector<bool>used(sources.physical.size());unsigned segments=0;std::uint64_t bytes=0;
 for(const auto&f:sources.logical){bytes+=f.bytes;for(const auto j:f.parts){if(j>=used.size())return 4;used[j]=true;}}
 for(const auto&plan:qwen_app::expert_q2_pending_segments){std::uint64_t cursor=0;const auto file=std::find_if(sources.logical.begin(),sources.logical.end(),[&](const auto&f){return f.path==plan.path;});if(file==sources.logical.end())return 5;
  for(const auto&s:plan.segments){if(!s.bytes||s.logical_offset!=cursor||s.physical>=used.size()||s.physical_offset>sources.physical[s.physical].bytes||s.bytes>sources.physical[s.physical].bytes-s.physical_offset)return 6;used[s.physical]=true;cursor+=s.bytes;++segments;}
  if(cursor!=file->bytes)return 7;
 }
 if(bytes!=151157049472ULL||std::find(used.begin(),used.end(),false)!=used.end()||segments>8192)return 8;
 if(argc==9){Json physical=Json::array(),logical=Json::array();
  for(const auto&f:sources.physical)physical.push_back({{"path",f.path},{"bytes",f.bytes},{"identity",f.identity}});
  for(const auto&f:sources.logical){Json ranges=Json::array();const auto plan=std::find_if(qwen_app::expert_q2_pending_segments.begin(),qwen_app::expert_q2_pending_segments.end(),[&](const auto&p){return p.path==f.path;});
   if(plan!=qwen_app::expert_q2_pending_segments.end())for(const auto&s:plan->segments)ranges.push_back({{"logical_offset",s.logical_offset},{"bytes",s.bytes},{"physical",s.physical},{"physical_offset",s.physical_offset}});
   else{std::uint64_t at=0;for(const auto j:f.parts){ranges.push_back({{"logical_offset",at},{"bytes",sources.physical[j].bytes},{"physical",j},{"physical_offset",0}});at+=sources.physical[j].bytes;}}
   logical.push_back({{"path",f.path},{"bytes",f.bytes},{"ranges",ranges}});
  }
  std::ofstream out(argv[8],std::ios::binary);out<<Json({{"schema","ps5-qwen-all-q2-metadata-topology-control-v1"},{"metadata_only",true},{"not_for_deployment",true},{"physical",physical},{"logical",logical}}).dump(2)<<'\n';if(!out)return 10;
 }
 unsigned refused=0;const auto reject=[&](Json candidate,Json seal){qwen_app::expert_q2_pending_segments.clear();auto g=gate;const auto raw=seal.dump();g["Expert_all_Q2_source_integrity"]["raw"]=raw;g["Expert_all_Q2_source_integrity"]["sha256"]=qwen_app::sha256_metadata_bytes(raw);
  try{qwen_app::ExpertAllQ2Receipt shape(candidate);(void)qwen_app::expert_all_q2_source_integrity(g,candidate,root,shape.mapped_bytes,metadata);}catch(const std::exception&){++refused;return;}throw std::runtime_error("Malformed all-Expert Q2 source accepted");};
 unsigned first=0;while(model["files"][first]["reused_original"]==true)++first;
 auto c=model;c["Down_encoding"]="upstream_maxabs";reject(c,proof);
 c=model;c["Down_files"].erase(c["Down_files"].end()-1);reject(c,proof);
 c=model;c["Down_files"][0]["bytes"]=235929599;reject(c,proof);
 c=model;c["Down_files"][0]["sha256"]=std::string(64,'0');reject(c,proof);
 c=model;c["retained_mixed_model_receipt"]["sha256"]=std::string(64,'0');reject(c,proof);
 c=model;c["files"][first]["regions"].erase(c["files"][first]["regions"].begin());reject(c,proof);
 c=model;for(auto&r:c["files"][first]["regions"])if(r["storage"]=="retained_mixed"){r["storage_offset"]=r["storage_offset"].get<std::uint64_t>()+32;break;}reject(c,proof);
 c=model;for(auto&t:c["tensors"])if(t["type"]=="Q2_K"){t["payload_sha256"]=std::string(64,'0');break;}reject(c,proof);
 c=model;c["KV_quantization"]=true;reject(c,proof);
 auto s=proof;s["Down_files"][48]["identity"][5]=1;reject(model,s);
 s=proof;s["logical_files"][first]["parts"][0]["identity"][5]=1;reject(model,s);
 s=proof;s["original_BF16_Q4_and_mixed_sources_unchanged"]=false;reject(model,s);
 s=proof;s["source_writes"]=1;reject(model,s);
 if(refused!=13)return 9;
 std::cout<<"{\"complete_all_Expert_Q2_metadata_passed\":true,\"logical_files\":76,\"composite_files\":74,\"physical_sources\":"<<sources.physical.size()<<",\"source_segments\":"<<segments<<",\"invalid_candidates_refused\":13,\"metadata_fixture_only\":true,\"PS5_operations\":0}\n";
}
