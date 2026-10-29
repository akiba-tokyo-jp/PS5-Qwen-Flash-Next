// SPDX-License-Identifier: MIT
#pragma once
#include "expert_all_q2_receipt.h"
#include "expert_q2_composite_source.h"
#include <map>
#include <set>

namespace qwen_app {
// The original mixed source validator remains intact. Its complete logical
// ranges are clipped to byte-identical Gate/Up and non-Expert payloads only.
template<class MetadataRead>inline SplitModelIntegrity expert_all_q2_source_integrity(
 const nlohmann::json&gate,const nlohmann::json&receipt,const std::string&root,
 std::uint64_t total_bytes,MetadataRead read_metadata){
 using Json=nlohmann::json;
 const auto require=[](bool v){if(!v)throw std::runtime_error("Complete all-Expert Q2 source plan is not admitted");};
 require(expert_q2_source_root(root)&&expert_q2_pending_segments.empty()&&receipt.at("packed_composite_sources")==true);
 const auto&proof=gate.at("Expert_all_Q2_source_integrity");require(proof.at("schema")=="ps5-qwen-expert-all-q2-source-policy-v1");
 const auto raw=proof.at("raw").get<std::string>();require(!raw.empty()&&raw.size()<=(2u<<20)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
 const auto sealed=Json::parse(raw);
 require(sealed.at("schema")=="ps5-qwen-expert-all-q2-native-source-integrity-v1"&&sealed.at("model_receipt_sha256")==gate.at("model_receipt_sha256")&&
  sealed.at("source_directory")==root&&sealed.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5)&&
  sealed.at("logical_bytes")==total_bytes&&sealed.at("Down_encoding")=="signed_FP16_scale_MSE_fit");
 for(const char*k:{"same_existing_title_nullfs_namespace","all_new_parts_complete_Direct_SHA256_readback","all_parts_unchanged_since_readback",
  "CPU_owners_positively_closed","original_BF16_Q4_and_mixed_sources_unchanged","Gate_Up_and_non_Expert_payloads_byte_exact"})require(sealed.at(k)==true);
 for(const char*k:{"source_writes","GPU_calls","automatic_retries","permission_changes","mount_changes"})require(sealed.at(k)==0);
 require(sealed.at("model_loaded")==false);
 const auto identity=[&](const Json&j){require(j.is_array()&&j.size()==10);SourceIdentity k{};for(unsigned i=0;i<10;++i){require(j[i].is_number_integer()&&j[i]>=0);k[i]=j[i].get<std::uint64_t>();}
  require(k[0]&&k[1]&&!k[3]&&!k[4]&&k[5]&&(k[2]==0100644||k[2]==0040755)&&k[7]<1000000000&&k[9]<1000000000);return k;};
 const auto digest=[&](const Json&j){const auto s=j.get<std::string>();require(s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos);return s;};
 const auto&backing=sealed.at("backing_metadata");require(backing.size()==1);
 std::string oldraw;
 const Json oldseal=read_metadata(root+"/retained-mixed-proof.json",receipt.at("retained_mixed_source_seal"),identity(backing.at(0).at("identity")),&oldraw);
 require(oldseal.at("schema")=="ps5-qwen-expert-q2-packed-source-integrity-v1");
 const auto oldroot=oldseal.at("source_directory").get<std::string>();require(expert_q2_source_root(oldroot)&&oldroot!=root);
 const auto&oldrecord=receipt.at("retained_mixed_model_receipt");require(oldrecord.at("bytes")==754194&&oldrecord.at("sha256")=="d28acbe933416b9fe91ca056ce70be3e3cb64bf8940c90344835e5fb84910024");
 const Json oldreceipt=read_metadata(oldroot+"/model-receipt.json",oldrecord,identity(oldseal.at("receipt_identity")),nullptr);
 ExpertQ2Receipt oldmanifest(oldreceipt);
 Json oldgate={{"model_receipt_sha256",oldrecord.at("sha256")},{"model_receipt_bytes",oldrecord.at("bytes")},
  {"Expert_Q2_source_integrity",{{"schema","ps5-qwen-expert-q2-source-policy-v1"},{"raw",oldraw},{"sha256",receipt.at("retained_mixed_source_seal").at("sha256")}}}};
 const auto old=expert_q2_composite_source_integrity(oldgate,oldreceipt,oldroot,oldmanifest.mapped_bytes,read_metadata);
 auto oldplans=std::move(expert_q2_pending_segments);expert_q2_pending_segments.clear();require(oldplans.size()==74);
 std::map<std::string,Json>old_tensors;for(const auto&t:oldreceipt.at("tensors"))require(old_tensors.emplace(t.at("name").get<std::string>(),t).second);
 const auto&down=receipt.at("Down_files"),&downproof=sealed.at("Down_files");require(down.size()==49&&downproof.size()==49);
 std::map<std::string,unsigned>down_names;
 for(unsigned i=0;i<49;++i){const auto&d=down[i],&s=downproof[i];const auto name="blk."+std::to_string(i)+".ffn_down_exps.weight";
  require(d.at("name")==name&&d.at("layer")==i&&d.at("path")=="down-"+std::to_string(i)+".q2_0"&&d.at("bytes")==235929600&&
   s.at("path")==root+"/"+d.at("path").get<std::string>()&&s.at("bytes")==d.at("bytes")&&s.at("sha256")==d.at("sha256"));
  digest(d.at("sha256"));digest(d.at("original_payload_sha256"));const auto k=identity(s.at("identity"));require(k[2]==0100644&&k[5]==235929600);down_names.emplace(name,i);
 }
 SplitModelIntegrity result;result.prior.directory=identity(sealed.at("directory_identity"));result.part_directory_identity=result.prior.directory;
 result.prior.receipt=identity(sealed.at("receipt_identity"));require(result.prior.directory[2]==0040755&&result.prior.receipt[2]==0100644&&result.prior.receipt[5]==gate.at("model_receipt_bytes"));
 std::map<std::string,std::size_t>physical;
 const auto add=[&](const SourceFile&f){const auto found=physical.find(f.path);if(found!=physical.end()){const auto&oldf=result.physical[found->second];require(oldf.bytes==f.bytes&&oldf.identity==f.identity);return found->second;}
  require(result.physical.size()<1024);const auto n=result.physical.size();physical.emplace(f.path,n);result.physical.push_back(f);return n;};
 std::vector<ExpertQ2SourceSegments>plans;std::set<std::string>used_down;std::uint64_t logical_total=0;unsigned regions_total=0;
 const auto&files=sealed.at("logical_files");require(files.size()==76);
 for(unsigned i=0;i<76;++i){const auto&f=receipt.at("files")[i],&s=files[i],&previous=oldreceipt.at("files")[i];
  const auto name=f.at("path").get<std::string>();const auto bytes=receipt_integer(f,"bytes");require(s.at("path")==name&&previous.at("path")==name&&s.at("bytes")==bytes&&s.at("sha256")==f.at("sha256"));
  LogicalSourceFile logical{expert_q2_logical_path(receipt,root,name),bytes,{}};
  if(f.at("reused_original")==true){require(previous.at("reused_original")==true&&bytes==previous.at("bytes")&&f.at("sha256")==previous.at("sha256"));
   for(const auto index:old.logical[i].parts)logical.parts.push_back(add(old.physical[index]));
  }else{
   const auto header=receipt_integer(f,"header_bytes");require(header&&header<=(64u<<20)&&f.at("packed_bytes")==header&&s.at("packed_bytes")==header&&s.at("parts").size()==1&&f.at("parts").size()==1);
   const auto&p=s.at("parts")[0];const auto k=identity(p.at("identity"));const auto path=root+"/"+name;
   require(p.at("path")==path&&p.at("bytes")==header&&p.at("offset")==0&&k[2]==0100644&&k[5]==header&&p.at("sha256")==f.at("parts")[0].at("sha256"));digest(p.at("sha256"));
   const auto header_index=add({path,header,k});logical.parts.push_back(header_index);ExpertQ2SourceSegments plan{logical.path,{}};
   const auto&r=f.at("regions");require(!r.empty());std::size_t at=0;std::uint64_t cursor=0;
   const auto region=[&](std::uint64_t lo,std::uint64_t n,const char*storage,std::uint64_t offset)->const Json&{require(at<r.size()&&++regions_total<=8192);const auto&v=r[at++];require(v.at("logical_offset")==lo&&v.at("bytes")==n&&v.at("storage")==storage&&v.at("storage_offset")==offset);return v;};
   region(0,header,"new_header",0);plan.segments.push_back({0,header,header_index,0});cursor=header;
   for(const auto&t:receipt.at("tensors"))if(t.at("file")==name){const auto n=receipt_integer(t,"bytes");require(receipt_integer(t,"offset")==cursor&&n&&n<=bytes-cursor);const auto tn=t.at("name").get<std::string>();
    if(t.at("type")=="Q2_0"){const auto j=down_names.at(tn);const auto&d=down[j],&proofrow=downproof[j],&v=region(cursor,n,"Down_Q2_0",0);
     require(n==235929600&&t.at("payload_sha256")==d.at("sha256")&&v.at("tensor")==tn&&v.at("layer")==j&&v.at("output_name")==d.at("path")&&used_down.insert(tn).second);
     plan.segments.push_back({cursor,n,add({proofrow.at("path").get<std::string>(),n,identity(proofrow.at("identity"))}),0});
    }else{const auto&prior=old_tensors.at(tn);require(prior.at("file")==name&&prior.at("type")==t.at("type")&&prior.at("shape")==t.at("shape")&&prior.at("bytes")==n&&prior.at("payload_sha256")==t.at("payload_sha256"));
     const auto offset=receipt_integer(prior,"offset");const auto&v=region(cursor,n,"retained_mixed",offset);require(v.at("tensor")==tn&&v.at("retained_file")==name&&v.at("payload_sha256")==t.at("payload_sha256"));
     const auto oldplan=std::find_if(oldplans.begin(),oldplans.end(),[&](const auto&x){return x.path==old.logical[i].path;});require(oldplan!=oldplans.end());std::uint64_t done=0;
     for(const auto&segment:oldplan->segments){const auto lo=std::max(offset,segment.logical_offset),hi=std::min(offset+n,segment.logical_offset+segment.bytes);if(lo>=hi)continue;
      require(lo==offset+done&&segment.physical<old.physical.size());const auto count=hi-lo;const auto index=add(old.physical[segment.physical]);plan.segments.push_back({cursor+done,count,index,segment.physical_offset+lo-segment.logical_offset});done+=count;}
     require(done==n);
    }
    cursor+=n;require(cursor%32==0);
   }
   require(cursor==bytes&&at==r.size());plans.push_back(std::move(plan));
  }
  require(!logical.parts.empty());result.prior.files.push_back(result.physical[logical.parts.front()].identity);logical_total+=bytes;result.logical.push_back(std::move(logical));
 }
 require(logical_total==total_bytes&&plans.size()==74&&used_down.size()==49);
 result.prior.report_sha256=proof.at("sha256").get<std::string>();result.prior.snapshot_sha256=result.prior.report_sha256;result.prior.original_elapsed_ms=receipt_integer(sealed,"verification_elapsed_ms");
 expert_q2_pending_segments=std::move(plans);return result;
}
inline SplitModelIntegrity expert_all_q2_source_integrity(const nlohmann::json&gate,const nlohmann::json&receipt,const std::string&root,std::uint64_t bytes){return expert_all_q2_source_integrity(gate,receipt,root,bytes,expert_q2_backing_metadata);}
}
