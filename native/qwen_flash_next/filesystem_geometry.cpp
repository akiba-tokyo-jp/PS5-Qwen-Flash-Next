// SPDX-License-Identifier: MIT
// Compare the staging and application filesystems using the qualified CPU ABI.
#include <cstdint>
#include <limits>
#include <string>
#include <sys/mount.h>
extern "C" {
int split_report_line(const char *);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();
}
int main(int argc,char **) {
    if(!split_open_journal())return 2;
    bool ok=(argc==0||argc==1)&&split_context(1)&&split_context(2)&&split_headroom();
    for(const char*path:{"/data/ai","/data/ai/native-moss-image-sft/PPSA99190"}) {
        if(!ok)break;
        struct statfs v{};ok=!statfs(path,&v)&&v.f_bsize>0&&v.f_bavail>=0&&
            std::uint64_t(v.f_bavail)<=std::numeric_limits<std::uint64_t>::max()/v.f_bsize;
        if(!ok)break;
        std::uint64_t fsid=0;const auto*b=reinterpret_cast<const unsigned char*>(&v.f_fsid);
        for(unsigned i=0;i<sizeof(v.f_fsid)&&i<8;++i)fsid|=std::uint64_t(b[i])<<(i*8);
        const auto line="SCOPE_CAPACITY path="+std::string(path)+" fsid="+std::to_string(fsid)+
            " version="+std::to_string(v.f_version)+" total_blocks="+std::to_string(v.f_blocks)+" io_bytes="+std::to_string(v.f_iosize)+" block_bytes="+std::to_string(v.f_bsize)+" available_blocks="+std::to_string(v.f_bavail)+
            " available_bytes="+std::to_string(std::uint64_t(v.f_bavail)*v.f_bsize)+
            " free_blocks="+std::to_string(v.f_bfree)+" file_nodes="+std::to_string(v.f_files)+
            " free_file_nodes="+std::to_string(v.f_ffree)+" flags="+std::to_string(v.f_flags);
        ok=split_report_line(line.c_str())&&split_context(3)&&split_headroom();
    }
    split_report_line(ok?"END success=1 CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0":
                         "END success=0 CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0");
    return split_close_journal()?(ok?0:3):4;
}
