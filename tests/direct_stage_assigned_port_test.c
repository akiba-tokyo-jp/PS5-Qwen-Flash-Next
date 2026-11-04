/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned socklen_t;
struct sockaddr {unsigned char bytes[16];};
struct sockaddr_in {unsigned char sin_len,sin_family;uint16_t sin_port;struct {uint32_t s_addr;}sin_addr;unsigned char pad[8];};
#define AF_INET 2
#define ntohs(x) (x)
#define DIRECT_STAGE_CONSOLE_IP 1234u
#define CASE_ASSIGNED_PORT_HOST_ABI 1
static unsigned scenario,bind_calls;static char output[1100];
static int report(const char*format,...){va_list args;va_start(args,format);int rc=vsnprintf(output,sizeof(output),format,args);va_end(args);return rc>0;}
static int bind(int fd,const struct sockaddr*address,socklen_t bytes){
    (void)fd;(void)address;(void)bytes;++bind_calls;return scenario==1?-1:0;
}
static int getsockname(int fd,struct sockaddr*address,socklen_t*bytes){
    (void)fd;struct sockaddr_in value={0};value.sin_len=sizeof(value);value.sin_family=AF_INET;value.sin_addr.s_addr=DIRECT_STAGE_CONSOLE_IP;value.sin_port=54321;
    if(scenario==2)return -1;if(scenario==3)--*bytes;if(scenario==4)++value.sin_family;if(scenario==5)++value.sin_addr.s_addr;if(scenario==6)value.sin_port=80;
    memcpy(address,&value,sizeof(value));return 0;
}
#include "direct_stage_assigned_port.h"
int main(void){
    for(scenario=0;scenario<10;++scenario){
        bind_calls=0;direct_stage_assigned_port=0;struct sockaddr_in value={0};value.sin_family=AF_INET;value.sin_addr.s_addr=DIRECT_STAGE_CONSOLE_IP;
        if(scenario==7)value.sin_port=5555;if(scenario==8)++value.sin_family;
        int rc=direct_stage_bind_assigned(1,(const struct sockaddr*)&value,sizeof(value)-(scenario==9));
        if(!scenario){
            if(rc||direct_stage_assigned_port!=54321||bind_calls!=1)return 10;
            if(!direct_stage_assigned_report("DIRECT_STAGE_READY bytes=%u",32u)||strcmp(output,"DIRECT_STAGE_READY bytes=32 port=54321"))return 11;
            if(!direct_stage_assigned_report("ordinary %u",42u)||strcmp(output,"ordinary 42"))return 12;
        }else if(!rc||direct_stage_assigned_port||(scenario>=7?bind_calls!=0:bind_calls!=1))return 13;
    }
    puts("{\"completed\":true,\"cases\":10,\"OS_objects\":0,\"actual_adapter_tested\":true}");return 0;
}
