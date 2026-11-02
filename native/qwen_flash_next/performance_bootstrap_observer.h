/* SPDX-License-Identifier: MIT
 * Read the prerequisites of the previously successful startup order.
 * No runtime initialization, mount mutation, title launch or GPU operation.
 */
#pragma once
#include <sys/mount.h>
#include <sys/stat.h>
#include <ps5/kernel.h>

static struct statfs qwen_startup_mounts[4096];
static int qwen_success_route_prerequisites(FILE *out,unsigned phase) {
    const char *alias="/system_ex/app/PPSA99190";
    const char *source="/data/ai/native-moss-image-sft/PPSA99190";
    int count=getfsstat(qwen_startup_mounts,sizeof(qwen_startup_mounts),MNT_NOWAIT);
    if(count<1||count>=4096)return 1;
    unsigned title_mounts=0,owned_mounts=0;
    uint64_t fingerprint=UINT64_C(14695981039346656037);
    for(int i=0;i<count;++i){
        const struct statfs *m=&qwen_startup_mounts[i];
        if(!memchr(m->f_fstypename,0,sizeof(m->f_fstypename))||
           !memchr(m->f_mntonname,0,sizeof(m->f_mntonname))||
           !memchr(m->f_mntfromname,0,sizeof(m->f_mntfromname)))return 1;
        if(!strcmp(m->f_mntonname,alias))++title_mounts;
        if(!strcmp(m->f_mntfromname,source))++owned_mounts;
        const char *values[]={m->f_fstypename,m->f_mntonname,m->f_mntfromname};
        for(unsigned v=0;v<3;++v){
            for(const unsigned char *p=(const unsigned char*)values[v];*p;++p)
                fingerprint=(fingerprint^*p)*UINT64_C(1099511628211);
            fingerprint=(fingerprint^0xffu)*UINT64_C(1099511628211);
        }
    }
    struct stat st;memset(&st,0,sizeof(st));
    int source_rc=lstat(source,&st);
    struct statfs fs;memset(&fs,0,sizeof(fs));
    int alias_rc=statfs(alias,&fs);
    int strings=!alias_rc&&memchr(fs.f_fstypename,0,sizeof(fs.f_fstypename))&&
        memchr(fs.f_mntonname,0,sizeof(fs.f_mntonname))&&
        memchr(fs.f_mntfromname,0,sizeof(fs.f_mntfromname));
    int exact=!!(strings&&!strcmp(fs.f_fstypename,"nullfs")&&
        !strcmp(fs.f_mntonname,alias)&&!strcmp(fs.f_mntfromname,source));
    unsigned free_pages=0,page_size=0;size_t n=sizeof(free_pages),p=sizeof(page_size);
    int free_rc=sysctlbyname("vm.stats.vm0.v_free_count",&free_pages,&n,NULL,0);
    int page_rc=sysctlbyname("hw.pagesize",&page_size,&p,NULL,0);
    fprintf(out,"SUCCESS_ROUTE phase=%u firmware=%u mount_count=%d mount_fingerprint=%llu title_mounts=%u owned_mounts=%u source_directory=%d exact_title_alias=%d alias_statfs_rc=%d free_pages=%u page_size=%u reads_only=1\n",
        phase,kernel_get_fw_version(),count,(unsigned long long)fingerprint,title_mounts,owned_mounts,
        !source_rc&&S_ISDIR(st.st_mode),exact,alias_rc,free_pages,page_size);
    return source_rc||!S_ISDIR(st.st_mode)||free_rc||page_rc||n!=sizeof(free_pages)||p!=sizeof(page_size)||!page_size;
}
