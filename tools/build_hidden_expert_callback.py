#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the real callback from its isolated header view and report actual reads."""
from pathlib import Path
from build_speculative_batch_probe import once


def observed_entry(text):
    marker='            const auto shadow_report=qwen_app::finish_router_shadow_request(context);'
    return once(text,marker,'''            auto shadow_report=qwen_app::finish_router_shadow_request(context);
            qwen_predictive_cache_stats actual_prediction{};qwen_app_predictive_cache_counters(&actual_prediction);
            shadow_report["speculative_reads"]=3*actual_prediction.loads;
            shadow_report["prediction"]=Json{{"proposals",actual_prediction.proposals},{"loads",actual_prediction.loads},
                {"useful",actual_prediction.useful},{"unused",actual_prediction.unused},{"ineligible",actual_prediction.ineligible},
                {"logical_bytes",actual_prediction.logical_bytes}};
            if(kind=="hidden"&&(actual_prediction.proposals!=18||!actual_prediction.loads||
               actual_prediction.useful+actual_prediction.unused!=actual_prediction.loads))
                throw std::runtime_error("The actual one-Expert hidden callback must exercise and complete real reads");
            if(kind!="hidden"&&(actual_prediction.proposals||actual_prediction.loads||actual_prediction.logical_bytes))
                throw std::runtime_error("The same-graph control cannot submit speculative reads");''')


def main():
    path=Path(__file__).with_name('build_hidden_expert_prefetch.py');text=path.read_text()
    text=once(text,"runtime=ROOT/'native/app/router_shadow_runtime.cpp'",'''runtime=a.out/'router-shadow-hidden-callback.private.cpp'
    runtime.write_bytes((ROOT/'native/app/router_shadow_runtime.cpp').read_bytes())''')
    text=once(text,'main_src.write_text(entry_source(original.read_text()),',
        'main_src.write_text(observed_entry(entry_source(original.read_text())),')
    text=once(text,'old_route_forecast_disabled=True)',
        'old_route_forecast_disabled=True,actual_hidden_callback_enabled=True)')
    text=once(text,'a.parent,Path(__file__),ROOT/',
        'a.parent,Path(__file__),Path(__file__).with_name("build_hidden_expert_prefetch.py"),ROOT/')
    exec(compile(text,str(path)+'#isolated-actual-callback','exec'),
        {'__file__':__file__,'__name__':'__main__','observed_entry':observed_entry})


if __name__=='__main__':main()
