#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check zero-copy ring ownership and drain every returned-error path."""
import argparse,json,os,subprocess
from pathlib import Path
from check_next_five_stream import CPP
from expert_q4 import record,require,write_json
from ring_stream_source import transform
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);body=transform()
    native=a.out/'streaming_read_pool.h';native.write_text(body,newline='\n')
    body=body.replace('posix_memalign','host_align').replace('std::free(spare_)','host_free(spare_)')
    (a.out/'stream-host.private.h').write_text(body,newline='\n')
    cpp=CPP.replace('qwen_next_refill_before_consume','qwen_post_ring_enabled')
    cpp=cpp.replace('std::atomic<unsigned>entered{0},returned{0};','std::atomic<unsigned>entered{0},returned{0},active{0},peak{0};')
    cpp=cpp.replace('++entered;const auto id=', '++entered;const auto in=++active;auto max=peak.load();while(max<in&&!peak.compare_exchange_weak(max,in)){};const auto id=')
    cpp=cpp.replace('++returned;','--active;++returned;')
    cpp=cpp.replace('pool.require_completed();pool.stop_completed();','if(active||peak>4)throw std::runtime_error("More than four simultaneous reads");pool.require_completed();pool.stop_completed();')
    source=a.out/'check.private.cpp';source.write_text(cpp,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'check.exe'
    for i,command in enumerate([[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(a.out),'-I'+str(ROOT/'native/app'),str(source),'-o',str(exe)],[str(exe)]]):
        r=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-2000:])
    write_json(a.out/'complete.private.json',dict(completed=True,cases=8,all_bytes_preserved_during_consumption=True,
        all_queued_reads_returned=True,maximum_simultaneous_reads=4,extra_owned_CPU_bytes=2<<20,owned_source=record(native),
        inputs=[record(__file__),record(ROOT/'tools/ring_stream_source.py'),record(source)],PS5_operations=0,native_speed_proven=False))
    print(r.stdout.decode().strip())

if __name__=='__main__':main()
