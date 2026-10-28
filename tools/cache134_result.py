#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the completed 134-slot geometry contract without editing legacy validators."""
import inspect,linecache


def compiled_function(text,env,label,name):
    filename=__file__+'#'+label
    linecache.cache[filename]=(len(text),None,text.splitlines(keepends=True),filename)
    namespace=dict(env);exec(compile(text,filename,'exec'),namespace);return namespace[name]


def install_geometry():
    import cache128_result,expert_route_result,padded_bank_result
    text=inspect.getsource(padded_bank_result.validate_layout_report).replace('expected_slots in (53,128)','expected_slots in (53,128,134)').replace('if expected_slots==128:','if expected_slots in(128,134):')
    layout=compiled_function(text,padded_bank_result.__dict__,'complete-134-layout','validate_layout_report')
    padded_bank_result.validate_layout_report=layout;cache128_result.validate_layout_report=layout
    cache128_result.CACHE_BYTES=1333739520
    cache128_result.MODEL_REQUIREMENT=12042833408+1333739520-1274462208
    text=inspect.getsource(cache128_result.validate_binding).replace('ps5-qwen-cache128-model-binding-v1','ps5-qwen-cache134-model-binding-v1').replace('active_slots=128,physical_planes=129','active_slots=134,physical_planes=135')
    cache128_result.validate_binding=compiled_function(text,cache128_result.__dict__,'134-cache-binding','validate_binding')
    text=inspect.getsource(cache128_result.validate_model).replace('expected_slots=128','expected_slots=134').replace('active_slots=128,physical_planes=129','active_slots=134,physical_planes=135')
    cache128_result.validate_model=compiled_function(text,cache128_result.__dict__,'134-native-pool-and-model','validate_model')
    text=inspect.getsource(expert_route_result.validate_routes).replace('not in (53,128)','not in (53,128,134)').replace('expected_slots!=128','expected_slots not in(128,134)')
    expert_route_result.validate_routes=compiled_function(text,expert_route_result.__dict__,'134-route-capacity-only','validate_routes')


def install_counting(binding):
    install_geometry()
    import speculative_monitor_result as module
    text=inspect.getsource(module.checked_quality).replace('active_cache_slots=128','active_cache_slots=134')
    module.checked_quality=compiled_function(text,module.__dict__,'134-counting-cross-capacity-F32','checked_quality')
    text=inspect.getsource(module.install).replace('expected_slots=128','expected_slots=134').replace('active_slots=128,physical_planes=129,cache_request_bytes=1274462208','active_slots=134,physical_planes=135,cache_request_bytes=1333739520')
    return compiled_function(text,module.__dict__,'134-counting-original-state-and-source-checks','install')(binding)


def install_adaptive(binding):
    install_geometry()
    from adaptive_monitor_result import install
    return install(binding)
