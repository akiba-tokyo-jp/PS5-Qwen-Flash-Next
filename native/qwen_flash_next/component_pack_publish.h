/* SPDX-License-Identifier: MIT
 * Atomically publish one new immutable component pack with the same verified
 * runtime-directory owner lease as ordinary application publication.
 */
static int acquire_directory(const char*,unsigned,unsigned*,int*);
static int release_directory(const char*,unsigned,unsigned);
static int case_publish_component(int*calls){
    struct stat before,after;
    if(lstat(CASE_COMPONENT_TARGET,&before)!=-1||errno!=ENOENT||
       lstat(CASE_COMPONENT_ALIAS,&before)!=-1||errno!=ENOENT||
       !qwen_launch_digest_matches(CASE_COMPONENT_PENDING,CASE_COMPONENT_BYTES,CASE_COMPONENT_SHA256))return 0;
    int fd=open(CASE_COMPONENT_PENDING,O_RDONLY|O_NOFOLLOW);
    if(fd<0||fstat(fd,&before)||!S_ISREG(before.st_mode)||before.st_nlink!=1||before.st_uid>1||before.st_gid||
       before.st_size!=(off_t)CASE_COMPONENT_BYTES){if(fd>=0)(void)close(fd);return 0;}
    int mode=fchmod(fd,0444),closed=close(fd);if(mode||closed)return 0;
    unsigned owner=0;int held=0;
    if(!acquire_directory(NEW_STAGE "/qwen-runtime",0755,&owner,&held)){
        if(held)(void)release_directory(NEW_STAGE "/qwen-runtime",0755,owner);return 0;}
    if(!report("BEFORE component_pack_atomic_publication original_runtime_UID=%u existing_target_absent=1",owner)){
        (void)release_directory(NEW_STAGE "/qwen-runtime",0755,owner);return 0;}
    ++*calls;int rc=rename(CASE_COMPONENT_PENDING,CASE_COMPONENT_TARGET),saved=errno;
    int released=release_directory(NEW_STAGE "/qwen-runtime",0755,owner);
    if(!report("RETURN component_pack_atomic_publication rc=%d errno=%d original_runtime_owner_restored=%d",rc,saved,released)||rc||!released)return 0;
    if(lstat(CASE_COMPONENT_TARGET,&after)||after.st_dev!=before.st_dev||after.st_ino!=before.st_ino||
       after.st_size!=before.st_size||after.st_uid!=before.st_uid||after.st_gid!=before.st_gid||
       after.st_mtim.tv_sec!=before.st_mtim.tv_sec||after.st_mtim.tv_nsec!=before.st_mtim.tv_nsec||
       (after.st_mode&07777)!=0444||
       !qwen_launch_digest_matches(CASE_COMPONENT_TARGET,CASE_COMPONENT_BYTES,CASE_COMPONENT_SHA256)||
       !qwen_launch_digest_matches(CASE_COMPONENT_ALIAS,CASE_COMPONENT_BYTES,CASE_COMPONENT_SHA256))return 0;
    return report("COMPONENT_PACK_PUBLISHED whole_physical_and_alias_SHA256_EOF=1 immutable_mode=0444 original_current_files_untouched=1");
}
