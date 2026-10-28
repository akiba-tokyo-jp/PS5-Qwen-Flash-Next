#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the original finite API observer with the current boot-qualified journal."""
from pathlib import Path


def main():
    path=Path(__file__).with_name('observe_native_plan.py')
    source=path.read_text()
    needle='    expected = binding["native_binding"]'
    assert source.count(needle)==1
    source=source.replace(needle,needle+'''
    boot=binding["current_boot"]
    require(type(boot)is list and len(boot)==2 and type(boot[0])is int and type(boot[1])is int and
        boot[0]>0 and 0<=boot[1]<1000000,"Complete current boot identity required")
''')
    needle='MODEL_ROOT + "entry-" + str(expected["pid"]) + ".stages"'
    assert source.count(needle)==1
    source=source.replace(needle,'MODEL_ROOT + "entry-b" + str(boot[0]) + "-" + str(boot[1]) + "-" + str(expected["pid"]) + ".stages"')
    exec(compile(source,str(path)+'#boot-bound','exec'),{'__file__':str(path),'__name__':'__main__'})


if __name__=='__main__':main()
