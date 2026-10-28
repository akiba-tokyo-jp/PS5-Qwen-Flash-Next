#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Distinguish reused cache comparison provenance from the new passive entry."""
import argparse,copy,json
from pathlib import Path
from shader_storage import record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    prior=json.loads(a.parent.read_text());receipt=copy.deepcopy(prior);g=receipt['additional_cache_geometry'];monitor=receipt['adaptive_monitor']
    if monitor['active_slots']!=134 or not monitor['whole_model_capacity_ABBA_qualified']:
        raise ValueError('The completed combined 134-slot application build is required')
    if 'historical_capacity_comparison'in g:raise ValueError('This immutable provenance receipt is already sealed')
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('A frozen combined input changed')
    g['historical_capacity_comparison']=dict(compiled=copy.deepcopy(g['compiled'][:2]),actual_entry=g['actual_entry'],map_proof=g.pop('actual_seven_override_map_proof'))
    for i,key in enumerate(('actual_engine','actual_entry')):
        c=monitor['commands'][i];old=g['compiled'][i];obj=record(c[c.index('-o')+1])
        if prior['link_command'].count(obj['path'])!=1:raise ValueError('Exactly one current selected entry/engine object is required')
        g['compiled'][i]=dict(original_object=old['original_object'],object=obj,command=c,logical_source=monitor[key],compiled_source=monitor[key],historical_geometry_object=old['object'])
    g['actual_entry']=monitor['actual_entry'];g['commands']=copy.deepcopy(monitor['commands']);g['model_speed_qualified']=True
    mapping=Path(next(x[5:]for x in prior['link_command']if x.startswith('-Map=')));text=mapping.read_text()
    if not all(row['object']['path']in text for row in g['compiled']):raise ValueError('All fourteen current selected geometry objects must occur in the native map')
    if not all(row['object']['path']in prior['link_command']for row in prior['bounded_model_source_overrides']['objects']):
        raise ValueError('All seven selected ModelIO providers must remain linked')
    g['actual_seven_override_map_proof']=dict(map=record(mapping),all_fourteen_selected_objects_present=True,all_seven_selected_ModelIO_objects_present=True,driver_objects_unchanged=True,historical_comparison_objects_not_claimed_as_new=True)
    receipt['source_parent']=record(a.parent);receipt['inputs_before'] += [record(a.parent),record(Path(__file__))]
    a.out.mkdir(parents=True);(a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(current_entry_and_engine_provenance_sealed=True,application_bytes_changed=False,PS5_operations=0)))
if __name__=='__main__':main()
