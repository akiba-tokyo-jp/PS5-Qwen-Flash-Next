// SPDX-License-Identifier: MIT
#include "model_integrity.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
int main(int argc,char ** argv){
    try{
        if(argc<3||argc>4)throw std::invalid_argument("Supply fixture path, digest and optional mutation flag");
        std::ifstream input(argv[1],std::ios::binary|std::ios::ate);
        const auto bytes=static_cast<std::uint64_t>(input.tellg());input.close();
        std::uint64_t previous=0;unsigned samples=0;
        qwen_app::verify_model_file(argv[1],bytes,argv[2],[&](std::uint64_t count){
            if(count<previous||count>bytes)throw std::logic_error("Integrity progress escaped its byte range");
            previous=count;++samples;
            if(argc==4&&samples==1){std::ofstream changed(argv[1],std::ios::binary|std::ios::app);changed<<'x';}
        });
        if(previous!=bytes||samples<2)throw std::logic_error("Integrity completion was not observed");
        std::cout<<"Streaming native integrity matched the supplied digest; no model or GPU execution\n";
    }catch(const std::exception & error){std::cerr<<error.what()<<'\n';return 1;}
}
