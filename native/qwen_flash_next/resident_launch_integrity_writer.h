/* SPDX-License-Identifier: MIT
 * Included only in the exact ordinary launcher after its original SHA reader.
 * Root-owned fresh receipt binds the completed full hash to the native inode.
 */
#include "resident_launch_integrity_context.h"
static int resident_launch_receipt_written;
static int resident_launch_receipt_refuse(const char *phase) {
    (void)report("RESIDENT_SELF_RECEIPT_REFUSED phase=%s errno=%d launch_not_called_by_receipt=1",phase,errno);
    return 0;
}
static int resident_receipt_directory(unsigned owner) {
    struct stat s;return !lstat(NEW_STAGE "/qwen-runtime",&s)&&S_ISDIR(s.st_mode)&&
        s.st_uid==owner&&s.st_gid==0&&(s.st_mode&07777)==0755;
}
static int resident_launch_digest_matches(const char *path,size_t bytes,const char *sha) {
    struct stat first;const int selected=!strcmp(path,RESIDENT_SELF_PATH)&&bytes==RESIDENT_SELF_BYTES&&!strcmp(sha,RESIDENT_SELF_SHA256);
    if(selected&&(geteuid()!=0||lstat(path,&first)||!S_ISREG(first.st_mode)))return resident_launch_receipt_refuse("initial_identity");
    if(!qwen_launch_digest_matches(path,bytes,sha))return 0;
    if(!selected)return 1;
    if(resident_launch_receipt_written)return 1;
    struct stat s,p,alias;memset(&s,0,sizeof(s));
    if(lstat(path,&s)||!unchanged(&first,&s)||!S_ISREG(s.st_mode)||s.st_size!=(off_t)bytes||!s.st_ino)return resident_launch_receipt_refuse("identity_after_full_hash");
    /* nullfs can report a different device ID for the same backing inode.
     * Bind the receipt to the exact admitted title mount used by /app0. */
    struct statfs fs;memset(&fs,0,sizeof(fs));
    if(lstat(MOUNT "/eboot.bin",&alias)||statfs(MOUNT,&fs)||
       !memchr(fs.f_fstypename,0,sizeof(fs.f_fstypename))||strcmp(fs.f_fstypename,"nullfs")||
       !memchr(fs.f_mntonname,0,sizeof(fs.f_mntonname))||strcmp(fs.f_mntonname,MOUNT)||
       !memchr(fs.f_mntfromname,0,sizeof(fs.f_mntfromname))||strcmp(fs.f_mntfromname,NEW_STAGE))return resident_launch_receipt_refuse("qualified_nullfs_mount");
    p=s;p.st_dev=alias.st_dev;if(!unchanged(&p,&alias))return resident_launch_receipt_refuse("mapped_inode_identity");
    char shader_json[1024]={0};
#ifdef RESIDENT_SHADER_SOURCE_PATH
    struct stat shader_before,shader_after,shader_alias;
    if(lstat(RESIDENT_SHADER_SOURCE_PATH,&shader_before)||!S_ISREG(shader_before.st_mode)||
       shader_before.st_size!=(off_t)RESIDENT_SHADER_BYTES||
       !qwen_launch_digest_matches(RESIDENT_SHADER_SOURCE_PATH,RESIDENT_SHADER_BYTES,RESIDENT_SHADER_SHA256)||
       lstat(RESIDENT_SHADER_SOURCE_PATH,&shader_after)||!unchanged(&shader_before,&shader_after)||
       lstat(MOUNT "/qwen-runtime/" RESIDENT_SHADER_FILENAME,&shader_alias))
        return resident_launch_receipt_refuse("complete_shader_integrity");
    struct stat shader_normalized=shader_after;shader_normalized.st_dev=shader_alias.st_dev;
    if(!unchanged(&shader_normalized,&shader_alias))return resident_launch_receipt_refuse("mounted_shader_identity");
    int sn=snprintf(shader_json,sizeof(shader_json),
        ",\"external_shader\":{\"schema\":\"ps5-qwen-same-launch-shader-integrity-v1\",\"path\":\"%s\","
        "\"bytes\":%llu,\"sha256\":\"%s\",\"identity\":[%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu]}",
        RESIDENT_SHADER_APP_PATH,(unsigned long long)RESIDENT_SHADER_BYTES,RESIDENT_SHADER_SHA256,
        (unsigned long long)shader_alias.st_dev,(unsigned long long)shader_after.st_ino,(unsigned long long)shader_after.st_mode,
        (unsigned long long)shader_after.st_uid,(unsigned long long)shader_after.st_gid,(unsigned long long)shader_after.st_size,
        (unsigned long long)shader_after.st_mtim.tv_sec,(unsigned long long)shader_after.st_mtim.tv_nsec,
        (unsigned long long)shader_after.st_ctim.tv_sec,(unsigned long long)shader_after.st_ctim.tv_nsec);
    if(sn<=0||(size_t)sn>=sizeof(shader_json))return resident_launch_receipt_refuse("bounded_shader_receipt");
    if(!report("RESIDENT_SHADER_RECEIPT full_Direct_SHA256_identity_EOF_passed=1 per_use_original_SPIRV_hashes_preserved=1"))return 0;
#endif
    char text[2048];int n=snprintf(text,sizeof(text),
        "{\"schema\":\"ps5-qwen-same-launch-SELF-integrity-v1\",\"run_id\":\"%s\",\"nonce\":\"%s\","
        "\"SELF_bytes\":%llu,\"SELF_sha256\":\"%s\",\"full_Direct_SHA256_identity_EOF_passed\":true,"
        "\"identity\":[%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu]%s}\n",
        RESIDENT_RUN_ID,RESIDENT_RECEIPT_NONCE,(unsigned long long)bytes,sha,
        (unsigned long long)alias.st_dev,(unsigned long long)s.st_ino,(unsigned long long)s.st_mode,
        (unsigned long long)s.st_uid,(unsigned long long)s.st_gid,(unsigned long long)s.st_size,
        (unsigned long long)s.st_mtim.tv_sec,(unsigned long long)s.st_mtim.tv_nsec,
        (unsigned long long)s.st_ctim.tv_sec,(unsigned long long)s.st_ctim.tv_nsec,shader_json);
    if(n<=0||(size_t)n>=sizeof(text))return resident_launch_receipt_refuse("bounded_receipt_format");
    /* Use the existing native configuration-publication ownership protocol.
     * Native euid 0 does not bypass this title directory's write ownership.
     * Return the exact owner before the ordinary launch can proceed. */
    if(!resident_receipt_directory(1)||chown(NEW_STAGE "/qwen-runtime",0,0))
        return resident_launch_receipt_refuse("owned_directory_prepare");
    if(!resident_receipt_directory(0)) {
        int restored=!chown(NEW_STAGE "/qwen-runtime",1,0)&&resident_receipt_directory(1);
        return resident_launch_receipt_refuse(restored?"prepared_directory_observation":"directory_restore_after_prepare_failure");
    }
    int fd=open(RESIDENT_RECEIPT_PATH,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0) {
        int saved=errno;int restored=!chown(NEW_STAGE "/qwen-runtime",1,0)&&resident_receipt_directory(1);
        errno=saved;return resident_launch_receipt_refuse(restored?"exclusive_receipt_create":"directory_restore_after_create_failure");
    }
    int ok=fchmod(fd,0444)==0;size_t done=0;
    while(ok&&done<(size_t)n){ssize_t got=write(fd,text+done,(size_t)n-done);if(got<=0)ok=0;else done+=(size_t)got;}
    if(fsync(fd)||fstat(fd,&p)||p.st_uid!=0||(p.st_mode&0777)!=0444||p.st_size!=n)ok=0;
    if(close(fd)||lstat(path,&p)||!unchanged(&s,&p))ok=0;
    if(chown(NEW_STAGE "/qwen-runtime",1,0)||!resident_receipt_directory(1))
        return resident_launch_receipt_refuse("owned_directory_restore");
    if(!ok)return resident_launch_receipt_refuse("receipt_write_close_and_identity");
    if(!report("RESIDENT_SELF_RECEIPT full_Direct_SHA256_identity_EOF_passed=1 root_owned_readonly=1 payload_bytes=%d",n))return 0;
    resident_launch_receipt_written=1;return 1;
}
