// SPDX-License-Identifier: MIT
#include "chat_prompt.h"
#include "bounded_demo.h"
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    std::ifstream source_file(argv[1]),manifest_file(argv[2]);
    const std::string source((std::istreambuf_iterator<char>(source_file)),{});
    const auto manifest=nlohmann::json::parse(manifest_file);
    auto rows=nlohmann::json::array({
        {{"name","arithmetic_control"},{"rendered",qwen_app::render_first_generation_prompt(source)}},
        {{"name","counting_control"},{"rendered",qwen_app::render_bounded_user_prompt(source,qwen_app::demo_prompt)}}});
    for(const auto &row:manifest.at("requests"))
        rows.push_back({{"name",row.at("name")},{"rendered",qwen_app::render_bounded_user_prompt(source,row.at("prompt"))}});
    std::cout<<rows.dump()<<std::endl;
}
