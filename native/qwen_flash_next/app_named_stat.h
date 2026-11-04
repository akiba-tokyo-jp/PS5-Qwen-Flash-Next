/* SPDX-License-Identifier: MIT
 * Native title namespaces permit open/fstat while lstat can return EPERM.
 * Bind a fresh no-follow descriptor, matching the successful main SELF reader.
 */
#ifndef QWEN_APP_NAMED_STAT_H
#define QWEN_APP_NAMED_STAT_H
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
static int qwen_app_named_stat(const char*path,struct stat*value){
    int fd=open(path,O_RDONLY|O_NOFOLLOW);
    if(fd<0)return -1;
    int status=fstat(fd,value),saved=errno;
    int closed=close(fd);
    if(status){errno=saved;return -1;}
    return closed?-1:0;
}
#endif
