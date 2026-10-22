// SPDX-License-Identifier: MIT
#include "model_integrity.h"
#include <chrono>
#include <fstream>
#include <stdexcept>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
void verify_model_file(const std::string & path,std::uint64_t bytes,const std::string & expected,
                       const std::function<void(std::uint64_t)> & progress,unsigned timeout_seconds) {
    if(!bytes||bytes>(512ull<<30)||expected.size()!=64||expected.find_first_not_of("0123456789abcdef")!=std::string::npos||
       !timeout_seconds||timeout_seconds>86400)
        throw std::invalid_argument("Invalid original-model integrity contract");
    std::ifstream file(path,std::ios::binary|std::ios::ate);
    if(!file||file.tellg()<0||static_cast<std::uint64_t>(file.tellg())!=bytes)
        throw std::runtime_error("Transferred model file size is not admitted");
    file.seekg(0);sha256_t hash;sha256_init(&hash);
    std::vector<unsigned char> buffer(1u<<20);std::uint64_t read=0,reported=0;
    const auto started=std::chrono::steady_clock::now();
    if(progress)progress(0);
    while(file) {
        if(std::chrono::steady_clock::now()-started>std::chrono::seconds(timeout_seconds))
            throw std::runtime_error("Original-model integrity deadline expired");
        file.read(reinterpret_cast<char *>(buffer.data()),buffer.size());const auto got=file.gcount();
        if(got<0||static_cast<std::uint64_t>(got)>bytes-read)
            throw std::runtime_error("Transferred model changed during integrity verification");
        if(got) {sha256_update(&hash,buffer.data(),static_cast<std::size_t>(got));read+=got;}
        if(progress&&read-reported>=(64u<<20)) {reported=read;progress(read);}
    }
    if(!file.eof()||read!=bytes) throw std::runtime_error("Original-model integrity read did not complete");
    unsigned char digest[32];sha256_final(&hash,digest);std::string actual;
    for(auto value:digest){actual.push_back("0123456789abcdef"[value>>4]);actual.push_back("0123456789abcdef"[value&15]);}
    if(actual!=expected)throw std::runtime_error("Transferred original-model SHA256 does not match");
    if(progress)progress(read);
}
}
