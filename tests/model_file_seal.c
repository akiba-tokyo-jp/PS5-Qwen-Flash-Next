/* SPDX-License-Identifier: MIT */
#define QWEN_SEAL_HOST_STUBS
#define main seal_native_entry
#include "../native/qwen_flash_next/model_file_seal.c"
#undef main
static struct stat files[sizeof(expected_files)/sizeof(expected_files[0])];
static int chmod_calls,stat_calls,scenario;
static int seal_fake_open(const char *path,int flags,...) {
    (void)flags;if(!strcmp(path,SEAL_ROOT))return 900;
    for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!strcmp(path,expected_files[i].path))return (int)i+10;
    return -1;
}
static int seal_fake_fstat(int fd,struct stat *out) {
    if(fd==900){memset(out,0,sizeof(*out));out->st_mode=0040755;out->st_ino=1;return 0;}
    if(fd<10||(unsigned)(fd-10)>=sizeof(files)/sizeof(files[0]))return -1;
    *out=files[fd-10];++stat_calls;
    if(scenario==4&&stat_calls>(int)(sizeof(files)/sizeof(files[0]))&&fd==10)++out->st_ino;
    return 0;
}
static int seal_fake_fchmod(int fd,unsigned mode) {
    ++chmod_calls;if(scenario==5)return -1;
    files[fd-10].st_mode=0100000|mode;return 0;
}
static int seal_fake_close(int fd){(void)fd;return 0;}
int main(void) {
    for(scenario=0;scenario<7;++scenario){
        chmod_calls=stat_calls=0;memset(files,0,sizeof(files));
        for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);++i){
            files[i].st_dev=7;files[i].st_ino=i+10;files[i].st_size=(int64_t)expected_files[i].bytes;
            files[i].st_mode=0100777;files[i].st_mtim.tv_sec=4;
        }
        if(scenario==1)files[0].st_uid=1;
        if(scenario==2)files[0].st_mode=0100666;
        if(scenario==3)--files[0].st_size;
        if(scenario==6)for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);++i)files[i].st_mode=0100644;
        FILE *log=tmpfile();if(!log)return 1;int ok=seal_files(log);fclose(log);
        if(scenario==0){if(!ok||chmod_calls!=(int)(sizeof(files)/sizeof(files[0])))return 2;}
        else if(scenario==6){if(!ok||chmod_calls)return 3;}
        else if(ok||chmod_calls!=(scenario==5?1:0))return 4;
    }
    puts("Model file sealing: seven scope and failure checks passed");return 0;
}
