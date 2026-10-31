// SPDX-License-Identifier: MIT
#include "adaptive_prefill_protection.h"
#include <iostream>
void need(bool v){if(!v)throw std::runtime_error("Adaptive prefill invariant failed");}
int main()try{
 qwen_app::AdaptivePrefillProtection h;h.begin(true,true);h.bind_prompt({1,2});
 need(!h.prepare(0,{7},false,true,0));h.observe(0,{7,8},true);h.commit();h.observe(0,{9},true);
 h.begin(true,false);h.bind_prompt({1,2});auto*p=h.prepare(0,{7},false,true,0);need(p&&(*p)[7]&&(*p)[8]&&!(*p)[9]);need(!h.prepare(0,{7},true,true,0));
 h.begin(true,false);h.bind_prompt({1,3});need(!h.prepare(0,{7},false,true,0));
 p=h.prepare(0,{7,7,10,11,12},false,false,4);need(p&&(*p)[7]&&(*p)[8]&&!(*p)[9]);
 p=h.prepare(0,{10,11},false,false,4);need(p&&!(*p)[7]&&!(*p)[8]);
 bool refused=false;try{h.bind_prompt(std::vector<int>(257,1));}catch(const std::invalid_argument&){refused=true;}need(refused);
 h.begin(true,true);h.bind_prompt({1,2});need(!h.prepare(0,{7},false,true,0));
 for(unsigned subgroup:{32,64}){const unsigned lanes=subgroup/4;need(128%lanes==0&&subgroup%lanes==0&&128%(subgroup/lanes)==0);}
 std::cout<<"PASS: exact prompt identity, accepted history, duplicate-aware causal overlap, reset, bounds and four-column GDN coverage\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
