/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
struct stat {uint64_t st_dev,st_ino;int64_t st_size;unsigned st_mode,st_uid,st_gid;
    struct {int64_t tv_sec,tv_nsec;} st_mtim;};
#define O_RDONLY 0
#define O_NONBLOCK 1
#define O_NOFOLLOW 2
#define O_DIRECTORY 4
#define O_WRONLY 8
#define O_CREAT 16
#define O_EXCL 32
#define S_ISREG(m) (((m)&0170000)==0100000)
#define S_ISDIR(m) (((m)&0170000)==0040000)
static int seal_fake_open(const char *,int,...);
static int seal_fake_fstat(int,struct stat *);
static int seal_fake_fchmod(int,unsigned);
static int seal_fake_close(int);
#define open seal_fake_open
#define fstat seal_fake_fstat
#define fchmod seal_fake_fchmod
#define close seal_fake_close
#define getuid() 1u
#define geteuid() 0u
#define fsync(fd) 0
#define fdopen(fd,mode) tmpfile()
#define fileno(file) 0
