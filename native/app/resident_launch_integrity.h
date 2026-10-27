// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include "resident_shader_integrity.h"
namespace qwen_app {
using ResidentFileIdentity=std::array<std::uint64_t,10>;
inline ResidentFileIdentity resident_file_identity(const struct stat &s) {
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),
        std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
inline void validate_resident_launch_receipt(const nlohmann::json &scope,const nlohmann::json &receipt,
        const std::string &run,std::uint64_t bytes,const std::string &sha,const ResidentFileIdentity &identity,
        const nlohmann::json *expected_shader=nullptr) {
    using J=nlohmann::json;
    const auto nonce=scope.at("nonce").get<std::string>();
    if(!scope.at("maximum_receipt_bytes").is_number_integer()||!receipt.at("SELF_bytes").is_number_integer()||
       !receipt.at("identity").is_array()||receipt.at("identity").size()!=10)
        throw std::runtime_error("Typed integrity receipt geometry required");
    for(const auto &v:receipt.at("identity"))if(!v.is_number_integer())throw std::runtime_error("Typed native file identity required");
    const auto path="/app0/qwen-runtime/resident-launch-"+run+".json";
    J expected_scope={{"schema","ps5-qwen-same-launch-SELF-integrity-scope-v1"},{"run_id",run},{"nonce",nonce},
           {"receipt_path",path},{"maximum_receipt_bytes",2048},{"exclusive_writer_lease_required",true},
           {"native_whole_SHA256_identity_EOF_before_ordinary_launch_required",true},
           {"root_owned_readonly_receipt_required",true},{"current_inode_identity_required",true},
           {"device_ID_scope","verified_title_nullfs_namespace"}};
    if(expected_shader)expected_scope["external_shader_at_ordinary_launch"]=true;
    if(run.size()!=32||run.find_first_not_of("0123456789abcdef")!=std::string::npos||
       nonce.size()!=32||nonce.find_first_not_of("0123456789abcdef")!=std::string::npos||
       !bytes||sha.size()!=64||sha.find_first_not_of("0123456789abcdef")!=std::string::npos||scope!=expected_scope)
        throw std::runtime_error("Exact same-launch integrity scope required");
    // Case 3490 matched all nine inode/owner/size/time fields and differed
    // only in st_dev across the root mount and native sandbox namespaces.
    // Verify the application-local filesystem separately below; keep both
    // namespace IDs in their original records rather than comparing them.
    auto translated_identity=identity;
    translated_identity[0]=receipt.at("identity")[0].get<std::uint64_t>();
    if(!identity[0]||!translated_identity[0])throw std::runtime_error("Nonzero namespace filesystem identities required");
    J expected_receipt={{"schema","ps5-qwen-same-launch-SELF-integrity-v1"},{"run_id",run},{"nonce",nonce},
        {"SELF_bytes",bytes},{"SELF_sha256",sha},{"full_Direct_SHA256_identity_EOF_passed",true},{"identity",translated_identity}};
    if(expected_shader) {
        (void)validate_resident_shader_receipt(receipt.at("external_shader"),*expected_shader);
        expected_receipt["external_shader"]=receipt.at("external_shader");
    }
    if(receipt!=expected_receipt) {
        unsigned mask=0;for(unsigned i=0;i<identity.size();++i)if(receipt.at("identity")[i]!=identity[i])mask|=1u<<i;
        throw std::runtime_error("Native full integrity receipt or current SELF identity differs: identity_mask="+std::to_string(mask));
    }
}
inline nlohmann::json verify_resident_launch_integrity(const nlohmann::json &scope,const std::string &run,
        std::uint64_t bytes,const std::string &sha,const nlohmann::json *expected_shader=nullptr) {
    const auto path="/app0/qwen-runtime/resident-launch-"+run+".json";
    struct stat before{},after{},self{},current{};
    // Native title lstat returned EPERM in case 3474. Use the already
    // qualified descriptor API and O_NOFOLLOW for both path observations.
    int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW);
    if(fd<0)throw std::runtime_error("Integrity receipt descriptor open failed: errno="+std::to_string(errno));
    const auto stat_rc=fstat(fd,&before);const auto stat_errno=errno;
    if(stat_rc||!S_ISREG(before.st_mode)||before.st_uid!=0||
       (before.st_mode&0777)!=0444||before.st_size<=0||before.st_size>2048) {
        (void)close(fd);
        throw std::runtime_error("Fresh root-owned readonly integrity receipt required: rc="+std::to_string(stat_rc)+
            " errno="+std::to_string(stat_errno)+" uid="+std::to_string(before.st_uid)+
            " mode="+std::to_string(before.st_mode)+" bytes="+std::to_string(before.st_size)+" path="+path);
    }
    std::array<char,2049> raw{};std::size_t used=0;bool ok=true;
    while(ok&&used<std::size_t(before.st_size)){const auto n=read(fd,raw.data()+used,std::size_t(before.st_size)-used);if(n<=0)ok=false;else used+=n;}
    char eof=0;if(ok)ok=read(fd,&eof,1)==0&&!fstat(fd,&after)&&resident_file_identity(after)==resident_file_identity(before);
    if(close(fd))ok=false;
    int named=open(path.c_str(),O_RDONLY|O_NOFOLLOW);
    if(named<0)ok=false;
    else {if(fstat(named,&after)||resident_file_identity(after)!=resident_file_identity(before))ok=false;if(close(named))ok=false;}
    if(!ok)
        throw std::runtime_error("Complete integrity receipt identity or EOF failed");
    int executable=open("/app0/eboot.bin",O_RDONLY|O_NOFOLLOW);
    if(executable<0)throw std::runtime_error("Current native SELF descriptor unavailable");
    ok=!fstat(executable,&self)&&S_ISREG(self.st_mode)&&self.st_ino&&self.st_size==(off_t)bytes;
    if(self.st_dev!=before.st_dev)ok=false;
    if(close(executable))ok=false;
    named=open("/app0/eboot.bin",O_RDONLY|O_NOFOLLOW);
    if(named<0)ok=false;
    else {if(fstat(named,&current)||resident_file_identity(self)!=resident_file_identity(current))ok=false;if(close(named))ok=false;}
    if(!ok)throw std::runtime_error("Current SELF stable descriptor identity failed");
    auto receipt=nlohmann::json::parse(raw.data(),raw.data()+used);
    validate_resident_launch_receipt(scope,receipt,run,bytes,sha,resident_file_identity(self),expected_shader);
    return receipt;
}
}
