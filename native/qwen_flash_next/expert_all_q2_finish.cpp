// SPDX-License-Identifier: MIT
// Publish owned GGUF headers, verify every logical byte and retain all controls.
#include "expert_all_q2_finish_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();uint64_t split_now_ns();
unsigned qwen_sha256_acceleration_available();
}
namespace {
using Key=std::array<uint64_t,10>;constexpr size_t window_bytes=8u<<20;
void*window=nullptr;uint64_t begun=0,completed=0,spans=0;int active_fd=-1;unsigned active_part=UINT32_MAX;
std::array<Key,74>header_keys{};
void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable all-Q2 finish journal failed");}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
void close_fd(int&fd){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
Key key(const struct stat&s){return{uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p,bool dir=false){struct stat s{};need(!lstat(p,&s)&&(dir?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Immutable all-Q2 source path missing");return key(s);}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_size>0,"Regular all-Q2 Direct descriptor required");return key(s);}
Key expected(unsigned i){const auto&p=finish_parts[i];return p.header<0?p.identity:header_keys.at(unsigned(p.header));}
void record_key(const std::string&label,const Key&k){auto s=label;for(auto v:k)s+=" "+std::to_string(v);line(s);}
void boundary(){const auto n=split_now_ns();need(n>=begun&&n-begun<=1800000000000ULL&&split_headroom(),"All-Q2 CPU finish deadline or memory boundary refused");}
void capacity(){struct statfs s{};need(!statfs(finish_directory,&s)&&s.f_bsize==65536&&s.f_bavail>0&&uint64_t(s.f_bavail)*s.f_bsize>=(2ull<<30)+(16ull<<20),"Header publication must preserve two GiB of available disk space");}
std::string hex(sha256_t*h){unsigned char d[32];sha256_final(h,d);std::string s;for(auto v:d){s+="0123456789abcdef"[v>>4];s+="0123456789abcdef"[v&15];}return s;}
void sources_intact(bool with_headers){for(unsigned i=0;i<sizeof(finish_parts)/sizeof(finish_parts[0]);++i)if(with_headers||finish_parts[i].header<0)need(path_key(finish_parts[i].path)==expected(i),"A sealed mixed, original or new Down source changed");}
void close_source(){if(active_fd>=0){need(fd_key(active_fd)==expected(active_part)&&path_key(finish_parts[active_part].path)==expected(active_part),"Source changed before positive descriptor close");close_fd(active_fd);}active_part=UINT32_MAX;}
void select(unsigned index){if(active_part==index)return;close_source();need(index<sizeof(finish_parts)/sizeof(finish_parts[0]),"Physical source index overflow");const auto&p=finish_parts[index];active_fd=open(p.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(active_fd>=0&&(fcntl(active_fd,F_GETFL)&O_DIRECT)&&fd_key(active_fd)==expected(index)&&path_key(p.path)==expected(index),"Exact read-only Direct source required");active_part=index;}
void headers(int pack_fd,const Key&pack_key){
 for(unsigned i=0;i<74;++i){boundary();capacity();const auto&h=finish_headers[i];const auto target=std::string(finish_directory)+"/"+h.name,pending=target+".pending";struct stat absent{};errno=0;need(lstat(target.c_str(),&absent)&&errno==ENOENT,"New header final path must be absent");int fd=open(pending.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Exclusive new header output required");
  try{for(uint64_t at=0;at<h.bytes;){boundary();const auto n=size_t(std::min<uint64_t>(window_bytes,h.bytes-at)),request=(n+16383)&~size_t(16383);line("BEFORE own_header_write index="+std::to_string(i)+" offset="+std::to_string(at));need(pread(pack_fd,window,request,h.pack_offset+at)==ssize_t(request)&&fd_key(pack_fd)==pack_key,"Sealed header pack read differs");need(pwrite(fd,window,request,at)==ssize_t(request),"New dense header write short");line("RETURN own_header_write");at+=n;}
   need(!ftruncate(fd,h.bytes)&&!fsync(fd),"New header exact size/fsync failed");close_fd(fd);fd=open(pending.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Header complete Direct readback required");const auto before=fd_key(fd);need(before[5]==h.bytes,"Header readback size differs");sha256_t hash;sha256_init(&hash);
   for(uint64_t at=0;at<h.bytes;){boundary();const auto n=size_t(std::min<uint64_t>(window_bytes,h.bytes-at));need(pread(fd,window,(n+16383)&~size_t(16383),at)==ssize_t(n),"Header complete readback short");sha256_update(&hash,static_cast<unsigned char*>(window),n);at+=n;}
   need(hex(&hash)==h.sha256&&fd_key(fd)==before&&path_key(pending.c_str())==before&&pread(fd,window,16384,(h.bytes+16383)&~uint64_t(16383))==0,"Header complete SHA256, identity or EOF differs");need(!fchmod(fd,0644)&&!fsync(fd),"Own new header seal failed");close_fd(fd);errno=0;need(lstat(target.c_str(),&absent)&&errno==ENOENT&&!rename(pending.c_str(),target.c_str()),"New header publication cannot overwrite an existing path");header_keys[i]=path_key(target.c_str());need(header_keys[i][2]==0100644&&!header_keys[i][3]&&!header_keys[i][4]&&header_keys[i][5]==h.bytes,"Published header owner or bytes differ");line("ALL_Q2_HEADER index="+std::to_string(i)+" file="+std::to_string(h.file)+" bytes="+std::to_string(h.bytes)+" SHA256="+h.sha256);record_key("ALL_Q2_HEADER_ID index="+std::to_string(i),header_keys[i]);
  }catch(...){close_fd(fd);throw;}
 }
}
void logical_file(const FinishFile&f){
 sha256_t whole;sha256_init(&whole);uint64_t cursor=0;unsigned range_index=f.first_range;
 for(unsigned hi=0;hi<f.hashes;++hi){const auto&h=finish_hashes[f.first_hash+hi];need(h.bytes&&h.bytes<=f.bytes-cursor,"Complete hash span bounds differ");sha256_t part_hash;sha256_init(&part_hash);uint64_t remaining=h.bytes;
  while(remaining){boundary();need(range_index<f.first_range+f.ranges,"Logical source plan ended early");const auto&r=finish_ranges[range_index];need(cursor>=r.logical&&cursor-r.logical<r.bytes,"Logical all-Q2 source partition differs");select(r.physical);const auto k=expected(r.physical);const auto offset=r.offset+cursor-r.logical;need(offset<k[5],"Physical all-Q2 source bounds differ");const auto aligned=offset&~uint64_t(16383),skip=size_t(offset-aligned);const auto n=size_t(std::min({remaining,r.bytes-(cursor-r.logical),uint64_t(window_bytes-skip),k[5]-offset}));need(n,"Nonempty all-Q2 source read required");const auto request=(skip+n+16383)&~size_t(16383);line("BEFORE logical_Direct_read file="+std::to_string(f.index)+" offset="+std::to_string(cursor));const auto got=pread(active_fd,window,request,aligned);line("RETURN logical_Direct_read bytes="+std::to_string(got));need(got==int64_t(std::min<uint64_t>(request,k[5]-aligned))&&fd_key(active_fd)==k,"Complete stable logical source Direct read failed");auto*data=static_cast<unsigned char*>(window)+skip;sha256_update(&whole,data,n);sha256_update(&part_hash,data,n);cursor+=n;remaining-=n;if(cursor==r.logical+r.bytes)++range_index;
  }
  need(hex(&part_hash)==h.sha256,"Complete original/reused/Down payload SHA256 differs");++spans;line("ALL_Q2_HASH_SPAN file="+std::to_string(f.index)+" span="+std::to_string(hi)+" complete_SHA256_verified=1");
 }
 need(cursor==f.bytes&&range_index==f.first_range+f.ranges,"Complete all-Q2 logical file byte accounting differs");close_source();const auto digest=hex(&whole);need(!*f.original_whole||digest==f.original_whole,"Unchanged original logical source hash differs");line("ALL_Q2_FILE file="+std::to_string(f.index)+" bytes="+std::to_string(f.bytes)+" SHA256="+digest);++completed;
}
}
int main(int argc,char**){if(!split_open_journal())return 2;begun=split_now_ns();bool ok=false,mapped=false;int64_t physical=-1;int pack_fd=-1;
 try{line("BEGIN nonce=" FINISH_NONCE " CPU_only=1 source_writes=0 GPU_calls=0 title_launches=0");need(finish_deployable&&(argc==0||argc==1)&&begun&&split_context(1)&&split_context(2),"Completed actual Down conversion and idle context required");boundary();need(path_key(finish_directory,true)==finish_root_identity,"Exact positively closed Down directory required");sources_intact(false);need(qwen_sha256_acceleration_available()==1,"Qualified SHA extension required");need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Fixed all-Q2 finish Direct allocation failed");if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window||uintptr_t(window)%16384)retain();mapped=true;
  pack_fd=open(finish_pack,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(pack_fd>=0&&(fcntl(pack_fd,F_GETFL)&O_DIRECT),"Complete header pack Direct descriptor required");const auto pack_key=fd_key(pack_fd);need(pack_key[5]==finish_pack_bytes&&!pack_key[3]&&!pack_key[4],"Header pack byte count/owner differs");sha256_t hash;sha256_init(&hash);for(uint64_t at=0;at<finish_pack_bytes;){boundary();const auto n=size_t(std::min<uint64_t>(window_bytes,finish_pack_bytes-at));need(pread(pack_fd,window,n,at)==ssize_t(n),"Header pack complete Direct read short");sha256_update(&hash,static_cast<unsigned char*>(window),n);at+=n;}need(hex(&hash)==finish_pack_sha256&&fd_key(pack_fd)==pack_key&&path_key(finish_pack)==pack_key&&pread(pack_fd,window,16384,finish_pack_bytes)==0,"Header pack complete hash, identity or EOF differs");headers(pack_fd,pack_key);close_fd(pack_fd);sources_intact(true);
  for(const auto&f:finish_files){need(split_context(3),"Idle CPU owner changed during all-Q2 logical hashing");logical_file(f);}need(completed==76,"Every logical model split required");sources_intact(true);const auto root=path_key(finish_directory,true);need(std::equal(root.begin(),root.begin()+5,finish_root_identity.begin()),"Own candidate root inode or owner changed");record_key("ALL_Q2_DIRECTORY",root);ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" partial_candidate_retained=1 controls_unchanged=1");}catch(...){retain();}}
 close_fd(active_fd);active_part=UINT32_MAX;close_fd(pack_fd);if(mapped){if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();if(!split_context(5)||!split_headroom())ok=false;try{line("END success="+std::to_string(ok)+" files="+std::to_string(completed)+" hash_spans="+std::to_string(spans)+" active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}if(!split_close_journal())return 2;return ok?0:1;
}
