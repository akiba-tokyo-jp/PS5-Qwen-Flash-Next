/* SPDX-License-Identifier: MIT
 * Publish read permission for exactly one sealed, ordinarily closed capture.
 * Model files, payload bytes, UID/GID, inode, size and mtime remain unchanged.
 */
static int case_export_activation(int*calls){
    if(!case_completed_activation_reports_valid())return 0;
    struct stat before,after,mounted;
    if(lstat(CASE_ACTIVATION_PATH,&before)||!S_ISREG(before.st_mode)||before.st_nlink!=1||
       before.st_size!=(off_t)CASE_ACTIVATION_BYTES||before.st_uid>1||before.st_gid||
       ((before.st_mode&07777)!=0600&&(before.st_mode&07777)!=0644))return 0;
    if((before.st_mode&07777)==0600){
        if(!report("BEFORE completed_activation_read_permission old=0600 new=0644 payload_writes=0"))return 0;
        ++*calls;int rc=chmod(CASE_ACTIVATION_PATH,0644);
        if(!report("RETURN completed_activation_read_permission rc=%d errno=%d",rc,errno)||rc)return 0;
    }
    if(lstat(CASE_ACTIVATION_PATH,&after)||after.st_dev!=before.st_dev||after.st_ino!=before.st_ino||
       after.st_uid!=before.st_uid||after.st_gid!=before.st_gid||after.st_size!=before.st_size||
       after.st_mtim.tv_sec!=before.st_mtim.tv_sec||after.st_mtim.tv_nsec!=before.st_mtim.tv_nsec||
       (after.st_mode&07777)!=0644||lstat(CASE_ACTIVATION_ALIAS,&mounted))return 0;
    struct stat normalized=after;normalized.st_dev=mounted.st_dev;
    if(!unchanged(&normalized,&mounted)||
       !qwen_launch_digest_matches(CASE_ACTIVATION_PATH,CASE_ACTIVATION_BYTES,CASE_ACTIVATION_SHA256)||
       !qwen_launch_digest_matches(CASE_ACTIVATION_ALIAS,CASE_ACTIVATION_BYTES,CASE_ACTIVATION_SHA256))return 0;
    return report("ACTIVATION_EXPORTED complete_physical_and_alias_SHA256_EOF=1 payload_writes=0 original_inode_size_mtime_UID_GID_preserved=1");
}
