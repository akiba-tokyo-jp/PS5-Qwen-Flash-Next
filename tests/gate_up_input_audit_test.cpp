// SPDX-License-Identifier: MIT
#include "gate_up_input_audit.h"
struct Fixture {
    ggml_tensor input{},IDs{},up{},gate{};
    Fixture(){input.type=GGML_TYPE_F32;input.ne[0]=2560;input.ne[1]=1;input.ne[2]=30;
        IDs.type=GGML_TYPE_I32;IDs.ne[0]=10;IDs.ne[1]=30;
        up.op=gate.op=GGML_OP_MUL_MAT_ID;up.src[1]=gate.src[1]=&input;up.src[2]=gate.src[2]=&IDs;}
};
int main(){
    Fixture f;qwen_app::GateUpInputAudit valid;
    for(int i=0;i<48;++i)valid.observe(&f.up,&f.gate,i);
    auto s=valid.snapshot();if(s.calls!=48||s.layer_masks[2]!=((std::uint64_t(1)<<48)-1)||s.input_mismatches||s.ID_mismatches)return 1;
    Fixture changed;changed.gate.src[1]=&f.input;qwen_app::GateUpInputAudit mismatch;
    mismatch.observe(&changed.up,&changed.gate,0);if(mismatch.snapshot().input_mismatches!=1)return 2;
    changed=Fixture{};changed.up.src[1]=changed.gate.src[1]=&changed.input;changed.up.src[2]=&changed.IDs;changed.gate.src[2]=&f.IDs;
    qwen_app::GateUpInputAudit IDs;IDs.observe(&changed.up,&changed.gate,0);if(IDs.snapshot().ID_mismatches!=1)return 3;
    Fixture half;half.input.type=GGML_TYPE_F16;qwen_app::GateUpInputAudit geometry;
    geometry.observe(&half.up,&half.gate,0);if(geometry.snapshot().geometry_failures!=1)return 4;
    qwen_app::GateUpInputAudit invalid;invalid.observe(nullptr,&f.gate,0);invalid.observe(&f.up,&f.gate,48);
    if(invalid.snapshot().unsupported!=2)return 5;
    return 0;
}
