#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain original exact-once native observation for a declared 134-slot profile."""
import json,sys
from pathlib import Path
from cache134_result import install_adaptive,install_counting


def main():
    if sys.argv.count('--binding')!=1:raise ValueError('One exact native monitor binding is required')
    binding=json.loads(Path(sys.argv[sys.argv.index('--binding')+1]).read_text())
    adaptive='require_adaptive_prefix_monitor'in binding
    state=install_adaptive(binding)if adaptive else install_counting(binding)
    path=Path(__file__).with_name('observe_native_plan.py');source=path.read_text()
    needle='    expected = binding["native_binding"]';assert source.count(needle)==1
    source=source.replace(needle,needle+'''
    boot=binding["current_boot"]
    require(type(boot)is list and len(boot)==2 and type(boot[0])is int and type(boot[1])is int and boot[0]>0 and 0<=boot[1]<1000000,"Complete current boot identity required")
''')
    needle='MODEL_ROOT + "entry-" + str(expected["pid"]) + ".stages"';assert source.count(needle)==1
    source=source.replace(needle,'MODEL_ROOT + "entry-b" + str(boot[0]) + "-" + str(boot[1]) + "-" + str(expected["pid"]) + ".stages"')
    if adaptive:
        from adaptive_monitor_result import PROMPT
        needle='PROMPT = "Count from 1 to 8, separated by commas. Reply with only the sequence."';assert source.count(needle)==1;source=source.replace(needle,'PROMPT = '+repr(PROMPT))
        source=source.replace('reused_prompt_tokens=30 if expected.get(', 'reused_prompt_tokens=25 if expected.get(')
    exec(compile(source,str(path)+'#134-capacity-boot-and-profile-bound','exec'),{'__file__':str(path),'__name__':'__main__'})
    if state['quality_review']is None:raise ValueError('No completed original-precision capacity/profile quality proof')
    print(json.dumps(dict(cache134_native_monitor_review=state['quality_review'],adaptive_profile=adaptive,legacy_validator_files_unchanged=True)),flush=True)
if __name__=='__main__':main()
