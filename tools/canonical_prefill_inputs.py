#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Move qualified P1 rebuild sources into current without changing object bytes."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save


def entry(current,view,build,refinement):
    selected=build['entries']['candidate'];old=Path(selected['source']['path']).parent
    need(record(selected['source']['path'])==selected['source'],'The measured P1 entry source changed')
    headers=[]
    for path in old.glob('*.h'):
        target=view/path.name;shutil.copyfile(path,target);headers.append(record(target))
    source=view/Path(selected['source']['path']).name;shutil.copyfile(selected['source']['path'],source)
    command=next(c for c in build['commands'] if '-c' in c and c[c.index('-c')+1]==selected['source']['path']).copy()
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:
        target=view/Path(root['external-contents']).name;need(target.is_file(),'Every selected entry header needs a canonical copy')
        root['external-contents']=target.resolve().as_posix()
    vfs=view/'selected-view.private.json';save(vfs,overlay)
    command=[str(view) if value==str(old) else value for value in command]
    obj=current/'linked-inputs'/('P1-'+selected['entry']['sha256'][:16]+'-entry.o')
    command[command.index('-ivfsoverlay')+1]=str(vfs);command[command.index('-c')+1]=str(source)
    command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(view/'entry.private.d')
    command+=['-ffile-prefix-map='+str(view)+'='+str(old)]
    run=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(view),TEMP=str(view)))
    (view/'entry-compile.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
    need(all(record(obj)[k]==selected['entry'][k] for k in ('bytes','sha256')),
         'Canonical headers and entry must reproduce the exact measured normal-UI object')
    save(view/'canonical-P1-entry.private.json',dict(completed=True,refinement=record(refinement),
        source=record(source),entry=record(obj),command=command,inputs=[record(source),record(vfs),*headers],
        all_entry_object_bytes_exact=True,normal_UI_preserved=True,PS5_operations=0))


def providers(current,view,build,reuse=None):
    if reuse:
        proof=load(reuse)
        need(proof['completed'] and proof['all_provider_objects_byte_exact'] and
             proof['qualified_graph_sha256']==build['model_provider_reused']['sha256'] and
             proof['qualified_selector_sha256']==build['selector']['sha256'] and
             all(record(r['path'])=={k:r[k] for k in ('path','bytes','sha256')} for r in
                 (proof['graph'],proof['selector'],*proof['dependencies'])),
             'Only the complete unchanged canonical provider compilation may be reused')
        save(view/'canonical-P1-providers.private.json',dict(proof,reused_completed_compilation=record(reuse),
            unchanged_compilations_replayed=0))
        return {'model_graph.o':proof['graph']},proof['selector'],[proof['graph_command'],proof['selector_command']],proof['dependencies']
    original=load(build['graph_provider']['path']);graph=original['artifacts']['candidate']['source']
    need(record(graph['path'])==graph,'The qualified post-trunk graph source changed')
    command=next(c for c in original['commands'] if '-c' in c and c[c.index('-c')+1]==graph['path']).copy()
    graph_dir=view/'graph';graph_dir.mkdir();env=dict(os.environ,TMP=str(graph_dir),TEMP=str(graph_dir))
    deps=graph_dir/'dependencies.private.d';scan=command.copy();scan[scan.index('-o')+1]=str(graph_dir/'dependency-scan.o')
    scan+=['-M','-MF',str(deps)]
    run=subprocess.run(scan,capture_output=True,timeout=180,env=env)
    (graph_dir/'dependency-scan.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
    text=re.sub(r'\\\r?\n',' ',deps.read_text());names=text.split(': ',1)[1].split()
    files=[Path(n.replace('\\:',':').replace('\\\\','\\')) for n in names]
    need(files and all(p.is_file() for p in files),'Every actual graph dependency must resolve')
    cache=current.parent;up=cache/'upstream';toolchain=Path(command[0]).parents[1]
    sdk=next(Path(command[i+1]) for i,v in enumerate(command[:-1]) if v=='-isysroot')
    preserved=[];roots=[]
    for source in dict.fromkeys(files):
        # SDK and pinned upstream sources are permanent toolchain inputs. All
        # campaign, repository and generated headers receive canonical copies.
        if any(source.resolve().is_relative_to(p.resolve()) for p in (up,toolchain,sdk,current)):
            preserved.append(record(source));continue
        row=record(source);target=graph_dir/(source.name if source.resolve()==Path(graph['path']).resolve()
                                        else row['sha256'][:16]+'-'+source.name)
        shutil.copyfile(source,target);roots.append(dict(type='file',name=source.resolve().as_posix(),
            **{'external-contents':target.resolve().as_posix()}))
        preserved.append(dict(record(target),virtual_path=str(source)))
    need(any(Path(r['name']).resolve()==Path(graph['path']).resolve() for r in roots) and
         any(Path(r['name']).name=='qwen4exp.post-trunk.cpp' for r in roots),
         'Both the unity source and qualified model implementation need canonical copies')
    overlay=graph_dir/'source-view.private.json';save(overlay,{'version':0,'case-sensitive':'false','use-external-names':False,'roots':roots})
    # Compile a real canonical input path while preserving the original
    # __FILE__ strings. Included source/header paths retain their virtual names.
    source=next(r['external-contents'] for r in roots if Path(r['name']).resolve()==Path(graph['path']).resolve())
    obj=current/'linked-inputs'/('P1-'+build['model_provider_reused']['sha256'][:16]+'-model_graph.o')
    command[command.index('-c')+1]=source;command[command.index('-o')+1]=str(obj)
    command+=['-ivfsoverlay',str(overlay),'-ffile-prefix-map='+source+'='+Path(graph['path']).as_posix()]
    run=subprocess.run(command,capture_output=True,timeout=240,env=env)
    (graph_dir/'compile.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
    need(all(record(obj)[k]==build['model_provider_reused'][k] for k in ('bytes','sha256')),
         'Canonical graph inputs must reproduce the exact numerically qualified model object')
    selector=current/'linked-inputs'/('P1-'+build['selector']['sha256'][:16]+'-cold-selector.o')
    job=next(c for c in build['commands'] if '-c' in c and c[c.index('-o')+1]==build['selector']['path']).copy()
    selector_source=Path(job[job.index('-c')+1]);source=view/selector_source.name
    shutil.copyfile(selector_source,source);shutil.copyfile(selector_source.parent/'prefill_process_candidate.cpp',view/'prefill_process_candidate.cpp')
    job[job.index('-c')+1]=str(source);job[job.index('-o')+1]=str(selector)
    job+=['-ffile-prefix-map='+str(view)+'='+str(selector_source.parent)]
    run=subprocess.run(job,capture_output=True,timeout=180,env=env)
    (view/'selector-compile.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
    need(all(record(selector)[k]==build['selector'][k] for k in ('bytes','sha256')),
         'The canonical cold selector must reproduce the actual measured object')
    sources=[record(source),record(view/'prefill_process_candidate.cpp'),record(overlay),*preserved]
    save(view/'canonical-P1-providers.private.json',dict(completed=True,graph=record(obj),selector=record(selector),
        graph_command=command,selector_command=job,dependencies=sources,all_provider_objects_byte_exact=True,
        qualified_graph_sha256=build['model_provider_reused']['sha256'],qualified_selector_sha256=build['selector']['sha256'],PS5_operations=0))
    return {'model_graph.o':record(obj)},record(selector),[command,job],sources


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','refinement','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--entry-only',action='store_true')
    args=parser.parse_args()
    need(args.out.resolve().is_relative_to((args.current/'provenance').resolve()),'Canonical sources must stay inside current provenance')
    args.out.mkdir(parents=True,exist_ok=False)
    if args.entry_only:entry(args.current,args.out,load(args.refinement),args.refinement)
    else:providers(args.current,args.out,load(args.refinement))
    print(json.dumps(dict(completed=True,canonical_entry_byte_exact=args.entry_only,
        canonical_graph_and_selector_byte_exact=not args.entry_only,PS5_operations=0)))
