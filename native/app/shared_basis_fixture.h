// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "ggml-quants.h"
#include "shared_basis_assets.private.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <unistd.h>
#include <vector>
namespace qwen_app {void verify_native_startup_file_direct(const std::string&,std::uint64_t,const std::string&,unsigned);}
namespace qwen_app {namespace shared_basis_fixture {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
inline void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
struct Resources {
 ggml_backend_t backend=nullptr;ggml_context*ctx=nullptr;ggml_backend_buffer_t buffer=nullptr;bool idle=true;
 void retire(void(*checkpoint)()){need(idle,"Shared-basis unknown completion retains resources");if(buffer){ggml_backend_buffer_free(buffer);buffer=nullptr;}if(ctx){ggml_free(ctx);ctx=nullptr;}if(backend){ggml_backend_free(backend);backend=nullptr;}checkpoint();}
 ~Resources(){if(idle){if(buffer)ggml_backend_buffer_free(buffer);if(ctx)ggml_free(ctx);if(backend)ggml_backend_free(backend);}}
};
inline Json run(void(*checkpoint)(),void(*stage)(const char*),void(*admit)()) {
 verify_native_startup_file_direct(shared_basis_path,shared_basis_bytes,shared_basis_sha,60);
 void*raw=nullptr;need(posix_memalign(&raw,65536,shared_basis_bytes)==0,"Shared-basis bounded source window unavailable");
 const int fd=open(shared_basis_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0){std::free(raw);throw std::runtime_error("Shared-basis immutable input unavailable");}
 for(size_t at=0;at<shared_basis_bytes;at+=2u<<20){const size_t n=std::min(size_t(2u<<20),size_t(shared_basis_bytes)-at);const auto got=pread(fd,static_cast<char*>(raw)+at,n,at);if(got!=ssize_t(n)){close(fd);std::free(raw);throw std::runtime_error("Shared-basis input read incomplete");}}
 need(close(fd)==0,"Shared-basis source did not close");std::vector<unsigned char>data(static_cast<unsigned char*>(raw),static_cast<unsigned char*>(raw)+shared_basis_bytes);std::free(raw);
 // These are numerical fixture oracles on the console, not host model inference.
 std::array<std::vector<float>,10>deq;
 for(unsigned i=0;i<10;++i){const auto&s=shared_basis_sections[i];const size_t count=s.ne[0]*s.ne[1]*s.ne[2];deq[i].resize(count);const void*p=data.data()+s.offset;
  if(s.type==GGML_TYPE_Q2_K)dequantize_row_q2_K(static_cast<const block_q2_K*>(p),deq[i].data(),count);
  else if(s.type==GGML_TYPE_TQ1_0)dequantize_row_tq1_0(static_cast<const block_tq1_0*>(p),deq[i].data(),count);
  else if(s.type==GGML_TYPE_Q8_0)dequantize_row_q8_0(static_cast<const block_q8_0*>(p),deq[i].data(),count);
  else throw std::runtime_error("Unexpected shared-basis fixture type");
 }
 unsigned graphs=0;Json cases=Json::array();const auto deadline=Clock::now()+std::chrono::seconds(600);
 for(unsigned scenario=0;scenario<5;++scenario){const unsigned tokens=scenario==4?30:(scenario%2)+1,selected=scenario==4?6:2;const bool duplicate=scenario==2||scenario==3;
  admit();Resources r;r.backend=ggml_backend_vk_init(0);need(r.backend,"Shared-basis Vulkan backend unavailable");ggml_init_params p{};p.mem_size=128*ggml_tensor_overhead()+3*ggml_graph_overhead_custom(64,false);p.no_alloc=true;r.ctx=ggml_init(p);need(r.ctx,"Shared-basis graph metadata unavailable");
  std::array<ggml_tensor*,10>w{};for(unsigned i=0;i<10;++i){const auto&s=shared_basis_sections[i];w[i]=ggml_new_tensor_3d(r.ctx,s.type,s.ne[0],s.ne[1],s.ne[2]);ggml_set_input(w[i]);need(ggml_nbytes(w[i])==s.bytes,"Exact shared-basis tensor bytes required");}
  auto*x=ggml_new_tensor_3d(r.ctx,GGML_TYPE_F32,2560,1,tokens);auto*ids=ggml_new_tensor_2d(r.ctx,GGML_TYPE_I32,selected,tokens);ggml_set_input(x);ggml_set_input(ids);
  std::array<ggml_tensor*,3>out{};std::array<ggml_cgraph*,3>g{};
  for(unsigned arm=0;arm<3;++arm){ggml_tensor*a=nullptr,*b=nullptr;
   if(arm<2){a=ggml_mul_mat_id(r.ctx,w[arm?2:0],x,ids);b=ggml_mul_mat_id(r.ctx,w[arm?3:1],x,ids);}
   else{auto*zg=ggml_mul_mat(r.ctx,w[8],x);auto*zu=ggml_mul_mat(r.ctx,w[9],x);a=ggml_add(r.ctx,ggml_mul_mat_id(r.ctx,w[4],x,ids),ggml_mul_mat_id(r.ctx,w[6],zg,ids));b=ggml_add(r.ctx,ggml_mul_mat_id(r.ctx,w[5],x,ids),ggml_mul_mat_id(r.ctx,w[7],zu,ids));}
   out[arm]=ggml_swiglu_split(r.ctx,a,b);ggml_set_output(out[arm]);g[arm]=ggml_new_graph_custom(r.ctx,64,false);ggml_build_forward_expand(g[arm],out[arm]);
   for(int j=0;j<ggml_graph_n_nodes(g[arm]);++j)need(ggml_backend_supports_op(r.backend,ggml_graph_node(g[arm],j)),"Shared-basis operation unsupported by the selected Vulkan backend");
  }
  auto*canary=ggml_new_tensor_1d(r.ctx,GGML_TYPE_F32,128);ggml_set_input(canary);ggml_set_output(canary);r.buffer=ggml_backend_alloc_ctx_tensors(r.ctx,r.backend);need(r.buffer,"Shared-basis bounded device tensors unavailable");
  for(unsigned i=0;i<10;++i)ggml_backend_tensor_set(w[i],data.data()+shared_basis_sections[i].offset,0,shared_basis_sections[i].bytes);
  std::vector<float>activation(tokens*2560);for(unsigned t=0;t<tokens;++t)for(unsigned c=0;c<2560;++c)activation[t*2560+c]=float(int((c*37+t*17)%251)-125)/16384.0f;
  std::vector<int>selection(tokens*selected);for(unsigned t=0;t<tokens;++t)for(unsigned e=0;e<selected;++e)selection[t*selected+e]=duplicate?0:(e+t)%3;
  std::array<float,128>guard{};guard.fill(42.125f);ggml_backend_tensor_set(x,activation.data(),0,activation.size()*4);ggml_backend_tensor_set(ids,selection.data(),0,selection.size()*4);ggml_backend_tensor_set(canary,guard.data(),0,sizeof(guard));
  std::array<std::vector<double>,3>references;for(auto&v:references)v.resize(tokens*selected*640);
  for(unsigned t=0;t<tokens;++t){std::array<std::array<double,32>,2>z{};for(unsigned role=0;role<2;++role)for(unsigned rank=0;rank<32;++rank)for(unsigned c=0;c<2560;++c)z[role][rank]+=double(deq[8+role][rank*2560+c])*activation[t*2560+c];
   std::array<std::vector<double>,3>unique;for(auto&v:unique)v.resize(3*640);
   for(unsigned e=0;e<3;++e)for(unsigned row=0;row<640;++row){double sums[3][2]{};
    for(unsigned role=0;role<2;++role){for(unsigned c=0;c<2560;++c){const auto at=(e*640+row)*2560+c;const double v=activation[t*2560+c];sums[0][role]+=double(deq[role][at])*v;sums[1][role]+=double(deq[2+role][at])*v;sums[2][role]+=double(deq[4+role][at])*v;}
     for(unsigned rank=0;rank<32;++rank)sums[2][role]+=double(deq[6+role][(e*640+row)*32+rank])*z[role][rank];}
    for(unsigned arm=0;arm<3;++arm)unique[arm][e*640+row]=(sums[arm][0]/(1+std::exp(-sums[arm][0])))*sums[arm][1];}
   for(unsigned arm=0;arm<3;++arm)for(unsigned e=0;e<selected;++e)std::copy_n(unique[arm].data()+selection[t*selected+e]*640,640,references[arm].data()+(t*selected+e)*640);
  }
  ggml_backend_synchronize(r.backend);checkpoint();std::array<double,3>maximum{},nmse{};
  auto verify=[&](unsigned arm){std::vector<float>actual(references[arm].size());ggml_backend_tensor_get(out[arm],actual.data(),0,actual.size()*4);double error=0,energy=0;
   for(size_t i=0;i<actual.size();++i){need(std::isfinite(actual[i]),"Shared-basis output must be finite");const double d=double(actual[i])-references[arm][i];error+=d*d;energy+=references[arm][i]*references[arm][i];maximum[arm]=std::max(maximum[arm],std::abs(d));}
   const double ratio=error/std::max(energy,1e-30);nmse[arm]=std::max(nmse[arm],ratio);need(ratio<=5e-4,"Shared-basis output differs from complete representation-specific F64 oracle");
   std::vector<float>observed(activation.size());ggml_backend_tensor_get(x,observed.data(),0,observed.size()*4);need(observed==activation,"Shared-basis input canary changed");std::vector<int>io(selection.size());ggml_backend_tensor_get(ids,io.data(),0,io.size()*4);need(io==selection,"Shared-basis indices changed");std::array<float,128>co{};ggml_backend_tensor_get(canary,co.data(),0,sizeof(co));need(co==guard,"Shared-basis output canary changed");};
  auto compute=[&](unsigned arm){admit();need(graphs<180&&Clock::now()<deadline,"Shared-basis finite graph/deadline bound reached");r.idle=false;const auto start=Clock::now();need(ggml_backend_graph_compute(r.backend,g[arm])==GGML_STATUS_SUCCESS,"Shared-basis GPU compute failed; retain owner");ggml_backend_synchronize(r.backend);const auto done=Clock::now();checkpoint();r.idle=true;++graphs;return std::array<double,2>{std::chrono::duration<double,std::micro>(done-start).count(),std::chrono::duration<double,std::micro>(Clock::now()-start).count()};};
  for(unsigned i=0;i<6;++i){compute(i%3);verify(i%3);}Json arms=Json::array();for(unsigned phase:{0u,1u,2u,2u,1u,0u}){Json samples=Json::array(),whole=Json::array();for(unsigned j=0;j<5;++j){const auto v=compute(phase);samples.push_back(v[0]);whole.push_back(v[1]);}verify(phase);arms.push_back({{"arm",phase},{"backend_samples_us",samples},{"whole_samples_us",whole}});}
  ggml_backend_synchronize(r.backend);checkpoint();r.retire(checkpoint);cases.push_back({{"scenario",scenario},{"tokens",tokens},{"selected",selected},{"duplicate_ids",duplicate},{"arms",arms},{"maximum_absolute_error",maximum},{"maximum_NMSE",nmse},{"complete_F64_and_canaries_passed",true},{"positive_retirement",true}});stage("shared_basis_fixture_case_completed_positive_retirement");
 }
 return {{"GPU_graphs",graphs},{"cases",cases},{"all_F64_outputs_passed",true},{"all_canaries_passed",true},{"NMSE_limit",5e-4},{"whole_model_speed_measured",false},{"weight_approximation_quality_not_answer_quality",true}};
}
}}
