// SPDX-License-Identifier: MIT
#include "limit_margin_probe.h"
#include <iostream>
void need(bool value){if(!value)throw std::runtime_error("Limit margin invariant failed");}
int main()try{
    qwen_app::LimitMarginProbe p;need(p.required(1137,898,206,256)==1154);
    p.phase(1);need(p.required(1137,898,206,256)==1104);
    need(p.required(1090,898,206,256)==1026);
    need(p.required(1010,898,206,256)==962);
    need(p.required(950,898,206,256)==898);
    need(p.required(897,898,206,256)>897);
    need(p.required(5000,898,206,256)==898);
    p.phase(2);need(p.required(950,898,206,64,41)==939);
    need(p.required(938,898,206,64,41)>938);
    p.phase(3);need(p.required(900,898,206,64)==898);
    bool refused=false;try{p.phase(2);}catch(const std::logic_error&){refused=true;}need(refused);
    std::uint64_t stats[22]{};p.snapshot(stats);need(stats[0]==3&&stats[1]==0&&stats[2]==6);
    std::cout<<"PASS: unchanged inactive policy,monotone padding steps,OS minimum,transient pricing,phase ordering and statistics\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
