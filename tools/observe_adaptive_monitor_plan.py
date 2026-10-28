#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the original exact-once observer with one explicit adaptive profile."""
import json,sys
from pathlib import Path
from adaptive_monitor_result import install,PROMPT


def main():
    if sys.argv.count('--binding')!=1:raise ValueError('One frozen adaptive observer binding is required')
    binding=Path(sys.argv[sys.argv.index('--binding')+1]);state=install(json.loads(binding.read_text()))
    path=Path(__file__).with_name('observe_native_plan.py');source=path.read_text()
    needle='    expected = binding["native_binding"]';assert source.count(needle)==1
    source=source.replace(needle,needle+'''
    boot=binding["current_boot"]
    require(type(boot)is list and len(boot)==2 and type(boot[0])is int and type(boot[1])is int and boot[0]>0 and 0<=boot[1]<1000000,"Exact current boot required")
''')
    needle='MODEL_ROOT + "entry-" + str(expected["pid"]) + ".stages"';assert source.count(needle)==1
    source=source.replace(needle,'MODEL_ROOT + "entry-b" + str(boot[0]) + "-" + str(boot[1]) + "-" + str(expected["pid"]) + ".stages"')
    needle='PROMPT = "Count from 1 to 8, separated by commas. Reply with only the sequence."';assert source.count(needle)==1;source=source.replace(needle,'PROMPT = '+repr(PROMPT))
    source=source.replace('reused_prompt_tokens=30 if expected.get(', 'reused_prompt_tokens=25 if expected.get(')
    exec(compile(source,str(path)+'#boot-bound-explicit-adaptive-profile','exec'),{'__file__':str(path),'__name__':'__main__'})
    if state['quality_review']is None:raise ValueError('No completed adaptive native quality proof')
    print(json.dumps(dict(adaptive_native_monitor_review=state['quality_review'],legacy_observers_unchanged=True)),flush=True)
if __name__=='__main__':main()
