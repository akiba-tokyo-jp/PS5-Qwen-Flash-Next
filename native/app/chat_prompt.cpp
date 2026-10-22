// SPDX-License-Identifier: MIT
#include "chat_prompt.h"
#include "first_generation.h"
#include "jinja/lexer.h"
#include "json.h"

namespace qwen_app {
std::string render_chat_prompt(const std::string & source, const jinja::program & program,
                              const nlohmann::json & messages, bool thinking) {
    using Json = nlohmann::json;
    jinja::context context(source);
    const auto variables = Json{{"messages", messages}, {"tools", Json::array()},
        {"add_generation_prompt", true}, {"enable_thinking", thinking}};
    jinja::global_from_json(context, common_json::parse(variables.dump()), true);
    jinja::runtime runtime(context);
    auto rendered = runtime.gather_string_parts(runtime.execute(program))->as_string().str();
    if (rendered.empty() || rendered.size() > (1u << 20))
        throw std::runtime_error("Rendered prompt is empty or too large");
    return rendered;
}

std::string render_first_generation_prompt(const std::string & source) {
    if (source.empty() || source.size() > (256u << 10))
        throw std::invalid_argument("The bounded original chat template is required");
    const auto program = jinja::parse_from_tokens(jinja::lexer().tokenize(source));
    return render_chat_prompt(source, program,
        nlohmann::json::array({{{"role", "user"}, {"content", first_generation_prompt}}}), false);
}
}
