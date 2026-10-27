#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually check native predictive integration using actual patched cache code."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    path=Path(path).resolve()
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','model-io-manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(a.model_io_manifest.read_text());name='src/llama-moe-cache.cpp'
    source=a.model_io_manifest.parent/'source'/name
    if record(source)['sha256']!=manifest['sources'][name]['patched_sha256']:
        raise ValueError('Exact compiled native cache source required')
    s=source.read_text();planner=s[s.index('struct moe_cache_slru {'):s.index('// gate, up, down or gate_up, down')]
    hook=s[s.index('    void predict_next_expert('):s.index('    bool copy(ggml_backend_t backend,')]
    # Check the real call order as well as executing the extracted functions.
    copy=s[s.index('    bool copy(ggml_backend_t backend,'):s.index('    void log_stats() const')]
    assert copy.index('qwen_app_complete_predictive_expert()')<copy.index('g.slru.plan(')
    assert copy.index('predict_next_expert(il,g)')<copy.index('ggml_backend_tensor_set_async(backend, dst, src->data')
    fixture=planner+'''\nstruct Harness {
    struct group {moe_cache_slru slru;std::vector<ggml_tensor *> banks;};
    struct layer {int ig=0;std::vector<ggml_tensor *> experts;};
    struct binding {ggml_tensor *cached;};
    std::vector<layer> layers;std::unordered_map<const ggml_tensor *,binding> bindings;
    std::unique_ptr<qwen_app::CrossLayerForecast> forecast=std::make_unique<qwen_app::CrossLayerForecast>();
    int predicted_layer=-1,predicted_expert=-1;std::vector<int> ids;
'''+hook+'};\n'
    include=a.out/'actual_predictive_cache.inc';include.write_text(fixture,newline='\n')
    app=ROOT/'native/app';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    inputs=[Path(__file__),a.model_io_manifest,source,include,
        *[app/n for n in ('mapped_source.h','expert_prefetch_io.h','cross_layer_forecast.h',
            'expert_policy.h','online_expert_verification.h','predictive_cache_bridge.h')],
        ROOT/'tests/native_predictive_integration.cpp',ROOT/'tests/predictive_cache_adapter.cpp']
    frozen=[record(f)for f in inputs];steps=[]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for name,cases in (('native_predictive_integration',('positive','short','timeout')),
                       ('predictive_cache_adapter',('positive','ineligible'))):
        exe=a.out/(name+'.exe')
        cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',str(app),'-I',str(a.out),str(ROOT/'tests'/(name+'.cpp')),'-o',str(exe)]
        for label,command in [(name+'-compile',cmd)]+[(name+'-'+c,[str(exe),c])for c in cases]:
            r=subprocess.run(command,capture_output=True,timeout=120,env=env)
            (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
            steps.append(dict(label=label,returncode=r.returncode,command=command))
            if r.returncode:raise RuntimeError(label+': '+r.stderr.decode(errors='replace')[-3000:])
            print(label+' passed',flush=True)
    assert frozen==[record(f)for f in inputs]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(completed=True,inputs=frozen,steps=steps,
        actual_native_cache_functions=True,synthetic_IO=True,PS5_operations=0,CI_runs=0),indent=2)+'\n')
if __name__=='__main__':main()
