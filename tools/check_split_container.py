#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual startup inspection against all76 original metadata prefixes."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','model-directory','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    app=ROOT/'native/app/native_main.cpp';text=app.read_text()
    begin=text.index('static void inspect_container(');end=text.index('static std::uint64_t observed_system_headroom()',begin)
    assert text.count('footprint,tensor_names,file_bytes,split_integrity?file_identities.back()[5]:file_bytes)')==1
    (a.out/'native_container_inspection.h').write_text(text[begin:end],encoding='utf-8',newline='\n')
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text());upstream=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])
    qualified_path=a.cache/'direct-metadata-host-595/receipt.private.json';qualified=json.loads(qualified_path.read_text())
    assert len(qualified['files'])==76 and all(x['metadata_identical']and x['GGML_context_identical']for x in qualified['files'])
    libraries=[Path(row['path'])for row in qualified['libraries']]
    for path,row in zip(libraries,qualified['libraries']):assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    paths=[app,ROOT/'native/app/direct_metadata.h',ROOT/'native/app/model_receipt.h',ROOT/'native/app/memory_admission.h',ROOT/'tests/split_container.cpp',Path(__file__),qualified_path]
    original=json.loads((a.model_directory/'model-receipt.json').read_text());assert len(original['files'])==76
    identities={row['path']:[(a.model_directory/row['path']).stat().st_size,(a.model_directory/row['path']).stat().st_mtime_ns]for row in original['files']}
    before={str(path):hashlib.sha256(path.read_bytes()).hexdigest()for path in paths}
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'split-container.exe';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    command=[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app','-I',upstream/'ggml/include','-I',upstream/'vendor','-I',a.out,ROOT/'tests/split_container.cpp','-Wl,--start-group',*libraries,'-Wl,--end-group','-o',exe]
    result=subprocess.run(list(map(str,command)),capture_output=True,env=env,cwd=ROOT,timeout=120);(a.out/'compile.private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode('utf-8','replace')[-3000:]
    result=subprocess.run([str(exe),str(a.model_directory/'model-receipt.json'),str(qualified_path),str(a.model_directory),str(a.out/'metadata-only-physical-prefix.fixture')],capture_output=True,env=env,cwd=ROOT,timeout=180)
    (a.out/'run.private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode('utf-8','replace')[-3000:]
    report=json.loads(result.stdout);assert report['logical_files']==76 and report['original_footprints_and_tensor_names_equal']and report['physical_and_logical_refusals']==4
    assert before=={str(path):hashlib.sha256(path.read_bytes()).hexdigest()for path in paths}
    assert identities=={row['path']:[(a.model_directory/row['path']).stat().st_size,(a.model_directory/row['path']).stat().st_mtime_ns]for row in original['files']}
    (a.out/'receipt.private.json').write_text(json.dumps(dict(actual_entry_function_checked=True,inputs=before,result=report,host_originals_unchanged=True,console_requests=0,GPU_calls=0),indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
