// SPDX-License-Identifier: MIT
// Fixture file bytes are host-only test data, never learned host inference.
#include "shader_file_fixture.h"
#include "shader_file_native.h"
#include "shader_assets_bridge.h"
#include "system_memory.h"
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <vector>
namespace {
class FixtureOps final:public qwen_app::ShaderFileOps {
public:
    std::vector<unsigned char> bytes;
    std::string mode;
    std::uint64_t version=1,clock=1000,delay=100,calls=0;
    bool opened=false,pressure=false,quarantine_during_read=false;
    std::array<std::uint64_t,10> identity()override{return {1,version,0100600,1,1,bytes.size(),11,0,11,0};}
    void system_headroom(bool startup)override {
        if(pressure||mode=="file_startup_guard")throw std::runtime_error("Synthetic external-file memory pressure");
        if(startup)(void)qwen_app::admit_native_system_memory();
        else(void)qwen_app::qualified_system_headroom(qwen_app::observe_native_system_memory());
    }
    std::uint64_t now_ns()override{return clock;}
    void before_read()override{}
    std::int64_t read_at(void*at,std::size_t count,std::uint64_t offset)override {
        ++calls;
        if(mode=="file_pending")throw std::runtime_error("Synthetic unknown external read");
        if(!at||count%16384||offset%16384||offset>=bytes.size())throw std::runtime_error("Actual external file read recipe changed");
        const auto logical=std::min<std::uint64_t>(count,bytes.size()-offset);
        std::memcpy(at,bytes.data()+offset,logical);clock+=delay;
        if(quarantine_during_read){try{qwen_app_complete_shader_code(reinterpret_cast<void*>(std::uintptr_t(1)));}catch(...){}}
        if(mode=="file_identity_during_read")++version;
        return static_cast<std::int64_t>(logical)+(mode=="file_short"?-4:mode=="file_oversized"?1:0);
    }
    void read_returned()override{}
};
FixtureOps fixture;
}
void configure_shader_file_fixture(const std::string&path,const std::string&mode) {
    if(!fixture.bytes.empty()||fixture.opened)throw std::runtime_error("The host shader file fixture may only configure once");
    std::ifstream file(path,std::ios::binary);
    if(!file)throw std::runtime_error("The exact host shader pool fixture is unavailable");
    fixture.bytes.assign(std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>());fixture.mode=mode;
    if(fixture.bytes.empty())throw std::runtime_error("The complete shader pool fixture is required");
    if(mode=="file_corrupt")fixture.bytes[0]^=1;
    if(mode=="file_timeout")fixture.delay=31000000000ull;
}
void change_shader_file_fixture_identity(){++fixture.version;}
void corrupt_shader_file_fixture_byte(std::uint64_t at){if(at>=fixture.bytes.size())throw std::runtime_error("Invalid fixture corruption offset");fixture.bytes[at]^=1;}
void delay_shader_file_fixture_read(std::uint64_t ns){fixture.delay=ns;}
void pressure_shader_file_fixture(){fixture.pressure=true;}
void quarantine_shader_file_fixture_during_read(){fixture.quarantine_during_read=true;}
std::uint64_t shader_file_fixture_calls(){return fixture.calls;}
namespace qwen_app {
ShaderFileOps &open_native_shader_file(const std::string &) {
    if(fixture.opened||fixture.bytes.empty())throw std::runtime_error("Unexpected host fixture descriptor open or retry");
    fixture.opened=true;return fixture;
}
}
