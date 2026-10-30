// SPDX-License-Identifier: MIT
// Read-only filesystem capacity using the qualified CPU owner guard.
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
    bool ok=false;
    if((argc==0||argc==1)&&split_context(1)&&split_context(2)&&split_headroom()) {
        struct statfs value{};
        if(!statfs("/data/ai/native-moss-image-sft/PPSA99190",&value)&&value.f_bsize>0&&value.f_bavail>=0&&
           std::uint64_t(value.f_bavail)<=std::numeric_limits<std::uint64_t>::max()/std::uint64_t(value.f_bsize)) {
            const auto bytes=std::uint64_t(value.f_bavail)*std::uint64_t(value.f_bsize);
            const auto line="CAPACITY free_bytes_lower_bound="+std::to_string(bytes)+
                " block_bytes="+std::to_string(value.f_bsize)+" available_blocks="+std::to_string(value.f_bavail);
            ok=split_report_line(line.c_str())&&split_context(3)&&split_headroom();
        }
    }
    split_report_line(ok?"END success=1 CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0":
                         "END success=0 CPU_only=1 GPU_calls=0 title_launches=0 source_writes=0");
    return split_close_journal()?(ok?0:3):4;
}
