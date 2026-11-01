# SPDX-License-Identifier: MIT
"""Keep the failed copy-callback rebinding prototype out of new model launches."""
REASON = (
    'Resident slot-map copy-callback rebinding has no completed full-model '
    'qualification: case57500 stopped responding during decode. New model '
    'builds and launches are disabled. Preserve the live case and exact9824 '
    'rollback; do not replay its launch or assume GPU completion.'
)

def require_qualified_slot_map_model(native):
    fixture=native.get('resident_slot_map_fixture',{}).get('scope',{})
    if fixture.get('model_loads')==0 and fixture.get('requests')==0:
        return
    if 'resident_slot_maps' in native or 'resident_slot_maps_normal' in native:
        raise ValueError(REASON)
