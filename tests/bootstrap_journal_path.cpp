// SPDX-License-Identifier: MIT
#include "bootstrap_journal_path.h"
#include <array>
#include <iostream>
#include <stdexcept>
int main() {
    using qwen_app::bootstrap_journal_path;
    const auto require=[](bool v){if(!v)throw std::runtime_error("Bootstrap journal path control failed");};
    char a[160]{},b[160]{};
    require(bootstrap_journal_path(a,sizeof(a),1793024098,650611,2247,".stages"));
    require(!std::strcmp(a,"/app0/qwen-runtime/entry-b1793024098-650611-2247.stages"));
    require(bootstrap_journal_path(b,sizeof(b),1792924098,650611,2247,".stages"));require(std::strcmp(a,b)!=0);
    require(bootstrap_journal_path(b,sizeof(b),1793024098,650611,2248,".stages"));require(std::strcmp(a,b)!=0);
    for(const char *suffix:{".stages",".fatal",".private.log"})
        require(bootstrap_journal_path(b,sizeof(b),1,0,1,suffix));
    for(unsigned size=0;size<=std::strlen(a);++size) {
        std::array<char,160> out;out.fill('x');
        require(!bootstrap_journal_path(out.data(),size,1793024098,650611,2247,".stages"));
        for(unsigned i=size;i<out.size();++i)require(out[i]=='x');
    }
    require(!bootstrap_journal_path(a,sizeof(a),0,0,1,".stages"));
    require(!bootstrap_journal_path(a,sizeof(a),1,1000000,1,".stages"));
    require(!bootstrap_journal_path(a,sizeof(a),1,0,0,".stages"));
    require(!bootstrap_journal_path(a,sizeof(a),1,0,1,"../stages"));
    std::cout<<"Boot/PID namespaces, exact suffixes and bounded writes passed\n";
}
