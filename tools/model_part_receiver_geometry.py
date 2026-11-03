#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive the explicitly bounded model-part socket and receive profiles."""
from start_success_route import need


def receiver_text(original, window, socket_buffer=32768, verify_socket=False,wait_all=False):
    need(window in (16384,262144) and original.count('(32ull<<20)')==1,
         'One exact original receiver and bounded supported window required')
    text=original.replace('(32ull<<20)','(512ull<<20)',1)
    need((socket_buffer==32768 and not verify_socket) or
         (window==262144 and socket_buffer==262144 and verify_socket), 'Only the explicitly bounded socket profiles are admitted')
    need(not wait_all or (window==262144 and socket_buffer==262144 and verify_socket),
         'Wait-all applies only to the positively bounded larger socket profile')
    if window==16384:return text
    changes=(('unsigned char direct_stage_window[16384]','unsigned char direct_stage_window[262144]'),
             ('offset+=16384','offset+=262144'),
             ('(DIRECT_STAGE_BYTES-offset)<16384?DIRECT_STAGE_BYTES-offset:16384',
              '(DIRECT_STAGE_BYTES-offset)<262144?DIRECT_STAGE_BYTES-offset:262144'),
             ('if(bytes<16384)memset(direct_stage_window+bytes,0,16384-bytes);',
              'if(bytes<262144)memset(direct_stage_window+bytes,0,262144-bytes);'),
             ('pwrite(file,direct_stage_window,16384,','pwrite(file,direct_stage_window,262144,'),
             ('written!=16384','written!=262144'))
    for before,after in changes:
        need(text.count(before)==1,'One exact receiver geometry site required: '+before)
        text=text.replace(before,after,1)
    before='window=16384 receive_buffer=32768'
    need(text.count(before)==1,'One exact truthful READY geometry required')
    text=text.replace(before,'window='+str(window)+' receive_buffer='+str(socket_buffer),1)
    if verify_socket:
        text=text.replace('const int receive_bytes=32768;','const int receive_bytes=262144;',1)
        before='    struct sockaddr_in local={0};'
        need(text.count(before)==1,'One socket observation before binding is required')
        check='''    int actual_receive_bytes=0;socklen_t receive_size=sizeof(actual_receive_bytes);
    if(getsockopt(server,SOL_SOCKET,SO_RCVBUF,&actual_receive_bytes,&receive_size)||
       receive_size!=sizeof(actual_receive_bytes)||actual_receive_bytes<receive_bytes||actual_receive_bytes>2*receive_bytes||
       !report("DIRECT_STAGE_SOCKET_BUFFER requested=%d observed=%d extra_kernel_reserve_pages=32",receive_bytes,actual_receive_bytes))goto done;
'''
        text=text.replace(before,check+before,1)
    if wait_all:
        before='recv(fd,(unsigned char*)value+offset,bytes-offset,0)'
        need(text.count(before)==1 and text.count('if(got<=0)return 0;offset+=(size_t)got;')==1,
             'One exact bounded receive loop is required')
        text=text.replace(before,'recv(fd,(unsigned char*)value+offset,bytes-offset,MSG_WAITALL)',1)
        text=text.replace('if(got<=0)return 0;offset+=(size_t)got;',
            'if(got<=0||(size_t)got>bytes-offset)return 0;offset+=(size_t)got;',1)
        marker='#include <sys/time.h>\n'
        need(text.count(marker)==1,'The actual socket ABI must be visible')
        text=text.replace(marker,marker+'_Static_assert(MSG_WAITALL==0x40,"The qualified PS5 wait-all socket ABI is required");\n',1)
    return text
