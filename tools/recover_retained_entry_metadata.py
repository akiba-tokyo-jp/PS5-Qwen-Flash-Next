#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover byte-exact embedded model metadata and deterministic entry headers."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from build_prefill16_monitor import causal_header_source
from build_speculative_batch_probe import once
from driver_table_storage import sections
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    def selected(name):
        rows=[r for r in retained if Path(r['original_path']).name==name]
        need(len(rows)==1,'One actual retained source/provider required: '+name)
        row={k:rows[0][k] for k in ('path','bytes','sha256')};need(record(row['path'])==row,'Retained entry changed');return row
    entry=selected('entry.o');source=selected('entry.private.cpp');native=load(args.current/'provenance/native-link.receipt.private.json')
    models={}
    for section in sections(Path(entry['path']).read_bytes()):
        if not section['name'].startswith('.rodata.str'):continue
        for raw in section['data'].split(b'\0'):
            if not raw.startswith(b'{') or len(raw)<100000:continue
            try:model=json.loads(raw)
            except (ValueError,UnicodeError):continue
            if len(model.get('tensors',[]))!=1256 or len(model.get('files',[]))!=76:continue
            sha=hashlib.sha256(raw).hexdigest()
            need(sha not in models or models[sha]['raw']==raw,'Ambiguous embedded metadata')
            models[sha]=dict(raw=raw,model=model)
    definitions={}
    for symbol,header in (('all_Q8_parent_raw','resident_all_q8_receipt.h'),('shared_Q8_base_raw','resident_shared_q8_receipt.h'),
                          ('output_Q8_parent_raw','resident_output_q8_receipt.h')):
        text=(ROOT/'native/app'/header).read_text()
        digests=re.findall(r'(?:all_Q8_parent_SHA256|shared_Q8_base_SHA256|resident_output_Q8_parent_SHA256)="([0-9a-f]{64})"',text)
        need(len(digests)==1 and digests[0] in models,'Exact source-bound embedded parent required')
        definitions[symbol]=models[digests[0]]
    prep_record=native['precision_candidate']['preparation'];need(record(prep_record['path'])==prep_record,'Selected precision preparation changed')
    prep=load(prep_record['path']);need(prep['completed'] and prep['selected_tensors']==109,'Exact selected 109-tensor precision plan required')
    for name in ('parent','candidate'):
        row=prep[name];need(row['sha256'] in models and len(models[row['sha256']]['raw'])==row['bytes'],'Complete byte-exact selected precision metadata required')
    outputs=[]
    for sha,row in models.items():
        path=args.out/('embedded-'+sha+'.json');path.write_bytes(row['raw']);outputs.append(record(path))
    for symbol,filename in (('shared_Q8_base_raw','shared_Q8_base.private.h'),('output_Q8_parent_raw','output_Q8_parent.private.h')):
        path=args.out/filename;path.write_text('#pragma once\ninline constexpr const char*'+symbol+'='+
            json.dumps(definitions[symbol]['raw'].decode())+';\n',encoding='utf-8',newline='\n');outputs.append(record(path))
    parent=definitions['all_Q8_parent_raw'];path=args.out/'resident_Q8_parent.private.h'
    path.write_text('#pragma once\ninline constexpr const char*all_Q8_parent_raw='+json.dumps(parent['raw'].decode())+
        ';\ninline bool all_Q8_parent_file(const std::string&name){for(const char*p:{'+
        ','.join(json.dumps(h['file']) for h in parent['model']['resident_Q8_overlay']['headers'])+
        '})if(name==p)return true;return false;}\n',encoding='utf-8',newline='\n');outputs.append(record(path))
    causal=causal_header_source((ROOT/'native/app/causal_expert_sharing.h').read_text()).replace('attempts_<8','attempts_<6')
    expected=native['speed_normal']['causal_source'];path=args.out/'speed-causal.private.h'
    path.write_text(causal,encoding='utf-8',newline='\n')
    need(record(path)['bytes']==expected['bytes'] and record(path)['sha256']==expected['sha256'],'Exact selected causal header was not reconstructed')
    outputs.append(record(path))
    parent=models[prep['parent']['sha256']];candidate=models[prep['candidate']['sha256']]
    gate=load(args.current/'qwen-runtime/development.json')['native_first_generation_validation']
    seal=json.loads(gate['resident_all_Q8_source_integrity']['raw']);root=seal['source_directory']
    need(seal['model_receipt_sha256']==prep['parent']['sha256'],'Original resident parent source root required')
    path=args.out/'precision-plan.private.h'
    path.write_text('#pragma once\nnamespace qwen_app {\n'+
        'inline constexpr const char*precision_parent_raw='+json.dumps(parent['raw'].decode())+';\n'+
        'inline constexpr const char*precision_candidate_raw='+json.dumps(candidate['raw'].decode())+';\n'+
        'inline constexpr const char*precision_parent_sha256='+json.dumps(prep['parent']['sha256'])+';\n'+
        'inline constexpr const char*precision_candidate_sha256='+json.dumps(prep['candidate']['sha256'])+';\n'+
        'inline constexpr const char*precision_parent_root='+json.dumps(root)+';\n'+
        'inline constexpr std::uint64_t precision_device_bytes='+str(prep['footprint']['device_weights'])+'ull;\n'+
        'inline constexpr std::uint64_t precision_expert_bytes='+str(prep['footprint']['mapped_experts'])+'ull;\n'+
        'inline bool precision_parent_file(const std::string&name){for(const char*p:{'+
        ','.join(json.dumps(h['file'])for h in parent['model']['resident_all_Q8_overlay']['headers'])+'})if(name==p)return true;return false;}\n'+
        'inline bool precision_selected_type(const std::string&name,int type){\n'+
        ''.join('if(name=='+json.dumps(c['name'])+')return type==2;\n'for c in candidate['model']['precision_overlay']['tensors'])+
        'return false;}\n}\n',encoding='utf-8',newline='\n');outputs.append(record(path))
    # Apply the exact typed-output transformation from the selected builder.
    typed=(ROOT/'native/app/precision_overlay_receipt.h').read_text()
    typed=once(typed,'m.largest_device_tensor!=675430400ull','m.largest_device_tensor!=357580800ull')
    typed='#include "output_plain_segments.h"\n'+typed
    marker='        auto plan=std::find_if(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;});need(__LINE__,plan!=expert_q2_pending_segments.end());'
    typed=once(typed,marker,'''        if(std::none_of(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;})){
            const auto output=std::find_if(baseline.at("tensors").begin(),baseline.at("tensors").end(),[](const Json&t){return t.at("name")=="output.weight";});
            need(__LINE__,output!=baseline.at("tensors").end()&&output->at("file")==name&&output->at("type")=="Q8_0"&&output->at("bytes")==675430400ull&&file==result.logical.end()-1);
            std::vector<std::uint64_t>physical_bytes;for(const auto&p:result.physical){need(__LINE__,p.identity[5]==p.bytes);physical_bytes.push_back(p.bytes);}
            expert_q2_pending_segments.push_back({file->path,output_plain_segments(file->bytes,file->parts,physical_bytes)});
        }
'''+marker)
    path=args.out/'precision_overlay_receipt.h';path.write_text(typed,encoding='utf-8',newline='\n');outputs.append(record(path))
    text=Path(source['path']).read_text();includes=re.findall(r'^#include "([^"]+/precision_overlay_receipt.h)"',text,re.M)
    need(len(includes)==1,'One actual generated typed header include required')
    text=text.replace('#include '+json.dumps(includes[0]),'#include "precision_overlay_receipt.h"',1)
    path=args.out/'entry.private.cpp';path.write_text(text,encoding='utf-8',newline='\n');outputs.append(record(path))
    report=dict(completed=True,actual_entry=entry,actual_source=source,embedded_complete_model_receipts=len(models),
        embedded_parent_and_candidate_metadata_byte_exact=True,selected_causal_header_byte_exact=True,
        selected_precision_preparation=prep_record,outputs=outputs,PS5_operations=0,
        missing_historical_VFS_views_reconstructed=False,entry_recompiled=False,native_equivalence_qualified=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('actual_entry','actual_source','outputs','selected_precision_preparation')}))


if __name__=='__main__':main()
