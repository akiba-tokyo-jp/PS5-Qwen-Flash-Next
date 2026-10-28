# SPDX-License-Identifier: MIT
"""Check native batch regrouping and reject incomplete or changed route evidence."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from resident_route_review import require_same_tokens


def capture(widths, first_token=0):
    rows=[];position=first_token
    for width in widths:
        for layer in range(48):
            ids=[(position+token+layer+expert)%512 for token in range(width) for expert in range(10)]
            rows.append(dict(layer=layer,tokens=width,ids=ids))
        position+=width
    return dict(complete=True,layers_per_process=48,experts=512,experts_per_token=10,
                all_existing_downloads_and_synchronizations_returned=True,additional_GPU_downloads=0,
                records=rows,process_calls=len(widths),selected_indices=sum(widths)*48*10)


ordinary=capture([4,2,1,1]);regrouped=capture([4,2,2]);suffix=capture([1,1],6)
assert require_same_tokens(ordinary,regrouped)["tokens_per_layer"]==8
assert require_same_tokens(ordinary,suffix,6)["tokens_per_layer"]==2
controls=[]
changed=copy.deepcopy(regrouped);changed["records"][-1]["ids"][0]^=1;controls.append(changed)
changed=copy.deepcopy(regrouped);changed["records"][0]["ids"][0]=512;controls.append(changed)
changed=copy.deepcopy(regrouped);changed["records"][0]["layer"]=1;controls.append(changed)
changed=copy.deepcopy(regrouped);changed["selected_indices"]-=1;controls.append(changed)
changed=copy.deepcopy(regrouped);changed["all_existing_downloads_and_synchronizations_returned"]=False;controls.append(changed)
for changed in controls:
    try:require_same_tokens(ordinary,changed)
    except ValueError:pass
    else:raise AssertionError("Invalid native route evidence accepted")
print("Native route review: two regrouping/prefix controls and five refusal controls passed; no console calls")
