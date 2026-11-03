# SPDX-License-Identifier: MIT
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from iq2_down_ggml_completion import ORDER,validate_terminal

owner=dict(held=True,device=100,instance=101,epoch=45,driver_used_bytes=80,driver_reserved_bytes=100,
           global_capacity_measured=False,device_destroy_calls=0,driver_retire_calls=0,
           post_completion_GPU_operations=0,ordinary_process_close_required=True)
rows=[dict(layer=l,width=w,GGML_graphs=1,positive_fence=True,all_case_resources_retired=True,
           actual_Gate_Up_prefix_bytes=11827200,actual_Down_view_offset=460800,carrier_plane_bytes=460800,
           selected=2 if w<=2 else 10,output_values=w*(2 if w<=2 else 10)*2560,
           all_outputs_passed=True,mismatches=0,canaries_exact=True) for l,w in ORDER]
t=dict(completed=True,GGML_carrier_ABI=True,unknown_completion=False,native_PS5=True,model_loads=0,
       all_GPU_resources_positively_retired=False,all_case_resources_positively_retired=True,
       all_source_IO_completed=True,IO_journal_closed=True,GGML_backend_free_calls=0,
       retained_GGML_backend=102,all_outputs_passed=True,cases=rows,retained_completed_device=owner)
validate_terminal(t)
negative=copy.deepcopy(t);negative['cases']=negative['cases'][:2]
negative['all_outputs_passed']=False;negative['cases'][-1].update(all_outputs_passed=False,mismatches=3)
validate_terminal(negative)
changes=[lambda x:x.update(unknown_completion=True),lambda x:x.update(all_source_IO_completed=False),
         lambda x:x.update(IO_journal_closed=False),lambda x:x.update(GGML_backend_free_calls=1),
         lambda x:x.update(retained_GGML_backend=0),lambda x:x['cases'][0].update(positive_fence=False),
         lambda x:x['cases'][0].update(all_case_resources_retired=False),lambda x:x['cases'].pop(),
         lambda x:x['cases'].reverse(),lambda x:x['cases'][0].update(actual_Down_view_offset=0),
         lambda x:x['retained_completed_device'].update(device=0),
         lambda x:x['retained_completed_device'].update(post_completion_GPU_operations=1),
         lambda x:x['retained_completed_device'].update(driver_used_bytes=101),
         lambda x:x['cases'][0].update(mismatches=1),
         lambda x:x.update(all_outputs_passed=False)]
for change in changes:
    bad=copy.deepcopy(t);change(bad)
    try:validate_terminal(bad)
    except (RuntimeError,KeyError):pass
    else:raise AssertionError('Incomplete or differently owned work must refuse')
bad=copy.deepcopy(negative);bad['cases'].append(copy.deepcopy(rows[2]))
try:validate_terminal(bad)
except RuntimeError:pass
else:raise AssertionError('No graph may follow a returned numerical negative')
suffix=copy.deepcopy(t);suffix['completed_GGML_case_prefix']=2;suffix['cases']=suffix['cases'][2:]
validate_terminal(suffix)
suffix_negative=copy.deepcopy(suffix);suffix_negative['cases']=suffix_negative['cases'][:1]
suffix_negative['all_outputs_passed']=False;suffix_negative['cases'][0].update(all_outputs_passed=False,mismatches=3)
validate_terminal(suffix_negative)
for change in (lambda x:x.update(completed_GGML_case_prefix=1),
               lambda x:x.update(completed_GGML_case_prefix=True),
               lambda x:x['cases'].insert(0,copy.deepcopy(rows[1])),
               lambda x:x['cases'].pop()):
    bad=copy.deepcopy(suffix);change(bad)
    try:validate_terminal(bad)
    except RuntimeError:pass
    else:raise AssertionError('Only the complete, non-replayed source-bound suffix may close')
print('{"completed":true,"positive_controls":4,"negative_controls":20,"PS5_operations":0}')
