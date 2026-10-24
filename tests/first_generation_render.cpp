// SPDX-License-Identifier: MIT
#include "http_app.h"
#include "first_generation.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }
int main(int argc, char ** argv) {
    try {
        check(argc == 2, "The pinned original template path is required");
        const std::string simple = "{% if enable_thinking %}invalid{% endif %}{{ messages[0].role }}:"
            "{{ messages[0].content }}{% if add_generation_prompt %}:assistant{% endif %}";
        check(qwen_app::render_first_generation_prompt(simple) ==
            std::string("user:") + qwen_app::first_generation_prompt + ":assistant", "Template variables changed");
        std::ifstream file(argv[1], std::ios::binary);
        check(bool(file), "Original template could not be read");
        const std::string source((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        const auto rendered = qwen_app::render_first_generation_prompt(source);
        check(!rendered.empty() && rendered.size() <= 16384 && rendered.find(qwen_app::first_generation_prompt) != std::string::npos,
            "Original model template did not retain the fixed request within its byte bound");
        for (const auto & bad : {std::string(), std::string(262145, 'x'), std::string("{% if")}) {
            bool rejected = false; try { qwen_app::render_first_generation_prompt(bad); }
            catch (const std::exception &) { rejected = true; }
            check(rejected, "Invalid template was admitted");
        }
        std::cout << "Actual application Jinja renderer passed, including the pinned original template ("
                  << rendered.size() << " rendered bytes); no tokenizer/model execution\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
