// SPDX-License-Identifier: MIT
#include "mtp_target_hidden_capture.h"
#include <cassert>
#include <limits>
using Capture=qwen_app::MtpTargetHiddenCapture<4>;
struct Context {Capture::Hidden first{1,2,3,4},last{5,6,7,8};};
Capture*observer=nullptr;
unsigned gets=0,synchronizations=0;
float*get(void*pointer,int index){
    ++gets;observer->original_synchronize_returned(pointer);
    auto&context=*static_cast<Context*>(pointer);return index==0?context.first.data():context.last.data();
}
void synchronize(void*context){++synchronizations;observer->original_synchronize_returned(context);}
int main(){
    Context target,auxiliary;int target_batch=0,other_batch=0;
    Capture capture({get,synchronize});observer=&capture;
    capture.batch_created(&target_batch,&target);capture.batch_created(&other_batch,&auxiliary);capture.bind_target(&target);
    capture.token_added(&target_batch,29);capture.original_process_returned(&target,&target_batch,0);
    capture.original_synchronize_returned(&target);
    assert(capture.valid()&&capture.last_width()==30&&capture.serial()==1&&capture.last()==target.last&&gets==1&&synchronizations==1);
    capture.batch_cleared(&target_batch);capture.token_added(&target_batch,0);capture.token_added(&target_batch,1);
    capture.original_process_returned(&target,&target_batch,0);capture.original_synchronize_returned(&target);
    const auto first=target.first,last=target.last;target.first.fill(-1);target.last.fill(-2);
    assert(capture.valid()&&capture.last_width()==2&&capture.serial()==2&&capture.first()==first&&capture.last()==last&&gets==3);
    // A rejected pair may restore compact state and then consume the pending
    // token normally. The actual single-token completion replaces both rows.
    capture.batch_cleared(&target_batch);capture.token_added(&target_batch,0);target.last={9,10,11,12};
    capture.original_process_returned(&target,&target_batch,0);capture.original_synchronize_returned(&target);
    assert(capture.valid()&&capture.serial()==3&&capture.last_width()==1&&capture.first()==target.last&&capture.last()==target.last);
    capture.token_added(&other_batch,0);capture.original_process_returned(&auxiliary,&other_batch,0);
    capture.original_synchronize_returned(&auxiliary);assert(capture.serial()==3&&gets==4);
    capture.batch_freed(&target_batch);capture.original_process_returned(&target,&target_batch,0);assert(capture.failed());
    Capture nonfinite({get,synchronize});observer=&nonfinite;nonfinite.batch_created(&target_batch,&target);nonfinite.bind_target(&target);
    nonfinite.token_added(&target_batch,0);target.last[0]=std::numeric_limits<float>::quiet_NaN();
    nonfinite.original_process_returned(&target,&target_batch,0);nonfinite.original_synchronize_returned(&target);assert(!nonfinite.valid()&&nonfinite.failed());
}
