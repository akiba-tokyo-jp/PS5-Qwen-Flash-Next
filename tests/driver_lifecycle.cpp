// SPDX-License-Identifier: MIT
#include "driver_lifecycle.h"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using qwen_app::DriverLifecycle;
namespace {
DriverLifecycle * current;
int mode, agc_calls, prepares, waits, retires, retains, checkpoints;
std::vector<std::string> stages;
int log_open(const char * path) { return std::string(path)=="own.log" && mode!=1 ? 0 : -1; }
std::int32_t agc(std::uint32_t value) { if(value!=8)throw std::runtime_error("AGC version changed");++agc_calls;return mode==2?-1:0; }
bool platform() {
    const auto result=current->initialize_agc(mode==3?7:8,agc);
    if(mode==4)current->initialize_agc(8,agc);
    return result==0;
}
int prepare() {++prepares;return mode==5?-1:0;}
int owner_ready() {return 1;}
void owner(ps5_ai_arena_stats * out) {*out={};if(mode==6)out->physical_owned=1;}
int kick(ps5_ai_arena_kick_stats * out) {
    *out={};out->log_healthy=1;
    if(waits) {*out={5,5,1,1,0,0,0,0,1};}
    if(mode==8)out->pending=1;
    if(mode==9)out->completed_epoch=4;
    if(mode==10)out->log_healthy=0;
    if(mode==11)return 1;
    return 0;
}
int retire(std::uint64_t epoch) {if(epoch!=5)throw std::runtime_error("Wrong retirement epoch");++retires;return mode==12?0:1;}
bool checkpoint() {++checkpoints;return true;}
void retain() {++retains;}
int wait(std::uintptr_t device) {if(device!=99)throw std::runtime_error("Wrong device");++waits;return mode==7?-1:0;}
void stage(const char * value) {stages.emplace_back(value);}
void check(bool value) {if(!value)throw std::runtime_error("Native lifecycle API-stub contract failed");}
template<class Call> void refused(Call operation) {bool caught=false;try{operation();}catch(const std::runtime_error&){caught=true;}check(caught);}
qwen_app::DriverOperations ops{log_open,platform,prepare,owner_ready,owner,kick,retire,checkpoint,retain,wait,stage};
void reset(int value) {mode=value;agc_calls=prepares=waits=retires=retains=checkpoints=0;stages.clear();}
}
int main() {
    try {
        for(int value=1;value<=6;++value) {
            reset(value);DriverLifecycle driver(ops);current=&driver;
            refused([&]{driver.initialize("own.log");});check(driver.faulted()&&retains==1&&!retires&&!waits);
            if(value==1)check(!agc_calls&&!prepares);
            if(value==3)check(!agc_calls);
            if(value==4)check(agc_calls==1);
            refused([&]{driver.initialize("own.log");});check(retains==1);
        }
        reset(0);DriverLifecycle no_device(ops);current=&no_device;no_device.initialize("own.log");
        no_device.begin_work();no_device.complete_work();check(no_device.ready()&&!waits&&!retires);
        check(std::find(stages.begin(),stages.end(),"native_driver_before_own_journal AGC_not_started=1")<
              std::find(stages.begin(),stages.end(),"native_driver_before_explicit_AGC8 hard_timeout=not_established"));
        for(int value: {0,7,8,9,10,11,12}) {
            reset(value);DriverLifecycle driver(ops);current=&driver;driver.initialize("own.log");
            driver.begin_work();driver.register_device(99);driver.before_submit();driver.after_submit();driver.before_submit();driver.after_submit();
            if(!value) {
                driver.checkpoint_work();check(driver.ready()&&waits==1&&retires==1&&!retains);
                driver.before_submit();driver.after_submit();driver.complete_work();
                check(driver.ready()&&waits==2&&retires==2&&!retains);
            }
            else {
                refused([&]{driver.complete_work();});check(driver.faulted()&&retains==1);
                check(retires==(value==12?1:0));refused([&]{driver.begin_work();});check(retains==1);
            }
        }
        reset(0);DriverLifecycle overlap(ops);current=&overlap;overlap.initialize("own.log");overlap.begin_work();
        refused([&]{overlap.begin_work();});check(overlap.faulted()&&!retires);
        reset(0);DriverLifecycle wrong_thread(ops);current=&wrong_thread;wrong_thread.initialize("own.log");wrong_thread.begin_work();
        std::thread other([&]{refused([&]{wrong_thread.complete_work();});});other.join();check(wrong_thread.faulted()&&!retires&&!waits);
        reset(0);DriverLifecycle no_lease(ops);current=&no_lease;no_lease.initialize("own.log");
        refused([&]{no_lease.before_submit();});check(no_lease.faulted()&&!retires);
        reset(0);DriverLifecycle busy(ops);current=&busy;busy.initialize("own.log");busy.begin_work();busy.register_device(99);
        std::atomic<bool> inside{false},leave{false};
        std::thread submitting([&]{busy.before_submit();inside.store(true);while(!leave.load())std::this_thread::yield();busy.after_submit();});
        while(!inside.load())std::this_thread::yield();
        refused([&]{busy.complete_work();});leave.store(true);submitting.join();check(busy.faulted()&&!waits&&!retires);
        std::cout<<"Own log before sole AGC8, exact empty owner, producer exclusion, device idle plus matching epoch, and retention on every failed boundary passed; API stubs only\n";
    } catch(const std::exception & error) {std::cerr<<error.what()<<'\n';return 1;}
}
