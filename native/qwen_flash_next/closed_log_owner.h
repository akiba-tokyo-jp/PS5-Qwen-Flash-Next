/* SPDX-License-Identifier: MIT
 * Transfer only enumerated, closed obsolete logs to their archive reader.
 * The owner authorized log handling. No payload, mode or timestamp setter is used.
 */
static int closed_log_same_after_owner(const struct stat*before,const struct stat*after,unsigned owner){
    struct stat expected=*before;expected.st_uid=owner;expected.st_ctim=after->st_ctim;
    return unchanged(&expected,after)&&before->st_nlink==after->st_nlink&&before->st_flags==after->st_flags;
}
static int case_retire_completed_images(int*calls){
    struct stat original[17];
    if(CASE_CLOSED_LOG_COUNT!=17u)return 0;
    /* Validate the complete batch before the first metadata mutation. */
    for(unsigned i=0;i<CASE_CLOSED_LOG_COUNT;++i){
        const struct ClosedLog*item=&case_closed_logs[i];struct stat mounted;
        if(!qwen_launch_headroom(NULL)||lstat(item->path,&original[i])||!S_ISREG(original[i].st_mode)||
           original[i].st_nlink!=1||(original[i].st_mode&07777)!=0600||original[i].st_uid!=1||original[i].st_gid||
           original[i].st_size!=(off_t)item->bytes||!item->bytes||item->bytes>(1u<<20)||lstat(item->alias,&mounted))return 0;
        struct stat expected=original[i];expected.st_dev=mounted.st_dev;
        if(!unchanged(&expected,&mounted))return 0;
    }
    for(unsigned i=0;i<CASE_CLOSED_LOG_COUNT;++i){
        const struct ClosedLog*item=&case_closed_logs[i];struct stat before,after,mounted;
        if(!qwen_launch_headroom(NULL)||lstat(item->path,&before)||!unchanged(&original[i],&before))return 0;
        if(!report("CLOSED_LOG_OWNER_BEFORE ordinal=%u old_uid=1 new_uid=0 mode=0600 payload_writes=0",i))return 0;
        ++*calls;errno=0;const int rc=chown(item->path,0,0),saved=errno;
        if(!report("CLOSED_LOG_OWNER_RETURN ordinal=%u rc=%d errno=%d",i,rc,saved)||rc)return 0;
        if(lstat(item->path,&after)||!closed_log_same_after_owner(&before,&after,0)||lstat(item->alias,&mounted))return 0;
        struct stat expected=after;expected.st_dev=mounted.st_dev;
        if(!unchanged(&expected,&mounted)||!report("CLOSED_LOG_OWNER_COMPLETE ordinal=%u uid=0 mode=0600 payload_and_mtime_unchanged=1",i))return 0;
    }
    return report("CLOSED_LOG_OWNER_BATCH_COMPLETE count=17 mode_changes=0 payload_writes=0 GPU_calls=0");
}
