// SPDX-License-Identifier: MIT
// These copies stand in for the completed, synchronized Vulkan transfer call.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>
using vk_buffer=std::vector<std::uint8_t>;
#define VK_LOG_DEBUG(...) do {} while(0)
static std::size_t calls=0, fail_on=0, expected_offset=0;
static bool bounded=true;
static void check(bool value){if(!value)throw std::runtime_error("Bounded staging contract failed");}
static void transfer(std::size_t offset,std::size_t width,std::size_t spitch,std::size_t dpitch,std::size_t height){
    check(height==1&&width==spitch&&width==dpitch&&offset==expected_offset);
    if(bounded)check(width<=(64u<<20));
    ++calls;if(calls==fail_on)throw std::runtime_error("Injected transfer failure");
    expected_offset+=width;
}
static void ggml_vk_buffer_write_2d(vk_buffer & dst,std::size_t offset,const void * src,std::size_t spitch,std::size_t dpitch,std::size_t width,std::size_t height){
    transfer(offset,width,spitch,dpitch,height);check(offset+width<=dst.size());std::memcpy(dst.data()+offset,src,width);
}
static void ggml_vk_buffer_read_2d(vk_buffer & src,std::size_t offset,void * dst,std::size_t spitch,std::size_t dpitch,std::size_t width,std::size_t height){
    transfer(offset,width,spitch,dpitch,height);check(offset+width<=src.size());std::memcpy(dst,src.data()+offset,width);
}
#include "actual-staging.inc"
int main(){
    try{
        constexpr std::size_t prefix=128,bytes=(128u<<20)+128;
        vk_buffer input(bytes),device(bytes+prefix+128,0xa5),readback(bytes);
        for(std::size_t i=0;i<bytes;++i)input[i]=std::uint8_t(i*31+7);
        _putenv_s("GGML_VK_BOUNDED_STAGING","1");
        expected_offset=prefix;ggml_vk_buffer_write(device,prefix,input.data(),bytes);check(calls==3);
        check(std::equal(input.begin(),input.end(),device.begin()+prefix));
        check(device.front()==0xa5&&device.back()==0xa5);
        calls=0;expected_offset=prefix;ggml_vk_buffer_read(device,prefix,readback.data(),bytes);
        check(calls==3&&input==readback);
        calls=0;fail_on=2;expected_offset=prefix;bool failed=false;
        try{ggml_vk_buffer_write(device,prefix,input.data(),bytes);}catch(const std::runtime_error &){failed=true;}
        check(failed&&calls==2&&expected_offset==prefix+(64u<<20));
        calls=0;fail_on=0;bounded=false;expected_offset=prefix;_putenv_s("GGML_VK_BOUNDED_STAGING","0");
        ggml_vk_buffer_write(device,prefix,input.data(),bytes);check(calls==1);
        std::cout<<"Actual transfer loops preserve raw bytes, cap chunks and stop after failure; host API stubs only\n";
    }catch(const std::exception & error){std::cerr<<error.what()<<'\n';return 1;}
}
