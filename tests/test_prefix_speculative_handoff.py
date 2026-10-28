# SPDX-License-Identifier: MIT
"""Check the actual final-consumer owner and replacement-budget boundaries."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class FinalPrefixTests(unittest.TestCase):
    def test_real_header_refuses_uncertified_owners_and_wrong_capacity(self):
        compiler=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin/clang++.exe'
        if not compiler.exists():self.skipTest('Configured native workspace host compiler not available')
        temporary_root=ROOT/'.local/final-prefix-host-check';temporary_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root)as temporary:
            folder=Path(temporary);self.assertTrue(folder.resolve().is_relative_to(temporary_root.resolve()))
            source=folder/'check.cpp';binary=folder/'check.exe'
            source.write_text('''#include "prefix_speculative_handoff.h"
#include <cassert>
#ifdef MEASURED_PRE_CAPTURE_BYTES
static_assert(qwen_app::FinalPrefixHandoff::speculative_bytes==MEASURED_PRE_CAPTURE_BYTES,
 "Use the measured pre-capture payload, not the active state after the target batch");
#endif
int main(){
 int engine=0,context=0,other=0;qwen_app::FinalPrefixHandoff h;
 auto refuse=[&](auto f){bool refused=false;try{f();}catch(const std::runtime_error&){refused=true;}assert(refused);};
 assert(h.new_allocation(&context,h.prefix_bytes)==121634816);
 refuse([&]{h.arm(&engine,&context,2,true);});
 refuse([&]{h.certify(&engine,&context,h.prefix_bytes,false);});
 h.certify(&engine,&context,h.prefix_bytes,true);
 refuse([&]{h.arm(&engine,&context,1,true);});
 refuse([&]{h.arm(&engine,&other,2,true);});
 refuse([&]{h.arm(&engine,&context,2,false);});
 h.arm(&engine,&context,2,true);assert(h.pending(&engine,&context));
 refuse([&]{h.consume(&engine,&context,h.prefix_bytes,31);});
 h.consume(&engine,&context,h.prefix_bytes,30);assert(h.consumed());
 assert(h.new_allocation(&context,h.speculative_bytes)==0);
 refuse([&]{h.new_allocation(&other,h.speculative_bytes);});
 refuse([&]{h.new_allocation(&context,h.speculative_bytes+1);});
 refuse([&]{h.arm(&engine,&context,2,true);});
}
''',newline='\n')
            env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(folder),TEMP=str(folder))
            definition=[]
            retained=os.environ.get('QWEN_FROZEN_BUILD_DIR')
            if retained:
                captured=json.loads((Path(retained).parent/'hardware-first-generation-5800/native-arm2.result.private.json').read_text())
                definition=['-DMEASURED_PRE_CAPTURE_BYTES='+str(captured['checkpoint_capacity']['logical_payload_bytes'])]
            result=subprocess.run([str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Werror',*definition,'-I',str(ROOT/'native/app'),str(source),'-o',str(binary)],env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            result=subprocess.run([str(binary)],env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))

if __name__=='__main__':unittest.main()
