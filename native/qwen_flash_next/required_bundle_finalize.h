/* SPDX-License-Identifier: MIT
 * Finalize only a positively completed and ordinarily closed native CPU output.
 * Payload bytes, inode, size and mtime stay fixed; only owner metadata changes.
 */
static int case_finalize_bundle(int*calls){
    if(!case_completed_bundle_report_valid())return 0;
    struct stat before,after,alias;uint64_t observed[10];
    if(lstat(CASE_BUNDLE_PATH,&before)||!S_ISREG(before.st_mode))return 0;
    uint64_t first[]={before.st_dev,before.st_ino,before.st_mode,before.st_uid,before.st_gid,before.st_size,
        before.st_mtim.tv_sec,before.st_mtim.tv_nsec,before.st_ctim.tv_sec,before.st_ctim.tv_nsec};
    if(first[0]!=CASE_BUNDLE_CANONICAL_DEVICE)return 0;
    for(unsigned i=1;i<10;++i)if(i!=3&&first[i]!=case_bundle_native_identity[i])return 0;
    if(first[3]!=case_bundle_native_identity[3]&&!(first[3]==1&&case_bundle_native_identity[3]==0))return 0;
    if(!report("COMPLETED_BUNDLE_OWNER_VIEWS native_report_UID=%llu canonical_UID=%llu other_eight_metadata_fields_exact=1",
        (unsigned long long)case_bundle_native_identity[3],(unsigned long long)first[3]))return 0;
    if((before.st_mode&07777)!=0444||before.st_uid>1||before.st_gid)return 0;
    if(before.st_uid){
        if(!report("BEFORE owned_completed_bundle_owner_finalization source_UID=1 target_UID=0 payload_writes=0"))return 0;
        ++*calls;int rc=chown(CASE_BUNDLE_PATH,0,0);
        if(!report("RETURN owned_completed_bundle_owner_finalization rc=%d errno=%d",rc,errno)||rc)return 0;
    }else if(!report("COMPLETED_BUNDLE_ROOT_OWNER_ALREADY_FINAL owner_changes=0 payload_writes=0"))return 0;
    if(lstat(CASE_BUNDLE_PATH,&after)||after.st_dev!=before.st_dev||after.st_ino!=before.st_ino||
       after.st_mode!=before.st_mode||after.st_uid||after.st_gid||after.st_size!=before.st_size||
       after.st_mtim.tv_sec!=before.st_mtim.tv_sec||after.st_mtim.tv_nsec!=before.st_mtim.tv_nsec||
       lstat(CASE_BUNDLE_ALIAS,&alias))return 0;
    struct stat normalized=after;normalized.st_dev=alias.st_dev;if(!unchanged(&normalized,&alias))return 0;
    uint64_t final[]={after.st_dev,after.st_ino,after.st_mode,after.st_uid,after.st_gid,after.st_size,
        after.st_mtim.tv_sec,after.st_mtim.tv_nsec,after.st_ctim.tv_sec,after.st_ctim.tv_nsec};
    memcpy(observed,final,sizeof(final));
    for(unsigned i=0;i<10;++i)if(!report("COMPLETED_BUNDLE_ID component=%u value=%llu",i,(unsigned long long)observed[i]))return 0;
    return report("COMPLETED_BUNDLE_FINALIZED original_native_whole_SHA256_and_EOF_preserved=1 payload_writes=0");
}
