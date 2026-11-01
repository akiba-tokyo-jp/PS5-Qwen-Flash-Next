#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prove the current source map before retiring unreferenced historical Q4 data."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
C=Path('D:/PS5-AI/qwen-flash-next')
TITLE='/data/ai/native-moss-image-sft/PPSA99190'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--plan-only',action='store_true');a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 baseline=C/'build/Frontier-normal-53060/receipt.private.json';n=json.loads(baseline.read_text())
 entry=n['precision_candidate']['commands']['entry'];dirs=[Path(entry[i+1])for i,x in enumerate(entry[:-1])if x=='-I']
 constants=next(d/'precision-plan.private.h'for d in dirs if(d/'precision-plan.private.h').exists())
 # Reuse only the qualified host metadata reader; production planner bodies remain current.
 old=C/'build/Resident-Q8-protected-sources-11489'
 shim=old/'expert_q2_composite_source.h';(a.out/shim.name).write_bytes(shim.read_bytes())
 for name in('resident_all_q8_source.h','resident_shared_q8_source.h','resident_output_q8_source.h','expert_all_q2_source_integrity.h','precision_overlay_receipt.h'):
  (a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
 actual_entry=Path(entry[entry.index('-c')+1]).read_text();actual_precision=Path(re.search(r'#include "([^"]+/precision_overlay_receipt.h)"',actual_entry).group(1))
 (a.out/'precision_overlay_receipt.h').write_bytes(actual_precision.read_bytes())
 (a.out/constants.name).write_bytes(constants.read_bytes())
 source=(old/'inventory.cpp').read_text().replace('#include "resident_shared_q8_source.h"','#include "precision_overlay_receipt.h"')
 start=source.index('int main(')
 source=source[:start]+r'''int main(int argc,char**argv){try{if(argc!=6)return 2;using J=nlohmann::json;
 auto gate=J::parse(read(argv[1])).at("native_first_generation_validation");auto r=J::parse(read(argv[2]));
 auto parent=J::parse(read(argv[3])),base=J::parse(read(argv[4])),original=J::parse(read(argv[5]));
 auto out=J::parse(gate.at("resident_output_Q8_source_integrity").at("raw").get<std::string>());
 auto shared=J::parse(gate.at("resident_shared_Q8_source_integrity").at("raw").get<std::string>());
 auto selected=J::parse(gate.at("precision_source_integrity").at("raw").get<std::string>());
 auto plan=qwen_app::precision_source_integrity(gate,r,parent,base,original,out.at("source_directory"),shared.at("source_directory"),selected.at("source_directory"),r.at("mapped_file_bytes"));
 J files=J::array();for(const auto&f:plan.physical)files.push_back({{"path",f.path},{"bytes",f.bytes},{"identity",f.identity}});
 std::cout<<J({{"completed",true},{"physical",files},{"backing",qwen_app::source_inventory_backing},{"logical_files",plan.logical.size()},{"PS5_operations",0}}).dump()<<'\n';
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''
 cpp=a.out/'inventory.cpp';cpp.write_text(source,newline='\n')
 up=C/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';tool=ROOT.parents[1]/'toolchain/msys-clang64/clang64/bin'
 env=dict(os.environ,PATH=str(tool)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
 cmd=[str(tool/'clang++.exe'),'-std=c++17','-O0',str(cpp),str(C/'build/Resident-all-Q8-host-11456/sha256.o'),'-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),'-o',str(a.out/'inventory.exe')]
 run=subprocess.run(cmd,capture_output=True,timeout=180,env=env);(a.out/'compile.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
 inputs=[C/'hardware-first-generation-53100/private-policy/development.json',C/'Post-top2-output-Q4-32100/model-receipt.json',C/'resident-shared-Q8-10456/model-receipt.json',C/'resident-output-Q8-9193/model-receipt.json',C/'Expert-all-Q2-receipt-8652.json']
 require(record(inputs[1])['sha256']=='46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426','Exact current and immediate model required')
 run=subprocess.run([str(a.out/'inventory.exe'),*map(str,inputs)],capture_output=True,timeout=30,env=env);(a.out/'planner.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
 current=json.loads(run.stdout);require(current['completed']and current['logical_files']==76,'Complete actual source plan required')
 legacy_path=C/'build/Resident-Q8-source-map-11498/source-maps.private.json';legacy=json.loads(legacy_path.read_text())
 old_q4={x['path']:x for x in legacy['physical']if'/expert-q4-'in x['path']}
 require(all(x['path']in old_q4 and x['identity']==old_q4[x['path']]['identity']for x in current['physical']if'/expert-q4-'in x['path']),'Historical source protection must be a superset of both current models')
 # Preserve that larger set as well as current sources and backing metadata.
 protected={x['path']:x for x in legacy['physical']}
 for x in current['physical']+current['backing']:protected[x['path']]=x
 protect=a.out/'protected.private.json';write_json(protect,dict(completed=True,physical=list(protected.values()),current_source_plan=current))
 listing_path=C/'Throughput-storage-54040/weight-directory-listings.private.json';listing=json.loads(listing_path.read_text());directory=next(x for x in listing if x['directory'].startswith('expert-q4-'))
 seal_path=C/'build/Expert-Q4-relocation-7670/source-integrity.private.json';seal=json.loads(seal_path.read_text());old_parts={x['path']:x for f in seal['logical_files']for x in f['parts']}
 candidates=[];root='/app0/'+directory['directory']
 for x in directory['files']:
  path=root+'/'+x['name']
  if not x['bytes']or path in protected or path not in old_parts:continue
  row=old_parts[path];require(row['bytes']==x['bytes']and row['identity'][5]==x['bytes']and row['identity'][2:5]==[0o100644,0,0],'Only unchanged sealed old payloads may be selected');candidates.append(row)
 require(sum(x['bytes']for x in candidates)>=14_000_000_000,'Enough genuinely unused data must exist; no reserve relaxation')
 protected_ids={(x['identity'][0],x['identity'][1])for x in protected.values()}
 require(all((x['identity'][0],x['identity'][1])not in protected_ids for x in candidates),'No hard-link alias of a protected source may be retired')
 write_json(a.out/'selection.private.json',dict(completed=True,selected=candidates,total_bytes=sum(x['bytes']for x in candidates),protected_sources=record(protect),historical_Q4_seal=record(seal_path),source_planner_replayed=True,console_access=False,PS5_operations=0,native_changes=0))
 if a.plan_only:
  print(json.dumps(dict(read_only_host_plan_completed=True,current_source_files=len(current['physical']),protected_files=len(protected),obsolete_parts=len(candidates),obsolete_bytes=sum(x['bytes']for x in candidates),PS5_operations=0,native_changes=0)));return
 package=C/'build/Frontier-normal-SELF-53068/receipt.private.json';control=json.loads(package.read_text())['SELF'];require(record(control['path'])==control and control['sha256']=='1a76c37007962b9da767b0e70667d140bfaeb2138a4d29925245958afd84047e','Exact installed control archive required')
 nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-throughput-reclaim-'+nonce
 ident=lambda key:'{'+','.join(str(v)+'ULL'for v in key)+'}'
 canonical=lambda path:TITLE+path[5:]if path.startswith('/app0/')else path
 text='#pragma once\nstruct Protected{const char*path;std::array<std::uint64_t,10>identity;};\nstatic const Protected protected_files[]={'+','.join('{'+json.dumps(canonical(x['path']))+','+ident(x['identity'])+'}'for x in protected.values())+'};\n'
 text+='struct Obsolete{const char*path;std::uint64_t bytes;const char*sha256;std::array<std::uint64_t,10>identity;};\nstatic constexpr unsigned obsolete_count='+str(len(candidates))+';\nstatic const Obsolete obsolete_files[]={'+','.join('{'+json.dumps(canonical(x['path']))+','+str(x['bytes'])+'ULL,'+json.dumps(x['sha256'])+','+ident(x['identity'])+'}'for x in candidates)+'};\n'
 text+='static const char*obsolete_directory='+json.dumps(canonical(root))+';\nstatic const char*control_path='+json.dumps(TITLE+'/eboot.bin')+';\nstatic constexpr std::uint64_t control_bytes='+str(control['bytes'])+'ULL;\nstatic const char*control_hash='+json.dumps(control['sha256'])+';\n'
 header=a.out/'obsolete-weight-plan.private.h';header.write_text(text,newline='\n')
 parent_path=C/'build/Throughput-full-bundles-54020/manifest.private.json';parent=json.loads(parent_path.read_text());oldbase=parent_path.parent
 for name in('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((oldbase/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 native=ROOT/'native/qwen_flash_next/reclaim_obsolete_weights.cpp';native_source=a.out/'reclaim.private.cpp';native_source.write_text(native.read_text().replace('original_BF16_and_recipe_retained=1','current_and_immediate_models_and_recipes_retained=1'),newline='\n')
 commands=[[v.replace(str(oldbase),str(a.out))for v in command]for command in parent['commands']];commands[1][commands[1].index('-c')+1]=str(native_source)
 for i,command in enumerate(commands):
  run=subprocess.run(command,capture_output=True,timeout=180,env=env);(a.out/f'native-{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={line.split()[0]for line in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if line.split()}
 require('ftruncate'in names and not any(x.startswith(('sceAgc','sceSystemServiceLaunch','sceSystemServiceKill'))or x in('unlink','rename','pwrite')for x in names),'Only exact already-sealed obsolete payload truncation allowed')
 write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',selected=candidates,protected_sources=record(protect),control_SELF=control,retired_bytes=sum(x['bytes']for x in candidates),GPU_calls=0,title_launches=0,automatic_retries=0,all_selected_whole_hashes_verified_before_first_truncate=True,active_and_immediate_source_writes=0,inputs=[record(x)for x in(Path(__file__),baseline,constants,shim,legacy_path,listing_path,seal_path,package,parent_path,native,native_source,header,*inputs)]))
 print(json.dumps(dict(actual_current_source_planner_replayed=True,protected_files=len(protected),obsolete_parts=len(candidates),obsolete_bytes=sum(x['bytes']for x in candidates),GPU_calls=0)))
if __name__=='__main__':main()
