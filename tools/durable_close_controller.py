# SPDX-License-Identifier: MIT
"""Retain exact native close guards while replacing an unacknowledged stdout pipe."""
from build_speculative_batch_probe import once

def source(text):
    marker='    assert modified[:index]==source[:index]\n'
    addition=r'''    journal='/data/ai/moss-qwen-durable-close-'+secrets.token_hex(16)+'.log'
    modified='#include <fcntl.h>\n'+modified
    entry='    (void)argv;int accepted=0,calls=0,returned=0,rc=-1;'
    assert modified.count(entry)==1
    modified=modified.replace(entry,entry+'\n    output_fd=open('+json.dumps(journal)+',O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);\n    if(output_fd<0)return 3;output_selected=1;')
    assert modified.count('output_selected=1;return 1;')==1
    modified=modified.replace('output_selected=1;return 1;','output_selected=1;if(fsync(output_fd)){healthy=0;return 0;}return 1;')
    modified=modified.replace('filesystem_calls=0','durable_filesystem_journal=1')
'''
    text=once(text,marker,marker+addition)
    text=once(text,'|seteuid|open|malloc)', '|seteuid|malloc)')
    text=once(text,"pipe='1'", "pipe='0'")
    text=once(text,'filesystem_calls_in_controller=0,GPU_calls=0,Unix_signals=0,automatic_retries=0',
              'filesystem_journal_path=journal,filesystem_journal_required=True,GPU_calls=0,Unix_signals=0,automatic_retries=0')
    before="    b.lan.stage_new(artifact,remote,b.sha(artifact))\n    raw=b.lan.web('/elfldr?'+b.lan.urllib.parse.urlencode(request),1<<20,45);(out/'console.private.log').write_bytes(raw)"
    after="    raw=b.lan.execute_once(artifact,b.sha(artifact),'',remote,journal,out/'execution',60);(out/'console.private.log').write_bytes(raw)"
    return once(text,before,after)
