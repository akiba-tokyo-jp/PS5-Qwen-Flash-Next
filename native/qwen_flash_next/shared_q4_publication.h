/* SPDX-License-Identifier: MIT
 * Seal only the explicitly generated new Q1 directory. No prior source writes,
 * Direct allocation, initialization, launch, mount operation or GPU call.
 */
static void shared_Q4_identity(const struct stat*s,uint64_t*out){
    uint64_t row[]={s->st_dev,s->st_ino,s->st_mode,s->st_uid,s->st_gid,s->st_size,
        s->st_mtim.tv_sec,s->st_mtim.tv_nsec,s->st_ctim.tv_sec,s->st_ctim.tv_nsec};memcpy(out,row,sizeof(row));
}
static int shared_Q4_same(const uint64_t*a,const uint64_t*b,unsigned first){
    for(unsigned i=first;i<10;++i)if(a[i]!=b[i])return 0;return 1;
}
static int shared_Q4_parents(void){
    for(unsigned i=0;i<SHARED_Q4_PARENT_COUNT;++i){
        const struct shared_Q4_parent*r=shared_Q4_parent_files+i;struct stat a,b;uint64_t x[10],y[10];
        if(lstat(r->physical,&a)||lstat(r->alias,&b)||!S_ISREG(a.st_mode)||!S_ISREG(b.st_mode))return 0;
        shared_Q4_identity(&a,x);shared_Q4_identity(&b,y);
        if(!shared_Q4_same(x,r->expected,0)||!shared_Q4_same(x,y,1))return 0;
    }
    return 1;
}
static int shared_Q4_directory(const char*path,uint64_t*identity,unsigned char*digest){
    struct stat before,after;if(lstat(path,&before)||!S_ISDIR(before.st_mode))return 0;
    DIR*d=opendir(path);if(!d)return 0;struct ai_sha256 hash;ai_sha256_init(&hash);
    unsigned count=0;int ok=1;struct dirent*item;errno=0;
    while((item=readdir(d))){
        if(++count>4096||!memchr(item->d_name,0,sizeof(item->d_name))){ok=0;break;}
        uint64_t inode=item->d_fileno;ai_sha256_update(&hash,(const unsigned char*)&inode,sizeof(inode));
        ai_sha256_update(&hash,(const unsigned char*)item->d_name,strlen(item->d_name)+1);
    }
    int read_error=errno,closed=closedir(d);
    if(read_error||closed||lstat(path,&after)||!unchanged(&before,&after))ok=0;
    if(!ok)return 0;shared_Q4_identity(&after,identity);ai_sha256_final(&hash,digest);return 1;
}
static int shared_Q4_report_identity(const char*kind,unsigned index,const uint64_t*v){
    return report("SHARED_Q4_ID kind=%s index=%u values=%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu",
        kind,index,(unsigned long long)v[0],(unsigned long long)v[1],(unsigned long long)v[2],(unsigned long long)v[3],
        (unsigned long long)v[4],(unsigned long long)v[5],(unsigned long long)v[6],(unsigned long long)v[7],
        (unsigned long long)v[8],(unsigned long long)v[9]);
}
static int case_seal_shared_Q4(int*calls){
    uint64_t directories[SHARED_Q4_DIRECTORY_COUNT][10];unsigned char snapshots[SHARED_Q4_DIRECTORY_COUNT][32];
    for(unsigned i=0;i<SHARED_Q4_DIRECTORY_COUNT;++i)
        if(!shared_Q4_directory(shared_Q4_directories[i],directories[i],snapshots[i]))return 0;
    if(!shared_Q4_parents())return 0;
    /* Authenticate every complete new file before changing its metadata. */
    for(unsigned i=0;i<SHARED_Q4_FILE_COUNT;++i){
        const struct shared_Q4_file*r=shared_Q4_files+i;
        if(!qwen_launch_digest_matches(r->physical,r->bytes,r->sha)||
           !qwen_launch_digest_matches(r->alias,r->bytes,r->sha))return 0;
    }
    for(unsigned i=0;i<SHARED_Q4_FILE_COUNT;++i){
        const struct shared_Q4_file*r=shared_Q4_files+i;struct stat before,after,alias;uint64_t a[10],b[10];
        int fd=open(r->physical,O_RDONLY|O_NOFOLLOW);if(fd<0)return 0;
        int valid=!fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_uid<=1&&!before.st_gid&&
            before.st_size==(off_t)r->bytes;
        if(valid){++*calls;valid=!fchown(fd,0,0);}
        if(valid){++*calls;valid=!fchmod(fd,0644);}
        if(valid)valid=!fstat(fd,&after)&&before.st_dev==after.st_dev&&before.st_ino==after.st_ino&&
            before.st_size==after.st_size&&before.st_mtim.tv_sec==after.st_mtim.tv_sec&&
            before.st_mtim.tv_nsec==after.st_mtim.tv_nsec&&!after.st_uid&&!after.st_gid&&after.st_mode==0100644;
        int closed=close(fd);if(!valid||closed||lstat(r->alias,&alias))return 0;
        shared_Q4_identity(&after,a);shared_Q4_identity(&alias,b);
        if(!shared_Q4_same(a,b,1)||!shared_Q4_report_identity("file",i,a))return 0;
    }
    int fd=open(SHARED_Q4_DIRECTORY,O_RDONLY|O_NOFOLLOW);struct stat directory;
    if(fd<0)return 0;int valid=!fstat(fd,&directory)&&S_ISDIR(directory.st_mode)&&directory.st_uid<=1&&!directory.st_gid;
    if(valid){++*calls;valid=!fchown(fd,0,0);}if(valid){++*calls;valid=!fchmod(fd,0755);}
    int closed=close(fd);if(!valid||closed)return 0;
    if(!shared_Q4_parents())return 0;
    for(unsigned i=0;i<SHARED_Q4_DIRECTORY_COUNT;++i){
        uint64_t identity[10];unsigned char digest[32];
        if(!shared_Q4_directory(shared_Q4_directories[i],identity,digest)||
           !shared_Q4_same(identity,directories[i],0)||memcmp(digest,snapshots[i],32))return 0;
    }
    struct stat alias;uint64_t a[10],b[10];
    if(lstat(SHARED_Q4_DIRECTORY,&directory)||lstat(SHARED_Q4_ALIAS,&alias))return 0;
    shared_Q4_identity(&directory,a);shared_Q4_identity(&alias,b);
    return a[2]==0040755&&!a[3]&&!a[4]&&shared_Q4_same(a,b,1)&&shared_Q4_report_identity("directory",0,a)&&
        report("SHARED_Q4_SEALED new_files=%u complete_physical_and_alias_SHA256_EOF=1 parent_sources=%u parent_identities_and_directory_snapshots_unchanged=1 original_source_writes=0",
            SHARED_Q4_FILE_COUNT,SHARED_Q4_PARENT_COUNT);
}
