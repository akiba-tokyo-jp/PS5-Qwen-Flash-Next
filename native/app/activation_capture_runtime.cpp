// SPDX-License-Identifier: MIT
#include "activation_capture.h"
#include "activation_capture_runtime.h"
#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <new>
#include <ps5platform/heap.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
void __real_ggml_backend_sched_set_eval_callback(ggml_backend_sched_t,ggml_backend_sched_eval_callback,void*);
ggml_status __real_ggml_backend_sched_graph_compute_async(ggml_backend_sched_t,ggml_cgraph*);
}
namespace {
// Do not touch the64KiB diagnostic state during pre-main initialization.
// It belongs to the tracked heap only after ordinary context admission.
qwen_app::ActivationCapture*capture=nullptr;
void*scratch=nullptr;int output=-1;
std::string path;std::thread::id producer;
bool attempted=false,prepare_failed=false;
std::uint64_t written=0;
ggml_backend_sched_t observed=nullptr;
ggml_backend_sched_eval_callback original_callback=nullptr;void*original_data=nullptr;
void need(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
void write(const void*data,std::size_t bytes){
    // A partial unaligned Direct write is a known diagnostic failure. Do not
    // issue a second native call with invalid Direct alignment or replay it.
    unsigned interruptions=0;ssize_t actual;
    do{actual=::write(output,data,bytes);}while(actual<0&&errno==EINTR&&++interruptions<8);
    need(actual==ssize_t(bytes),"Calibration Direct write did not complete");written+=bytes;
}
bool callback(ggml_tensor*t,bool ask,void*){return capture?capture->evaluate(t,ask):!ask;}
}
extern "C" void __wrap_ggml_backend_sched_set_eval_callback(ggml_backend_sched_t sched,ggml_backend_sched_eval_callback cb,void*data){
    observed=sched;original_callback=cb;original_data=data;
    __real_ggml_backend_sched_set_eval_callback(sched,cb,data);
}
extern "C" ggml_status __wrap_ggml_backend_sched_graph_compute_async(ggml_backend_sched_t sched,ggml_cgraph*graph){
    if(!capture||!capture->active())return __real_ggml_backend_sched_graph_compute_async(sched,graph);
    if(observed!=sched||original_callback||producer!=std::this_thread::get_id()){
        capture->fail("Calibration declined an unknown scheduler callback or producer");
        return __real_ggml_backend_sched_graph_compute_async(sched,graph);
    }
    try{capture->begin_compute();}catch(...){capture->fail("Calibration compute bound exceeded");return __real_ggml_backend_sched_graph_compute_async(sched,graph);}
    __real_ggml_backend_sched_set_eval_callback(sched,callback,nullptr);
    ggml_status status;
    try{status=__real_ggml_backend_sched_graph_compute_async(sched,graph);}
    catch(...){__real_ggml_backend_sched_set_eval_callback(sched,original_callback,original_data);throw;}
    __real_ggml_backend_sched_set_eval_callback(sched,original_callback,original_data);
    if(status==GGML_STATUS_SUCCESS)capture->end_compute();else capture->fail("Original graph did not positively complete");
    return status;
}
namespace qwen_app {
void prepare_activation_capture(const std::string&name,const nlohmann::json&binding){
    try{
    need(!attempted,"Only one calibration preparation is allowed");attempted=true;
    capture=new(std::nothrow) ActivationCapture;
    need(capture&&ps5_heap_owns(capture),"Calibration state must use the tracked CPU heap");
    need(path.empty()&&name.rfind("/app0/qwen-runtime/plan-",0)==0&&name.size()<240,"One fresh bounded calibration path required");
    path=name;producer=std::this_thread::get_id();
    need(!posix_memalign(&scratch,ActivationCapture::alignment,ActivationCapture::scratch_bytes)&&scratch&&ps5_heap_owns(scratch),
         "Tracked4MiB calibration scratch unavailable");
    output=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0644);
    need(output>=0&&(fcntl(output,F_GETFL)&O_DIRECT)&&fchmod(output,0644)==0,"Fresh readable Direct calibration sink unavailable");
    const auto json=binding.dump();need(json.size()<=ActivationCapture::alignment-128,"Calibration binding exceeds fixed header");
    std::memset(scratch,0,ActivationCapture::alignment);auto*header=static_cast<unsigned char*>(scratch);
    std::memcpy(header,"QWENACT1",8);const std::uint32_t version=1,size=ActivationCapture::alignment,json_bytes=std::uint32_t(json.size());
    const std::uint64_t limit=ActivationCapture::limit_bytes;
    std::memcpy(header+8,&version,4);std::memcpy(header+12,&size,4);std::memcpy(header+16,&limit,8);
    std::memcpy(header+24,&json_bytes,4);std::memcpy(header+128,json.data(),json.size());
    write(scratch,ActivationCapture::alignment);
    capture->initialize(scratch,ggml_backend_tensor_get,write);
    }catch(...){prepare_failed=true;if(capture)capture->fail("Returned calibration preparation failed; model inference continues");}
}
void activation_capture_request(unsigned ordinal){if(capture)capture->request(ordinal);}
nlohmann::json finish_activation_capture(){
    if(!capture)return {{"schema","ps5-qwen-real-activation-capture-v1"},{"completed",false},{"diagnostic_failed",true},
        {"error","Calibration state allocation failed"},{"path",path},{"bytes",0},{"sha256",""},{"evaluations",0},{"records",0},
        {"all_file_calls_returned",true},{"full_native_SHA256_and_EOF_verified",false},{"scratch_retained_until_ordinary_close",false}};
    capture->request(1);bool sealed=false,retained=false;std::string digest;
    try{
        need(output>=0&&scratch&&written==capture->bytes()&&!capture->failed(),"Calibration stream incomplete");
        struct stat before{};need(fsync(output)==0&&fstat(output,&before)==0&&std::uint64_t(before.st_size)==written,"Calibration sync or size failed");
        const int closing=output;output=-1;retained=close(closing)!=0;need(!retained,"Calibration writer close failed");
        output=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);need(output>=0,"Calibration readback open failed");
        sha256_t hash;sha256_init(&hash);
        for(std::uint64_t offset=0;offset<written;){
            const auto bytes=std::min<std::uint64_t>(ActivationCapture::scratch_bytes,written-offset);
            need(pread(output,scratch,bytes,off_t(offset))==ssize_t(bytes),"Calibration full readback failed");
            sha256_update(&hash,static_cast<unsigned char*>(scratch),bytes);offset+=bytes;
        }
        need(pread(output,scratch,ActivationCapture::alignment,off_t(written))==0,"Calibration EOF differs");
        struct stat after{};need(fstat(output,&after)==0&&before.st_dev==after.st_dev&&before.st_ino==after.st_ino&&
            before.st_size==after.st_size&&before.st_mtim.tv_sec==after.st_mtim.tv_sec&&before.st_mtim.tv_nsec==after.st_mtim.tv_nsec,
            "Calibration file identity changed");
        const int reading=output;output=-1;retained=close(reading)!=0;need(!retained,"Calibration readback close failed");
        unsigned char bytes[32];sha256_final(&hash,bytes);for(auto value:bytes){digest+="0123456789abcdef"[value>>4];digest+="0123456789abcdef"[value&15];}
        sealed=true;
    }catch(...){capture->fail("Calibration stream did not seal with full SHA256 and EOF");}
    if(output>=0){const int fd=output;output=-1;if(close(fd))retained=true;}
    if(!retained&&scratch){free(scratch);scratch=nullptr;}
    const auto report=nlohmann::json{{"schema","ps5-qwen-real-activation-capture-v1"},{"completed",sealed},{"diagnostic_failed",capture->failed()},
        {"error",capture->error()},{"path",path},{"bytes",written},{"sha256",digest},{"evaluations",capture->evaluations()},
        {"records",capture->records()},{"readback_bytes",capture->readback_bytes()},{"scratch_bytes",ActivationCapture::scratch_bytes},
        {"scratch_retained_until_ordinary_close",retained},{"only_first_request_captured",true},{"timings_usable_for_performance",false},
        {"preparation_failed",prepare_failed},{"all_file_calls_returned",true},{"full_native_SHA256_and_EOF_verified",sealed}};
    delete capture;capture=nullptr;return report;
}
}
