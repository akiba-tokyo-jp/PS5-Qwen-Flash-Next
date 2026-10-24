// SPDX-License-Identifier: MIT
#include "model_identity_namespace.h"
#include <iostream>
using namespace qwen_app;
int main() {
    const SourceIdentity directory{10,100,0040755,0,0,65536,1000,0,1000,0};
    const SourceIdentity receipt{10,101,0100644,0,0,95068,999,0,999,0};
    auto mounted_directory=directory, mounted_receipt=receipt;
    mounted_directory[0]=mounted_receipt[0]=20;
    auto reject = [&](const SourceIdentity & d, const SourceIdentity & r, bool allow) {
        try { ModelIdentityNamespace value(directory,d,receipt,r,allow); }
        catch (const std::runtime_error &) { return; }
        throw std::runtime_error("An invalid model namespace was accepted");
    };
    ModelIdentityNamespace exact(directory,directory,receipt,receipt,false);
    if (!exact.matches(receipt,receipt)) return 1;
    reject(mounted_directory,mounted_receipt,false);
    ModelIdentityNamespace mounted(directory,mounted_directory,receipt,mounted_receipt,true);
    if (!mounted.matches(mounted_receipt,receipt)) return 1;
    for (std::size_t i=0;i<10;++i) {
        auto changed=mounted_receipt;++changed[i];
        if (mounted.matches(changed,receipt)) return 1;
        reject(mounted_directory,changed,true);
    }
    auto wrong_inode=mounted_directory;++wrong_inode[1];reject(wrong_inode,mounted_receipt,true);
    auto missing=mounted_directory;missing[0]=0;reject(missing,mounted_receipt,true);
    std::cout << "Exact namespace, explicit device-only translation and all ten identity mismatch checks passed\n";
}
