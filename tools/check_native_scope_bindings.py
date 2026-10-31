#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Evaluate literal native policy equalities on the host before any launch."""
import argparse,json,os,re,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('entry','policy','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();text=a.entry.read_text();a.out.mkdir(parents=True,exist_ok=False)
    definitions=list(re.finditer(r'const Json (\w+)\s*=\s*(.*?);',text,re.S))
    quoted=r'"(?:\\.|[^"\\])*"'
    raw=r'R"\w*\(.*?\)\w*"'
    lhs=r'policy(?:\.at\('+quoted+r'\))+'
    rhs=r'(Json::parse\((?:'+quoted+'|'+raw+r')\)|\w+)'
    checks=[]
    for match in re.finditer(r'if\(('+lhs+r')\s*!=\s*'+rhs+r'\)',text,re.S):
        target,expected=match.group(1),match.group(2)
        local=[d for d in definitions if d.group(1)==expected and d.end()<match.start()]
        if local:expected=local[-1].group(2)
        elif not expected.startswith('Json::parse('):continue
        checks.append((target,expected))
    require(len(checks)>=10,'Expected literal native scope checks were not extracted')
    source='#include <nlohmann/json.hpp>\n#include <fstream>\n#include <iostream>\nusing Json=nlohmann::json;\nint main(int argc,char**argv){if(argc!=2)return 2;std::ifstream f(argv[1]);Json policy;f>>policy;unsigned bad=0;\n'
    for i,(target,expected)in enumerate(checks):
        source+='try{const Json expected='+expected+';if('+target+'!=expected){++bad;std::cerr<<"Scope mismatch '+str(i)+'"<<std::endl;}}catch(...){++bad;std::cerr<<"Scope unavailable '+str(i)+'"<<std::endl;}\n'
    source+='return bad?1:0;}\n'
    path=a.out/'scopes.private.cpp';path.write_text(source,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'scopes.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O1',
        '-I'+str(a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor'),str(path),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    run=subprocess.run(command,capture_output=True,timeout=120,env=env)
    (a.out/'build.private.log').write_bytes(run.stdout+run.stderr)
    require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
    run=subprocess.run([str(exe),str(a.policy)],capture_output=True,timeout=30,env=env)
    (a.out/'check.private.log').write_bytes(run.stdout+run.stderr)
    write_json(a.out/'result.private.json',dict(completed=True,passed=run.returncode==0,
        literal_scope_checks=len(checks),targets=[target for target,_ in checks],
        entry=record(a.entry),policy=record(a.policy),PS5_operations=0))
    require(run.returncode==0,run.stderr.decode(errors='replace'))
    print(json.dumps(dict(native_literal_scope_checks=len(checks),passed=True,PS5_operations=0)))

if __name__=='__main__':main()
