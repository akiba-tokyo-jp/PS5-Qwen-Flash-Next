#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace the supplemental pack with a sealed superset of complete triplets."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','bundle','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());pack=json.loads(a.bundle.read_text());require(pack['completed']and len(pack['bundles'])==112 and pack['CPU_Direct_positively_retired'],'Complete native sealed112 pack required')
 require(record(pack['selection']['path'])==pack['selection'],'Sealed placement selection changed');selection=json.loads(Path(pack['selection']['path']).read_text())['Experts'];pairs=sorted((r['layer'],r['expert'],i)for i,r in enumerate(selection))
 a.out.mkdir(parents=True,exist_ok=False);row=pack['output'];header=a.out/'current_bundle.private.h';path='/app0/'+row['path'].split('/PPSA99190/',1)[1]
 header.write_text('#pragma once\n#include <cstdint>\n#include <array>\ninline constexpr const char*Q2_current_path='+json.dumps(path)+';\ninline constexpr const char*Q2_current_SHA256='+json.dumps(row['sha256'])+';\ninline constexpr std::uint64_t Q2_current_expected_identity[]={'+','.join(map(str,row['identity']))+'};\ninline constexpr std::array<unsigned,2>Q2_current_keys[]={'+','.join('{'+f'{l},{e}'+'}'for l,e,i in pairs)+'};\ninline constexpr unsigned Q2_current_physical[]={'+','.join(str(i)for l,e,i in pairs)+'};\ninline bool Q2_current_mode=false;\n',newline='\n')
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-expanded-miss-placement-normal-v1',supplemental_bundles=112,total_bundled_Experts=532)
 cmd=prior['compile_commands'][0];entry=once(Path(cmd[cmd.index('-c')+1]).read_text(),literal(prior['all_Q2_optimized_monitor']['scope']),literal(scope));oc=prior['all_Q2_optimized_monitor']['commands'][1]
 result,commands,sources=link(a.parent,a.out,{'entry':(cmd,entry),'owner':(oc,Path(oc[oc.index('-c')+1]).read_text())},[Path(__file__),a.bundle,header])
 for key in ('normal_performance','output_Q8_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands);result[key]['scope']=scope
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=commands['entry']
 result['routing_sharing']['scope']=scope;result['routing_winners_normal'].update(scope=scope,actual_entry=sources['entry'])
 result['expanded_miss_placement']=dict(scope=scope,actual_sources=sources,commands=commands,bundle=record(a.bundle),additional_Experts=84,previous_Experts_retained=448,native_verification_pending=True)
 seal(result,a.workspace,a.cache,a.out);print('Sealed placement superset built; numerical weights and cache policy are unchanged.')
if __name__=='__main__':main()
