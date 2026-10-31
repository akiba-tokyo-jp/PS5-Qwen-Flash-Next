#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Spend verified resident-Q4 saving on a 3712-slot cache with explicit quotas."""
import argparse,copy,json
from pathlib import Path
from build_next_five_comparison import command_for,update_sources,ROOT
from build_cache_capacity_1125 import recipes,literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from rebind_cache_provenance import rebind_cache
SLOTS=3712;GROWTH=(SLOTS-3072)*1536000;CACHE=4720619520+GROWTH;TRANSFER=3207049216+GROWTH;CAP=5216120832+GROWTH

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    require(n['precision_candidate']['scope']['saved_payload_bytes']==1038090240,'Exact Q4 saving required')
    require(GROWTH+(48<<20)<1038090240 and (SLOTS+1)*537600<2<<30,'Q4 saving and per-bank geometry must cover growth')
    ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1];cc=n['routing_sharing']['commands'][1];en=n['routing_sharing']['commands'][2]
    linked={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
    pc=next(c for c in linked.values()if Path(c[c.index('-c')+1]).name=='padding.private.cpp')
    commands={r['object_path']:r['command']for r in n['CPU_metadata_scope']['changed_sources']if r['object_path']in n['link_command']}
    for cmd in (ec,oc,cc,en,pc):commands[cmd[cmd.index('-o')+1]]=cmd
    profile=a.cache/'build/Resident-cache3072-11600/resident_output_q8_profile.h';reset=profile.with_name('resident_output_q8_cache_reset.h');budget=a.cache/'build/Four-next-rollback-17600/device_buffer_budget.h'
    generated={
        profile.name:profile.read_text().replace('cache_transfer=3207049216','cache_transfer='+str(TRANSFER)).replace('cache_budget=4720619520','cache_budget='+str(CACHE)).replace('+3163852800ull','+3163852800ull+1038090240ull'),
        reset.name:reset.read_text().replace('3072','NEXTMAX').replace('1381','3072').replace('NEXTMAX',str(SLOTS)),
        budget.name:budget.read_text().replace('5216120832ull',str(CAP)+'ull').replace('1600ull << 20','2ull << 30')}
    mappings={}
    for name,body in generated.items():
        dest=a.out/name;dest.write_text(body,newline='\n');targets={ROOT/'native/app'/name,ROOT.with_name(ROOT.name+'-refill')/'native/app'/name}
        for cmd in commands.values():
            dirs=[Path(cmd[cmd.index('-c')+1]).parent]+[Path(cmd[i+1])for i,x in enumerate(cmd[:-1])if x=='-I']
            targets.update(d/name for d in dirs if(d/name).is_file())
        for row in n['inputs_before']:
            if Path(row['path']).name==name:targets.add(Path(row['path']))
        for target in targets:mappings[target]=dest
    overlay=a.out/'capacity-overlay.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=k.resolve().as_posix(),**{'external-contents':v.resolve().as_posix()})for k,v in sorted(mappings.items())]))
    entry=Path(ec[ec.index('-c')+1]).read_text();updates={}
    for key,member in [('all_Q2_optimized_monitor','scope'),('expert_q2_model','scope'),('output_Q8_normal','probation_scope'),('resident_all_Q8','scope'),('cold_request','scope')]:
        before=n[key][member];after=copy.deepcopy(before)
        for k,value in dict(active_cache_slots=SLOTS,expected_active_Q2_slots=SLOTS,cache_budget_bytes=CACHE,transferred_postload_quota_bytes=TRANSFER,postload_single_buffer_bytes=2<<30).items():
            if k in after:after[k]=value
        if literal(before)in entry:entry=entry.replace(literal(before),literal(after))
        updates[(key,member)]=after
    old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='resident-Q4-cache3712',candidate_id=0,active_cache_slots=[3072,SLOTS],physical_cache_planes=SLOTS+1,physical_cache_bytes=CACHE,
        resident_Q4_saving_bytes=1038090240,cache_growth_bytes=GROWTH,postload_budget_bytes=CAP,single_buffer_bytes=2<<30,
        both_arms_resident_Q4=True,comparison_to_installed_Q8_requires_separate_control=True,candidate_F32_and_token_equality_required=False)
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?1:0);','qwen_next_select(0);')
    entry=once(entry,'qwen_app_select_output_Q8_slots(3072);','qwen_app_select_output_Q8_slots(arm?'+str(SLOTS)+':3072);')
    entry=once(entry,'qwen_app::model_postload_device_budget==5216120832ull','qwen_app::model_postload_device_budget=='+str(CAP)+'ull')
    entry=once(entry,'arm==0?"installed-control":"routing4";','arm==0?"Q4-cache3072":"Q4-cache3712";')
    precision_scope=dict(n['precision_candidate']['scope'],active_cache_slots=SLOTS,cache_budget_bytes=CACHE)
    entry=once(entry,literal(n['precision_candidate']['scope']),literal(precision_scope))
    entry=once(entry,'{"active_slots",3072}','{"active_slots",i<10&&(i/2==2||i/2==3)||i>=10?'+str(SLOTS)+':3072}')
    cache=Path(cc[cc.index('-c')+1]).read_text();cache=cache.replace('g.n_slots < 3072','g.n_slots < '+str(SLOTS)).replace('output_Q8_selected_slots=3072','output_Q8_selected_slots='+str(SLOTS))
    cache=cache.replace('groups[0].n_slots!=1381&&groups[0].n_slots!=3072','groups[0].n_slots!=3072&&groups[0].n_slots!='+str(SLOTS)).replace('slots!=1381&&slots!=3072','slots!=3072&&slots!='+str(SLOTS))
    header=Path(oc[oc.index('-c')+1]).parent/'limit-winner-bundle.private.h';(a.out/header.name).write_bytes(header.read_bytes())
    variants={};originals={};special={ec[ec.index('-o')+1]:('entry',entry),cc[cc.index('-o')+1]:('cache',cache),oc[oc.index('-o')+1]:('owner',Path(oc[oc.index('-c')+1]).read_text()),en[en.index('-o')+1]:('engine',Path(en[en.index('-c')+1]).read_text()),pc[pc.index('-o')+1]:('padding',Path(pc[pc.index('-c')+1]).read_text().replace('1600ull<<20','2ull<<30'))}
    for i,(obj,cmd)in enumerate(commands.items()):
        src=Path(cmd[cmd.index('-c')+1]);label,text=special.get(obj,('budget'+str(i),src.read_text()));variants[label]=(cmd+['-ivfsoverlay',str(overlay)],text);originals[label]=record(src)
    r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),overlay,header,a.out/header.name,*[a.out/k for k in generated]])
    update_sources(r,jobs,sources)
    for (key,member),value in updates.items():r[key][member]=value
    r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
    for key in ('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):r[key].update(scope=r['all_Q2_optimized_monitor']['scope'],model_scope=r['expert_q2_model']['scope'])
    r['cold_request']['device_ledger_cap_bytes']=CAP;r['resident_cache3072'].update(active_slots=SLOTS,physical_planes=SLOTS+1,cache_budget_bytes=CACHE,transferred_postload_quota_bytes=TRANSFER,postload_single_buffer_bytes=2<<30)
    r['resident_weight_normal']['active_slots']=SLOTS;r['precision_candidate']['scope']['active_cache_slots']=SLOTS;r['precision_candidate']['scope']['cache_budget_bytes']=CACHE
    r['CPU_metadata_scope']['changed_sources']=[dict(original=originals[k],source=sources[k],object_path=jobs[k][jobs[k].index('-o')+1],command=jobs[k])for k in jobs if k not in ('entry','cache','engine','padding')]
    rebind_cache(r,a.out,jobs['cache'],sources['cache']);seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='Q4_saving_cache_redistribution',candidate=record(a.out/'receipt.private.json'),scope=scope,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
