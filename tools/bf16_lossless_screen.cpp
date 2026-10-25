// SPDX-License-Identifier: MIT
// Manual bit-exact codec screening; never executes a model or contacts a console.
#include "bf16_lossless.h"
#include "bf16_decode_queue.h"
#include "lz4hc.h"
#include <zstd.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Bytes=std::vector<unsigned char>;
using Json=nlohmann::json;
using Clock=std::chrono::steady_clock;
static void require(bool x,const char *message){if(!x)throw std::runtime_error(message);}
struct Variant {const char *name;bool exponent,hc,zstd;unsigned shards;};
static const Variant variants[]={
    {"raw_lz4",false,false,false,1},{"raw_lz4hc9",false,true,false,1},
    {"exp_lz4",true,false,false,1},{"exp_lz4hc9",true,true,false,1},
    {"exp4_lz4hc9",true,true,false,4},{"exp_zstd1_host_only",true,false,true,1}};
static Bytes encode(const Bytes &raw,const Variant &v) {
    require(!raw.empty()&&!(raw.size()%8)&&raw.size()<=QWEN_BF16_MATRIX_MAX,"Invalid original matrix size");
    const size_t count=raw.size()/2,table=32+12*v.shards;
    Bytes sm(count),exponents(count);qwen_bf16_split(raw.data(),count,sm.data(),exponents.data());
    const auto &plain=v.exponent?exponents:raw;Bytes output(table+(v.exponent?count:0));
    memcpy(output.data(),"QBF16E01",8);qwen_codec_put32(output.data()+8,(uint32_t)raw.size());
    qwen_codec_put32(output.data()+12,v.zstd?3u:v.exponent?QWEN_BF16_CODEC_EXPONENT:QWEN_BF16_CODEC_RAW);
    qwen_codec_put32(output.data()+16,v.shards);qwen_codec_put32(output.data()+24,v.exponent?(uint32_t)count:0u);
    if(v.exponent)memcpy(output.data()+table,sm.data(),count);
    for(unsigned i=0;i<v.shards;++i) {
        const size_t n=plain.size()/v.shards;Bytes block(v.zstd?ZSTD_compressBound(n):(size_t)LZ4_compressBound((int)n));
        size_t written=0;
        if(v.zstd){written=ZSTD_compress(block.data(),block.size(),plain.data()+i*n,n,1);require(!ZSTD_isError(written),"Zstd encode failed");}
        else {const int result=v.hc?LZ4_compress_HC((const char *)plain.data()+i*n,(char *)block.data(),(int)n,(int)block.size(),9):
            LZ4_compress_default((const char *)plain.data()+i*n,(char *)block.data(),(int)n,(int)block.size());
            require(result>0,"LZ4 encode failed");written=(size_t)result;}
        const size_t entry=32+12*i;qwen_codec_put32(output.data()+entry,(uint32_t)output.size());
        qwen_codec_put32(output.data()+entry+4,(uint32_t)written);qwen_codec_put32(output.data()+entry+8,(uint32_t)n);
        output.insert(output.end(),block.begin(),block.begin()+written);
    }
    qwen_codec_put32(output.data()+20,(uint32_t)output.size());return output;
}
static bool decode(const Bytes &encoded,Bytes &output,Bytes &scratch,bool host_zstd) {
    if(!host_zstd)return qwen_bf16_decode(encoded.data(),encoded.size(),output.data(),output.size(),scratch.data(),scratch.size())!=0;
    // Host-only comparison. This codec is deliberately rejected by the native parser.
    const size_t n=output.size()/2,offset=qwen_codec_u32(encoded.data()+32),packed=qwen_codec_u32(encoded.data()+36);
    const auto got=ZSTD_decompress(scratch.data(),n,encoded.data()+offset,packed);
    if(ZSTD_isError(got)||got!=n)return false;qwen_bf16_join(encoded.data()+44,scratch.data(),n,output.data());return true;
}
static Bytes load(const std::string &path) {
    std::ifstream f(path,std::ios::binary);require(bool(f),"Original matrix is missing");
    f.seekg(0,std::ios::end);const auto n=f.tellg();require(n>0&&n<=QWEN_BF16_MATRIX_MAX,"Original sample exceeds matrix bound");f.seekg(0);
    Bytes result((size_t)n);require(bool(f.read((char *)result.data(),n))&&f.peek()==std::char_traits<char>::eof(),"Original sample changed");return result;
}
static void save(const std::string &path,const Bytes &data) {
    std::ifstream existing(path,std::ios::binary);require(!existing,"A codec fixture already exists");
    std::ofstream f(path,std::ios::binary);require(bool(f.write((const char *)data.data(),data.size())),"Fixture write failed");
}
static void self_test() {
    Bytes all(131072);for(unsigned i=0;i<65536;++i){all[2*i]=(unsigned char)i;all[2*i+1]=(unsigned char)(i>>8);}
    unsigned checks=0;
    for(const auto &v:variants) {
        auto encoded=encode(all,v);Bytes output(all.size()),scratch(all.size()/2);
        require(decode(encoded,output,scratch,v.zstd)&&output==all,"Exhaustive BF16 roundtrip failed");++checks;
        if(v.zstd){require(!qwen_bf16_decode(encoded.data(),encoded.size(),output.data(),output.size(),scratch.data(),scratch.size()),"Native parser admitted unsupported codec");++checks;continue;}
        Bytes guarded(all.size()+32,0xa5);auto *target=guarded.data()+16;
        require(qwen_bf16_decode(encoded.data(),encoded.size(),target,all.size(),scratch.data(),scratch.size()),"Guarded decode failed");
        require(std::equal(guarded.begin(),guarded.begin()+16,Bytes(16,0xa5).begin())&&
            std::equal(guarded.end()-16,guarded.end(),Bytes(16,0xa5).begin()),"Output canary changed");++checks;
        for(size_t cut=0;cut<44;++cut){require(!qwen_bf16_decode(encoded.data(),cut,target,all.size(),scratch.data(),scratch.size()),"Truncated header admitted");++checks;}
        for(const auto &change:std::vector<std::pair<size_t,uint32_t>>{{8,1},{8,QWEN_BF16_MATRIX_MAX+2},{12,99},{16,3},{20,1},{24,1},{28,1},{32,UINT32_MAX},{36,UINT32_MAX},{40,1}}) {
            Bytes bad=encoded;qwen_codec_put32(bad.data()+change.first,change.second);
            require(!qwen_bf16_decode(bad.data(),bad.size(),target,all.size(),scratch.data(),scratch.size()),"Malformed bounds admitted");++checks;
        }
        require(!qwen_bf16_decode(encoded.data(),encoded.size()-1,target,all.size(),scratch.data(),scratch.size()),"Truncated payload admitted");++checks;
        require(!qwen_bf16_decode(encoded.data(),encoded.size(),target,all.size()-1,scratch.data(),scratch.size()),"Short destination admitted");++checks;
        require(!qwen_bf16_decode(encoded.data(),encoded.size(),encoded.data(),encoded.size(),scratch.data(),scratch.size()),"Aliased source admitted");++checks;
        if(v.exponent){require(!qwen_bf16_decode(encoded.data(),encoded.size(),target,all.size(),target,all.size()),"Aliased scratch admitted");++checks;}
    }
    Bytes maximum(QWEN_BF16_MATRIX_MAX);uint32_t random=1;
    for(auto &x:maximum){random^=random<<13;random^=random>>17;random^=random<<5;x=(unsigned char)random;}
    for(const auto &v:variants)if(!v.zstd) {
        auto encoded=encode(maximum,v);Bytes output(maximum.size()),scratch(maximum.size()/2);
        require(decode(encoded,output,scratch,false)&&output==maximum,"Maximum matrix roundtrip failed");
        const size_t working=encoded.size()+output.size()+(v.exponent?scratch.size():0);
        require(working+(3*16384)<(8u<<20),"Native aligned workspace exceeds 8 MiB");++checks;
    }
    {
        const auto &v=variants[4];auto encoded=encode(maximum,v);
        Bytes output(maximum.size()),scratch(maximum.size()/2);qwen_bf16_decode_plan plan;
        require(qwen_bf16_prepare(encoded.data(),encoded.size(),output.data(),output.size(),scratch.data(),scratch.size(),&plan),"Parallel plan refused");
        qwen_app::BF16DecodeQueue queue;queue.start();
        for(unsigned i=0;i<32;++i){require(queue.decode(plan)&&output==maximum,"Parallel original matrix reconstruction differs");++checks;}
        queue.stop_completed();
        const auto offset=qwen_codec_u32(encoded.data()+32+12*3),packed=qwen_codec_u32(encoded.data()+36+12*3);
        memset(encoded.data()+offset,0xff,packed);
        qwen_app::BF16DecodeQueue invalid;invalid.start();require(!invalid.decode(plan),"Corrupt exponent shard admitted");
        invalid.stop_completed();++checks;
    }
    std::cout<<Json{{"all_65536_BF16_patterns_preserved",true},{"bounded_controls",checks},
        {"maximum_matrix_roundtrips",5},{"parallel_repeated_roundtrips",32},
        {"completed_bad_shard_refused_and_workers_joined",true},{"aligned_workspace_below_8MiB",true}}.dump()<<'\n';
}
int main(int argc,char **argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--self-test"){self_test();return 0;}
        require(argc==3,"Usage: bf16_lossless_screen INPUT.raw OUTPUT_PREFIX, or --self-test");
        const auto raw=load(argv[1]);Json rows=Json::array();
        for(const auto &v:variants) {
            const auto encoded=encode(raw,v);Bytes output(raw.size()),scratch(raw.size()/2);std::vector<uint64_t> times;
            for(unsigned i=0;i<33;++i) {
                const auto start=Clock::now();const bool ok=decode(encoded,output,scratch,v.zstd);
                const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
                require(ok&&output==raw,"Original matrix reconstruction differs");if(i>=2)times.push_back((uint64_t)ns);
            }
            std::sort(times.begin(),times.end());
            const std::string file=std::string(argv[2])+"."+v.name+".eb16";save(file,encoded);
            rows.push_back(Json{{"variant",v.name},{"original_bytes",raw.size()},{"encoded_bytes",encoded.size()},
                {"encoded_file",file},{"shards",v.shards},{"native_compatible",!v.zstd},
                {"host_restore_median_ns",times[times.size()/2]},{"host_restore_p95_ns",times[29]},
                {"workspace_bytes",encoded.size()+output.size()+(v.exponent?scratch.size():0)},
                {"every_restored_byte_exact",true}});
        }
        std::cout<<Json{{"samples",rows},{"native_speed_qualified",false},{"host_model_inference",false}}.dump()<<'\n';
        return 0;
    }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
