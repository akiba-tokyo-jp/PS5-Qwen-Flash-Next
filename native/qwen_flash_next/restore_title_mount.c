/* SPDX-License-Identifier: GPL-3.0-or-later
 * Restore the existing registered title's volatile data-directory nullfs mount.
 * Reuse the unchanged launcher's measured ABI, boot/service, SHA and idle guards.
 * No unmount, system-volume remount, registration, title launch or GPU call.
 */
#define MOSS_RUNTIME_PREP 1
#include "controller.c"

static int empty_underlying_mountpoint(void) {
    struct stat st;struct statfs fs;
    if(lstat(MOUNT,&st)||!S_ISDIR(st.st_mode)||st.st_uid||
       statfs(MOUNT,&fs)||strcmp(fs.f_fstypename,"exfatfs")||
       strcmp(fs.f_mntonname,"/system_ex"))return 0;
    DIR *directory=opendir(MOUNT);if(!directory)return 0;
    unsigned count=0;int empty=1;struct dirent *entry;
    errno=0;
    while((entry=readdir(directory))) {
        if(++count>16||!memchr(entry->d_name,0,sizeof(entry->d_name))||
           (strcmp(entry->d_name,".")&&strcmp(entry->d_name,".."))) {empty=0;break;}
    }
    if(errno)empty=0;
    if(closedir(directory))empty=0;
    return report("underlying_mountpoint empty=%d original_system_volume=1 contents_changed=0",empty)&&empty;
}
int main(int argc,char **argv) {
    if(argc!=2||strcmp(argv[1],"--restore-mount"))return 2;
    journal=open(LAUNCH_LOG_PREFIX "-mount.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(journal<0)return 1;
    int success=0,calls=0;
    if(!report("BEGIN code=ps5-qwen-postboot-title-mount-v1 GPU_calls=0 title_launches=0 registration_calls=0 system_volume_remounts=0 unmount_calls=0")||
       constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!idle()||!no_native_owner()||
       registration_state()!=1||!new_files_valid()||!registered_metadata_valid()||
       !exact_text(APP "/mount.lnk",NEW_STAGE,1)||!empty_underlying_mountpoint()||
       !live_context()||!idle()||!no_native_owner()||!claim("restore-mount"))goto done;
    struct iovec iov[]={{"fstype",7},{"nullfs",7},{"from",5},{NEW_STAGE,sizeof(NEW_STAGE)},
                        {"fspath",7},{MOUNT,sizeof(MOUNT)}};
    if(!report("BEFORE own_title_nullfs_mount flags=0 maximum_calls=1 GPU_calls=0"))goto done;
    errno=0;calls=1;int rc=nmount(iov,sizeof(iov)/sizeof(iov[0]),0),error=errno;
    if(!report("RETURN own_title_nullfs_mount rc=%d errno=%d",rc,error)||rc)goto done;
    struct statfs fs;
    if(statfs(MOUNT,&fs)||strcmp(fs.f_fstypename,"nullfs")||
       strcmp(fs.f_mntonname,MOUNT)||strcmp(fs.f_mntfromname,NEW_STAGE)||
       !new_mounted_valid()||!live_context()||!idle()||!no_native_owner())goto done;
    success=1;
done:
    report("END success=%d mount_calls=%d log_healthy=%d GPU_calls=0 title_launches=0 unmount_calls=0 system_volume_remounts=0 registration_calls=0",success,calls,healthy);
    int status=success&&healthy?0:1;if(close(journal))status=1;return status;
}
