/* SPDX-License-Identifier: MIT */
#pragma once
#include <sys/types.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#define O_WRONLY 1
#define O_CREAT 2
#define O_EXCL 4
#define O_NOFOLLOW 8
int hp_clock_gettime(int,struct timespec*);
int hp_open(const char*,int,...);
int hp_close(int);
unsigned hp_getuid(void);
unsigned hp_geteuid(void);
int hp_fsync(int);
FILE *hp_fdopen(int,const char*);
int hp_fileno(FILE*);
#define clock_gettime hp_clock_gettime
#define open hp_open
#define close hp_close
#define getuid hp_getuid
#define geteuid hp_geteuid
#define fsync hp_fsync
#ifdef fdopen
#undef fdopen
#endif
#define fdopen hp_fdopen
#ifdef fileno
#undef fileno
#endif
#define fileno hp_fileno
