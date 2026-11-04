/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0x100
#endif
static int opened,stated,closed,open_result,stat_result,close_result;
static int mock_open(const char*path,int flags){
    assert(path&&flags==(O_RDONLY|O_NOFOLLOW));++opened;
    if(open_result<0)errno=EACCES;return open_result;
}
static int mock_stat(int fd,struct stat*value){
    assert(fd==41);++stated;value->st_size=7123;
    if(stat_result)errno=EIO;return stat_result;
}
static int mock_close(int fd){assert(fd==41);++closed;if(close_result)errno=EBADF;return close_result;}
#define open mock_open
#define fstat mock_stat
#define close mock_close
#include "app_named_stat.h"
static void reset(void){opened=stated=closed=0;open_result=41;stat_result=close_result=0;errno=0;}
int main(void){
    struct stat value;
    reset();assert(!qwen_app_named_stat("SELF",&value)&&value.st_size==7123&&opened==1&&stated==1&&closed==1);
    reset();open_result=-1;assert(qwen_app_named_stat("SELF",&value)==-1&&errno==EACCES&&opened==1&&!stated&&!closed);
    reset();stat_result=-1;assert(qwen_app_named_stat("SELF",&value)==-1&&errno==EIO&&stated==1&&closed==1);
    reset();close_result=-1;assert(qwen_app_named_stat("SELF",&value)==-1&&errno==EBADF&&closed==1);
    reset();stat_result=close_result=-1;assert(qwen_app_named_stat("SELF",&value)==-1&&errno==EIO&&closed==1);
    return 0;
}
