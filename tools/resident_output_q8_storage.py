# SPDX-License-Identifier: MIT
"""Storage admission for exactly two new bounded parts and their metadata."""
from expert_q4 import require
def require_new_output_storage(capacity,files):
    require(capacity['capture_completion_proven']and len(files)==3,'Completed capacity and exactly three new assets required')
    sizes=[r['local']['bytes']for r in files]
    require(all(type(n)is int and n>0 for n in sizes)and sizes[0]==512<<20 and sizes[1]==138559648 and sizes[2]<=1<<20,
        'Only the explicit Q8 output split and bounded metadata are admitted')
    # Four separately bounded 64-MiB program transfers cover the candidate,
    # retained control, restoration and a temporary artifact. Existing model
    # data is already present; this function cannot admit an original transfer.
    reserve=4*(64<<20);required=sum(sizes)+reserve
    require(capacity['free_bytes_lower_bound']>=required,'New Q8 assets cannot retain bounded program-transfer storage')
    return dict(new_payload_bytes=sum(sizes),program_transfer_reserve_bytes=reserve,required_free_bytes=required,
        original_model_transfer_policy_used=False)
