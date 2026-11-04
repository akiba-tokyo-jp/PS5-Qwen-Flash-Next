/* SPDX-License-Identifier: MIT
 * Read-only source identities and stable directory snapshots on the current boot.
 * Weight payloads are not reread; the authenticated source certificate remains
 * bound to every unchanged native file identity. No model/backend is linked.
 */
static void readmission_identity(const struct stat*s,uint64_t*out){
    uint64_t v[]={s->st_dev,s->st_ino,s->st_mode,s->st_uid,s->st_gid,s->st_size,
        s->st_mtim.tv_sec,s->st_mtim.tv_nsec,s->st_ctim.tv_sec,s->st_ctim.tv_nsec};
    memcpy(out,v,sizeof(v));
}
static int readmission_equal(const uint64_t*a,const uint64_t*b,unsigned start){
    for(unsigned i=start;i<10;++i)if(a[i]!=b[i])return 0;return 1;
}
static int readmission_directory(const char*path,uint64_t*identity,unsigned char*digest){
    struct stat before,after;if(lstat(path,&before)||!S_ISDIR(before.st_mode))return 0;
    DIR*d=opendir(path);if(!d)return 0;struct ai_sha256 hash;ai_sha256_init(&hash);
    unsigned count=0;int ok=1;struct dirent*item;
    errno=0;
    while((item=readdir(d))){
        if(++count>4096||!memchr(item->d_name,0,sizeof(item->d_name))){ok=0;break;}
        size_t length=strlen(item->d_name);uint64_t inode=item->d_fileno;
        ai_sha256_update(&hash,(const unsigned char*)&inode,sizeof(inode));
        ai_sha256_update(&hash,(const unsigned char*)item->d_name,length+1);
    }
    int read_error=errno,closed=closedir(d);
    if(read_error||closed||lstat(path,&after)||!unchanged(&before,&after))ok=0;
    if(!ok)return 0;readmission_identity(&after,identity);ai_sha256_final(&hash,digest);return 1;
}
static int case_model_readmission(void){
    uint64_t directories[READMISSION_DIRECTORY_COUNT][10];
    unsigned char snapshots[READMISSION_DIRECTORY_COUNT][32];
    for(unsigned i=0;i<READMISSION_DIRECTORY_COUNT;++i)
        if(!readmission_directory(readmission_directories[i],directories[i],snapshots[i]))return 0;
    for(unsigned i=0;i<READMISSION_SOURCE_COUNT;++i){
        const struct readmission_source*r=readmission_sources+i;struct stat physical,alias;uint64_t a[10],b[10];
        if(lstat(r->physical,&physical)||lstat(r->alias,&alias)||!S_ISREG(physical.st_mode)||!S_ISREG(alias.st_mode))
            return report("READMISSION_REFUSED source=%u phase=lstat errno=%d",i,errno)&&0;
        readmission_identity(&physical,a);readmission_identity(&alias,b);
        if(!readmission_equal(a,r->expected,0)||!readmission_equal(a,b,1))
            return report("READMISSION_REFUSED source=%u phase=complete_identity",i)&&0;
    }
    for(unsigned i=0;i<READMISSION_BACKING_COUNT;++i){
        const struct readmission_backing*r=readmission_backing+i;
        if(!qwen_launch_digest_matches(r->physical,r->bytes,r->sha)||
           !qwen_launch_digest_matches(r->alias,r->bytes,r->sha))return 0;
    }
    for(unsigned i=0;i<READMISSION_DIRECTORY_COUNT;++i){
        uint64_t identity[10];unsigned char digest[32];
        if(!readmission_directory(readmission_directories[i],identity,digest)||
           !readmission_equal(identity,directories[i],0)||memcmp(digest,snapshots[i],32))return 0;
    }
    struct stat a,b;uint64_t physical[10],alias[10];
    if(lstat(READMISSION_CANONICAL_DIRECTORY,&a)||lstat(READMISSION_APPLICATION_DIRECTORY,&b))return 0;
    readmission_identity(&a,physical);readmission_identity(&b,alias);
    if(memcmp(physical,readmission_previous_directory,6*sizeof(uint64_t))||!readmission_equal(physical,alias,1))return 0;
    if(!report("MODEL_READMISSION sources=%u backing_hashes=%u stable_directory_snapshots=%u source_payloads_changed=0",
        READMISSION_SOURCE_COUNT,READMISSION_BACKING_COUNT,READMISSION_DIRECTORY_COUNT))return 0;
    for(unsigned i=0;i<10;++i)
        if(!report("MODEL_DIRECTORY component=%u canonical=%llu application=%llu",i,
            (unsigned long long)physical[i],(unsigned long long)alias[i]))return 0;
    return live_context()&&idle();
}
