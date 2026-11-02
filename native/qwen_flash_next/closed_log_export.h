/* SPDX-License-Identifier: MIT
 * Read only the enumerated logs of positively exited, obsolete native owners.
 * Original permissions and bytes remain unchanged. Payloads stay in the private
 * once-only journal until the host has archived its positively returned result.
 */
static _Alignas(16384) unsigned char closed_log_window[16384];
static int case_export_closed_logs(int*calls){
    const uint64_t started=qwen_launch_now(NULL);
    if(!started||!report("CLOSED_LOG_EXPORT_PROOF prior_archive_sha256=" CASE_PRIOR_ARCHIVE_SHA256 " source_writes=0 permission_changes=0"))return 0;
    for(unsigned i=0;i<CASE_CLOSED_LOG_COUNT;++i){
        const struct ClosedLog *item=&case_closed_logs[i];struct stat before,named,after,mounted;
        if(!qwen_launch_headroom(NULL)||lstat(item->path,&before)||!S_ISREG(before.st_mode)||before.st_nlink!=1||
            (before.st_mode&07777)!=0600||before.st_uid>1||before.st_gid||before.st_size!=(off_t)item->bytes||
            item->bytes==0||item->bytes>(1u<<20)||lstat(item->alias,&mounted))return 0;
        struct stat normalized=before;normalized.st_dev=mounted.st_dev;if(!unchanged(&normalized,&mounted))return 0;
        int fd=open(item->path,O_RDONLY|O_NOFOLLOW|O_DIRECT);++*calls;if(fd<0)return 0;
        int valid=(fcntl(fd,F_GETFL)&O_DIRECT)==O_DIRECT&&!fstat(fd,&named)&&unchanged(&before,&named);
        struct ai_sha256 hash;ai_sha256_init(&hash);
        for(uint64_t offset=0;valid&&offset<item->bytes;offset+=16384){
            const uint64_t now=qwen_launch_now(NULL);const size_t bytes=item->bytes-offset<16384?(size_t)(item->bytes-offset):16384;
            if(!now||now<started||now-started>180000000000ull||!qwen_launch_headroom(NULL)){valid=0;break;}
            const ssize_t got=pread(fd,closed_log_window,16384,(off_t)offset);if(got!=(ssize_t)bytes){valid=0;break;}
            ai_sha256_update(&hash,closed_log_window,bytes);
            for(size_t at=0;at<bytes;at+=448){
                const size_t count=bytes-at<448?bytes-at:448;char hex[897];
                for(size_t j=0;j<count;++j){unsigned char v=closed_log_window[at+j];hex[2*j]="0123456789abcdef"[v>>4];hex[2*j+1]="0123456789abcdef"[v&15];}hex[2*count]=0;
                if(!report("CLOSED_LOG_BYTES ordinal=%u offset=%llu hex=%s",i,(unsigned long long)(offset+at),hex)){valid=0;break;}
            }
        }
        if(valid&&(pread(fd,closed_log_window,16384,(off_t)((item->bytes+16383)&~16383ull))!=0||
            fstat(fd,&after)||!unchanged(&before,&after)||lstat(item->path,&named)||!unchanged(&before,&named)||
            lstat(item->alias,&mounted)))valid=0;
        if(valid){normalized=before;normalized.st_dev=mounted.st_dev;valid=unchanged(&normalized,&mounted);}
        const int closed=close(fd);if(!valid||closed)return 0;
        unsigned char digest[32];char hex[65];ai_sha256_final(&hash,digest);
        for(unsigned j=0;j<32;++j){hex[2*j]="0123456789abcdef"[digest[j]>>4];hex[2*j+1]="0123456789abcdef"[digest[j]&15];}hex[64]=0;
        if(!report("CLOSED_LOG_SEALED ordinal=%u bytes=%llu sha256=%s full_identity_and_EOF=1 original_mode=0600",i,(unsigned long long)item->bytes,hex))return 0;
    }
    return report("CLOSED_LOG_EXPORT_COMPLETE count=%u original_permissions_unchanged=1 source_writes=0 GPU_calls=0",CASE_CLOSED_LOG_COUNT);
}
