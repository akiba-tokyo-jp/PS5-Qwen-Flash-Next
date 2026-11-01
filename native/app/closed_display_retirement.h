// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cerrno>
#include <string>
#include <stdexcept>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <nlohmann/json.hpp>
extern "C" {
#include "hash/sha256/sha256.h"
}
#include "closed-display-plan.private.h"
namespace qwen_app {namespace closed_display_retirement {
using Json=nlohmann::json;using Key=std::array<std::uint64_t,10>;
inline void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
inline Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
inline Key named(const char*p){const int fd=open(p,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0,"Closed display named identity unavailable");struct stat s{};const int rc=fstat(fd,&s);const bool closed=close(fd)==0;need(!rc&&closed,"Independent diagnostic descriptor did not positively close");return key(s);}
inline Json run(void(*admit)(),void(*stage)(const char*)){
    need(getuid()==1,"Native application diagnostic owner required");
    void*scratch=nullptr;need(!posix_memalign(&scratch,16384,8u<<20)&&scratch,"Bounded owned CPU scratch unavailable");
    std::array<Key,152>verified{};unsigned checked=0,removed=0;Json errors=Json::array();
    try{
        for(unsigned i=0;i<152;++i){admit();const auto&t=closed_display_files[i];int fd=open(t.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0,"Archived native display unavailable");struct stat s{};
            // Match the application's qualified ten-field descriptor ABI. A
            // second O_NOFOLLOW descriptor binds the name without payload lstat.
            const int observed=fstat(fd,&s);const bool same_name=!observed&&named(t.path)==key(s);
            // The title stat bridge reports UID0 for these physically UID1-owned
            // outputs. The process UID1 and normal unlink permissions enforce
            // ownership; exact hashes and two stable descriptors bind the data.
            if(observed||s.st_mode!=0100644||std::uint64_t(s.st_size)!=t.bytes||!same_name)
                throw std::runtime_error("Native diagnostic descriptor differs rc="+std::to_string(observed)+" mode="+std::to_string(s.st_mode)+" uid="+std::to_string(s.st_uid)+" gid="+std::to_string(s.st_gid)+" bytes="+std::to_string(s.st_size)+" named="+std::to_string(same_name));
            const auto before=key(s);
            sha256_t hash;sha256_init(&hash);
            for(std::uint64_t at=0;at<t.bytes;){admit();const auto n=std::min<std::uint64_t>(8u<<20,t.bytes-at);need(pread(fd,scratch,(n+16383)&~std::uint64_t(16383),at)==std::int64_t(n),"Whole native diagnostic read failed");sha256_update(&hash,static_cast<unsigned char*>(scratch),n);at+=n;}
            unsigned char d[32];sha256_final(&hash,d);std::string hex;for(auto b:d){hex+="0123456789abcdef"[b>>4];hex+="0123456789abcdef"[b&15];}
            need(hex==t.sha256&&!fstat(fd,&s)&&key(s)==before&&named(t.path)==before&&pread(fd,scratch,16384,(t.bytes+16383)&~std::uint64_t(16383))==0,"Complete host/native diagnostic SHA256 or identity differs");need(!close(fd),"Diagnostic descriptor retirement failed");verified[i]=before;++checked;
            if(i%16==15)stage("closed_display_CPU_hashes_verified_GPU_not_started");
        }
        for(unsigned i=0;i<152;++i){admit();const auto&t=closed_display_files[i];need(named(t.path)==verified[i],"Archived display changed before owner removal");const int rc=unlink(t.path),error=errno;if(!rc)++removed;else errors.push_back({{"index",i},{"errno",error}});}
    }catch(...){free(scratch);throw;}
    free(scratch);return{{"completed",removed==152},{"verified_archives",checked},{"removed_displays",removed},{"errors",errors},{"scratch_positively_freed",true},{"owner_UID",getuid()},{"permission_or_flag_changes",0},{"model_sources_started",false},{"model_loaded",false},{"GPU_initializations",0},{"GPU_calls",0}};
}
}}
