/* SPDX-License-Identifier: MIT
 * Empty journals need an explicit zero-byte EOF check; the qualified payload
 * reader deliberately refuses a zero payload. Nonempty files use it unchanged.
 */
static int case_closed_report_digest(const char*path,size_t bytes,const char*sha){
    if(bytes)return qwen_launch_digest_matches(path,bytes,sha);
    if(strcmp(sha,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")||
       !qwen_launch_headroom(NULL))return 0;
    struct stat named,opened,after;
    if(lstat(path,&named)||!S_ISREG(named.st_mode)||named.st_size)return 0;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0)return 0;
    int flags=fcntl(fd,F_GETFL);
    int ok=flags>=0&&(flags&O_DIRECT)&&!fstat(fd,&opened)&&unchanged(&named,&opened);
    if(ok)ok=qwen_launch_marker(NULL,1);
    if(ok){
        ssize_t got=pread(fd,qwen_launch_window,QWEN_LAUNCH_WINDOW,0);
        ok=qwen_launch_marker(NULL,0)&&got==0;
    }
    if(ok)ok=!fstat(fd,&after)&&unchanged(&opened,&after)&&!lstat(path,&after)&&unchanged(&opened,&after);
    if(close(fd))ok=0;
    return ok&&report("CLOSED_REPORT_EMPTY_EOF returned=1 whole_SHA256_exact=1 identity_stable=1");
}
