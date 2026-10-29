#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual immutable reader derivative with fake exact-byte IO."""
import argparse,json,os,re,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from expert_q2_reader_candidates import candidate_header
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('header','compiler','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 h=a.out/'resident-mapped-source.private.h';h.write_text(candidate_header(a.header.read_text()),newline='\n')
 text=(ROOT/'tests/expert_q2_sparse.cpp').read_text().replace('#include <mapped_source.h>','#include "resident-mapped-source.private.h"\n#include <thread>')
 text=text.replace('MappedSourceReader','ResidentMappedSourceReader')
 text=text.replace('{"retained",65536}','{"retained",64ull<<20}')
 # Keep all ranges and residues, but put the two real fragments inside the
 # existing conservatively inset file regions so the parallel arm is exercised.
 for before,after in [('42345','(8ull*1024*1024+42345)'),('41345','(8ull*1024*1024+41345)'),('12345','(8ull*1024*1024+12345)'),('12344','(8ull*1024*1024+12344)'),('10000','(8ull*1024*1024+10000)')]:
  text=re.sub(r'\b'+before+r'\b',after,text)
 text=text.replace(',2,777}',',2,16ull*1024*1024+777}').replace('+777+34','+16ull*1024*1024+777+34')
 text=text.replace('physical_offset=65536','physical_offset=64ull<<20')
 text=text.replace('int main(){','int main(int argc,char**argv){\n    check(argc==2);Q2_reader_candidate_mode.store(unsigned(std::atoi(argv[1])));')
 point='    reader.before_unmap(base,bytes);'
 extra='''    std::array<std::thread,4> queries;
    for(auto&t:queries)t=std::thread([&]{for(unsigned i=0;i<10000;++i)
        check(reader.contains_metadata(base+(8ull<<20)+10000,1));});
    for(auto&t:queries)t.join();
    const auto stats=reader.candidate_stats();
    if(Q2_reader_candidate_mode==1)check(stats[0]>0);
    if(Q2_reader_candidate_mode==2)check(stats[2]>0);
    std::cout<<"mode="<<Q2_reader_candidate_mode<<" hint_hits="<<stats[0]<<" lookups="<<stats[1]<<" composite_parallel="<<stats[2]<<'\\n';
'''
 require(text.count(point)==1,'One original retirement point required');text=text.replace(point,extra+point)
 source=a.out/'reader.private.cpp';source.write_text(text,newline='\n');exe=a.out/'reader.exe'
 command=[str(a.compiler),'-std=c++17','-O2','-pthread','-DEXPERT_Q2_PAIR_CASES','-I',str(a.out),'-I',str(ROOT/'native/app'),str(source),'-o',str(exe)]
 env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
 result=subprocess.run(command,capture_output=True,env=env);(a.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
 require(result.returncode==0,result.stderr.decode(errors='replace')[-5000:]);runs=[]
 for mode in range(3):
  result=subprocess.run([str(exe),str(mode)],capture_output=True,env=env);output=(result.stdout+result.stderr).decode(errors='replace');print(output,flush=True)
  require(result.returncode==0,'Exact resident reader control failed');runs.append(dict(mode=mode,output=output))
 write_json(a.out/'receipt.private.json',dict(completed=True,source_header=record(a.header),candidate_header=record(h),source=record(source),command=command,runs=runs,PS5_operations=0))
if __name__=='__main__':main()
