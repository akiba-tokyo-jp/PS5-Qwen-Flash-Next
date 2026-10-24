/* SPDX-License-Identifier: MIT */
#pragma once
#include <sys/types.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
struct stat { unsigned st_mode,st_uid,st_gid; unsigned long long st_nlink; long long st_size; };
#define S_IFMT 0170000
#define S_IFDIR 0040000
#define S_IFREG 0100000
#define S_IFLNK 0120000
#define S_ISDIR(m) (((m)&S_IFMT)==S_IFDIR)
#define S_ISREG(m) (((m)&S_IFMT)==S_IFREG)
#define O_RDONLY 0
#define O_WRONLY 1
#define O_CREAT 2
#define O_EXCL 4
#define O_NOFOLLOW 8
#define O_DIRECTORY 16
typedef long long md_ssize;
#define ssize_t md_ssize
int md_open(const char*,int,...);
md_ssize md_read(int,void*,size_t);
int md_close(int);
int md_lstat(const char*,struct stat*);
int md_fstat(int,struct stat*);
int md_chown(const char*,unsigned,unsigned);
int md_chmod(const char*,unsigned);
int md_fchmod(int,unsigned);
unsigned md_getuid(void);
unsigned md_geteuid(void);
int md_fsync(int);
FILE *md_fdopen(int,const char*);
int md_fileno(FILE*);
#define open md_open
#define read md_read
#define close md_close
#define lstat md_lstat
#define fstat md_fstat
#define chown md_chown
#define chmod md_chmod
#define fchmod md_fchmod
#define getuid md_getuid
#define geteuid md_geteuid
#define fsync md_fsync
#ifdef fdopen
#undef fdopen
#endif
#define fdopen md_fdopen
#ifdef fileno
#undef fileno
#endif
#define fileno md_fileno
