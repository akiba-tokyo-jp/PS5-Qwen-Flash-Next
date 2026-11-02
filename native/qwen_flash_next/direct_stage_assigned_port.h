/* SPDX-License-Identifier: MIT
 * Adapt only bind/READY reporting; keep the qualified receiver unchanged.
 */
#ifndef CASE_ASSIGNED_PORT_HOST_ABI
#include <sys/socket.h>
#include <netinet/in.h>
#endif
#include <stdarg.h>
#include <stdio.h>
static unsigned direct_stage_assigned_port;
static int direct_stage_bind_assigned(int fd,const struct sockaddr*address,socklen_t bytes){
    if(bytes!=sizeof(struct sockaddr_in)||!address)return -1;
    struct sockaddr_in local;memcpy(&local,address,sizeof(local));
    if(local.sin_family!=AF_INET||local.sin_port||local.sin_addr.s_addr!=DIRECT_STAGE_CONSOLE_IP)return -1;
    const int rc=bind(fd,(const struct sockaddr*)&local,sizeof(local));if(rc)return rc;
    socklen_t size=sizeof(local);
    if(getsockname(fd,(struct sockaddr*)&local,&size)||size!=sizeof(local)||local.sin_family!=AF_INET||
       local.sin_addr.s_addr!=DIRECT_STAGE_CONSOLE_IP||ntohs(local.sin_port)<1024)return -1;
    direct_stage_assigned_port=ntohs(local.sin_port);return 0;
}
static int direct_stage_assigned_report(const char*format,...){
    char line[1024];va_list args;va_start(args,format);int count=vsnprintf(line,sizeof(line),format,args);va_end(args);
    if(count<0||count>=(int)sizeof(line))return 0;
    if(!strncmp(line,"DIRECT_STAGE_READY ",19)){
        if(direct_stage_assigned_port<1024||direct_stage_assigned_port>65535)return 0;
        return report("%s port=%u",line,direct_stage_assigned_port);
    }
    return report("%s",line);
}
#define bind direct_stage_bind_assigned
#define report direct_stage_assigned_report
