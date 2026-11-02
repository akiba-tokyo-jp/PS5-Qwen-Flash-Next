/* SPDX-License-Identifier: MIT
 * One nonce-bound CPU-only stream into a new O_DIRECT staging file.
 * No current application file is opened for writing or renamed here.
 */
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/time.h>
static _Alignas(16384) unsigned char direct_stage_window[16384];
static int direct_receive_exact(int fd,void*value,size_t bytes,uint64_t deadline,unsigned*calls){
    size_t offset=0;
    while(offset<bytes){
        uint64_t now=qwen_launch_now(NULL);if(!now||now>=deadline)return 0;
        ssize_t got=recv(fd,(unsigned char*)value+offset,bytes-offset,0);++*calls;
        if(got<=0)return 0;offset+=(size_t)got;
    }
    return 1;
}
static int case_receive_direct_stage(int*calls){
    int server=-1,client=-1,file=-1,success=0;unsigned reads=0,writes=0;
    const uint64_t start=qwen_launch_now(NULL),deadline=start+180000000000ull;
    if(!start||DIRECT_STAGE_BYTES==0||DIRECT_STAGE_BYTES>(32ull<<20))return 0;
    struct stat absent_file;if(lstat(DIRECT_STAGE_PATH,&absent_file)!=-1||errno!=ENOENT)return 0;
    server=socket(AF_INET,SOCK_STREAM,0);if(server<0)goto done;
    const int receive_bytes=32768;const struct timeval timeout={20,0};
    if(setsockopt(server,SOL_SOCKET,SO_RCVBUF,&receive_bytes,sizeof(receive_bytes))||
       setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)))goto done;
    struct sockaddr_in local={0};local.sin_len=sizeof(local);local.sin_family=AF_INET;
    local.sin_port=htons(DIRECT_STAGE_PORT);local.sin_addr.s_addr=DIRECT_STAGE_CONSOLE_IP;
    if(bind(server,(struct sockaddr*)&local,sizeof(local))||listen(server,1)||
       !report("DIRECT_STAGE_READY bounded_one_peer=1 bytes=%llu window=16384 receive_buffer=32768",(unsigned long long)DIRECT_STAGE_BYTES))goto done;
    struct sockaddr_in peer={0};socklen_t peer_bytes=sizeof(peer);client=accept(server,(struct sockaddr*)&peer,&peer_bytes);
    if(client<0||peer_bytes!=sizeof(peer)||peer.sin_family!=AF_INET||peer.sin_addr.s_addr!=DIRECT_STAGE_PEER_IP)goto done;
    if(setsockopt(client,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))||
       setsockopt(client,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout)))goto done;
    unsigned char header[128];uint64_t declared=0;
    if(!direct_receive_exact(client,header,sizeof(header),deadline,&reads))goto done;
    memcpy(&declared,header+40,8);
    if(memcmp(header,"QWENDIR1",8)||memcmp(header+8,DIRECT_STAGE_NONCE,32)||declared!=DIRECT_STAGE_BYTES||
       memcmp(header+48,DIRECT_STAGE_SHA256,64))goto done;
    for(unsigned i=112;i<128;++i)if(header[i])goto done;
    if(!qwen_launch_headroom(NULL)||!report("DIRECT_STAGE_HEADER_MATCHED new_file_only=1 before_open=1"))goto done;
    file=open(DIRECT_STAGE_PATH,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0644);++*calls;
    if(file<0||(fcntl(file,F_GETFL)&O_DIRECT)!=O_DIRECT)goto done;
    struct stat opened;if(fstat(file,&opened)||!S_ISREG(opened.st_mode)||opened.st_nlink!=1||opened.st_size||opened.st_uid>1||opened.st_gid)goto done;
    struct ai_sha256 hash;ai_sha256_init(&hash);
    for(uint64_t offset=0;offset<DIRECT_STAGE_BYTES;offset+=16384){
        const size_t bytes=(size_t)((DIRECT_STAGE_BYTES-offset)<16384?DIRECT_STAGE_BYTES-offset:16384);
        if(!qwen_launch_headroom(NULL)||!report("BEFORE Direct_stage_chunk offset=%llu bytes=%zu",(unsigned long long)offset,bytes))goto done;
        if(!direct_receive_exact(client,direct_stage_window,bytes,deadline,&reads))goto done;
        ai_sha256_update(&hash,direct_stage_window,bytes);
        if(bytes<16384)memset(direct_stage_window+bytes,0,16384-bytes);
        ssize_t written=pwrite(file,direct_stage_window,16384,(off_t)offset);++writes;
        if(!report("RETURN Direct_stage_chunk offset=%llu written=%lld",(unsigned long long)offset,(long long)written)||written!=16384)goto done;
    }
    unsigned char digest[32];char text_digest[65];ai_sha256_final(&hash,digest);
    for(unsigned i=0;i<32;++i){text_digest[2*i]="0123456789abcdef"[digest[i]>>4];text_digest[2*i+1]="0123456789abcdef"[digest[i]&15];}text_digest[64]=0;
    if(strcmp(text_digest,DIRECT_STAGE_SHA256)||ftruncate(file,(off_t)DIRECT_STAGE_BYTES)||fsync(file))goto done;
    int closed=close(file);file=-1;if(closed)goto done;
    if(!report("DIRECT_STAGE_SOURCE_STREAM_SHA256_MATCHED bytes=%llu reads=%u writes=%u",(unsigned long long)DIRECT_STAGE_BYTES,reads,writes)||
       !qwen_launch_digest_matches(DIRECT_STAGE_PATH,DIRECT_STAGE_BYTES,DIRECT_STAGE_SHA256))goto done;
    if(send(client,"QWENDONE",8,0)!=8)goto done;
    success=1;
done:
    if(file>=0&&close(file))success=0;
    if(client>=0&&close(client))success=0;
    if(server>=0&&close(server))success=0;
    if(!report("DIRECT_STAGE_RETURN success=%d all_socket_and_file_calls_returned=1 no_current_file_writes=1 GPU_calls=0",success))success=0;
    return success;
}
