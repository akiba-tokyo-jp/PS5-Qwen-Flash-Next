// SPDX-License-Identifier: MIT
#include "resident-mapped-source.private.h"
#include <iostream>
#include <map>
using namespace qwen_app;
struct Ops:SourceReadOps{
 std::vector<SourceFile>files;std::map<int,std::size_t>fds;int next=1;unsigned reads=0;bool short_read=false,bad_identity=false;
 SourceIdentity identity(int fd)override{auto k=files.at(fds.at(fd)).identity;if(bad_identity)++k[1];return k;}
 int open_direct(const std::string&p)override{for(std::size_t i=0;i<files.size();++i)if(files[i].path==p){fds[next]=i;return next++;}return -1;}
 bool close_file(int fd)override{return fds.erase(fd)==1;}
 std::int64_t read_at(int fd,void*out,std::size_t n,std::uint64_t offset)override{const auto i=fds.at(fd);if(files[i].bytes<(16u<<20)||offset+n>files[i].bytes)throw std::runtime_error("Preflight touched a header or escaped its payload");for(std::size_t j=0;j<n;++j)static_cast<unsigned char*>(out)[j]=(offset+j+i*17)%251;++reads;return short_read?std::int64_t(n)-1:n;}
 std::uint64_t system_headroom()override{return 512ull<<20;}
};
int main(){
 std::vector<unsigned char>bytes(model_read_window+16384);void*scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(bytes.data())+16383)&~std::uintptr_t(16383));
 unsigned refused=0;
 for(unsigned test=0;test<5;++test){Ops ops;for(const auto n:std::vector<std::uint64_t>{832,1632,test==1?8192ull:32ull<<20}){SourceIdentity k{1,ops.files.size()+1,0100644,0,0,n,1,0,1,0};ops.files.push_back({"source-"+std::to_string(ops.files.size()),n,k});}
  ops.short_read=test==2;ops.bad_identity=test==3;ResidentMappedSourceReader reader(ops.files,ops,scratch);
  try{reader.qualify_source_schedule();if(test==4){reader.qualify_source_schedule();throw std::logic_error("Duplicate qualification accepted");}if(test)throw std::logic_error("Malformed preflight accepted");if(reader.stats().parallel_batches!=1||reader.stats().coalesced_batches!=1||ops.reads!=5)throw std::logic_error("Original scheduler paths not exercised");reader.close_completed();if(!ops.fds.empty())throw std::logic_error("Descriptors remain");}
  catch(const std::logic_error&){throw;}catch(const std::exception&){if(!test)throw;++refused;}
 }
 if(refused!=4)return 2;std::cout<<"{\"small_headers_skipped\":true,\"original_parallel_and_coalesced_byte_checks\":true,\"malformed_or_duplicate_qualifications_refused\":4}\n";
}
