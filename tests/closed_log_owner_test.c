/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#define off_t int64_t
struct stamp {int64_t tv_sec,tv_nsec;};
struct stat {uint64_t st_dev,st_ino;unsigned st_mode,st_uid,st_gid,st_nlink,st_flags;int64_t st_size;struct stamp st_mtim,st_ctim;};
struct ClosedLog {const char*path;const char*alias;unsigned long long bytes;};
#define CASE_CLOSED_LOG_COUNT 17u
#define S_ISREG(mode) (((mode)&0170000)==0100000)
static struct stat files[17];static struct ClosedLog case_closed_logs[17];static char physical[17][12],alias[17][12];
static unsigned scenario,changes;
static int unchanged(const struct stat*a,const struct stat*b){return !memcmp(a,b,sizeof(*a));}
static int report(const char*fmt,...){(void)fmt;return 1;}
static int qwen_launch_headroom(void*ctx){(void)ctx;return scenario!=4;}
static int mock_lstat(const char*path,struct stat*out){
    unsigned i=99;char role=0;if(sscanf(path,"/%c/%u",&role,&i)!=2||i>=17)return -1;
    *out=files[i];if(role=='A')out->st_dev=2;
    if(scenario==3&&i==3&&role=='A')++out->st_ino;
    if(scenario==7&&i==3&&role=='A'&&changes)++out->st_ctim.tv_nsec;
    return 0;
}
static int mock_chown(const char*path,unsigned uid,unsigned gid){
    unsigned i=99;if(sscanf(path,"/P/%u",&i)!=1||i>=17||uid||gid)return -1;
    ++changes;if(scenario==5&&i==3){errno=EACCES;return -1;}
    files[i].st_uid=uid;++files[i].st_ctim.tv_sec;
    if(scenario==6&&i==3)++files[i].st_mtim.tv_sec;
    return 0;
}
#define lstat mock_lstat
#define chown mock_chown
#include "closed_log_owner.h"
int main(void){
    for(scenario=0;scenario<8;++scenario){
        memset(files,0,sizeof(files));changes=0;
        for(unsigned i=0;i<17;++i){
            files[i].st_dev=1;files[i].st_ino=i+1;files[i].st_mode=0100600;files[i].st_uid=1;files[i].st_nlink=1;files[i].st_size=64;
            snprintf(physical[i],sizeof(physical[i]),"/P/%u",i);snprintf(alias[i],sizeof(alias[i]),"/A/%u",i);
            case_closed_logs[i]=(struct ClosedLog){physical[i],alias[i],64};
        }
        if(scenario==1)files[3].st_uid=0;
        if(scenario==2)files[3].st_mode=0100644;
        int calls=0,ok=case_retire_completed_images(&calls);
        if(scenario==0){
            if(!ok||calls!=17||changes!=17)return 10;
            for(unsigned i=0;i<17;++i)if(files[i].st_uid||files[i].st_mode!=0100600||files[i].st_size!=64||files[i].st_mtim.tv_sec)return 11;
        }else{
            if(ok)return 12;
            if(scenario<=4&&(calls||changes))return 13;
            if(scenario>=5&&(calls!=4||changes!=4))return 14;
        }
    }
    puts("{\"completed\":true,\"cases\":8,\"actual_header_control_flow_tested\":true,\"OS_objects_created\":0}");return 0;
}
