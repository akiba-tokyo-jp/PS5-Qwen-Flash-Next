# SPDX-License-Identifier: MIT
"""Select an admitted physical payload for the unchanged source-schedule test."""
from expert_q4 import require

def reader_header(text):
 start=text.index('    void qualify_source_schedule() {');end=text.index('\n    void enable_completed_pair_trace()',start)
 old=text[start:end];new=old
 marker='        if (schedule_enabled_ || files_.front().bytes < (16ull << 20))'
 require(new.count(marker)==1,'Exact original schedule admission required')
 new=new.replace(marker,'''        const auto payload=std::find_if(files_.begin(),files_.end(),[](const auto&f){return f.bytes>=(16ull<<20);});
        const auto preflight_file=std::size_t(payload-files_.begin());
        if (schedule_enabled_ || payload==files_.end())''')
 require(new.count('read_window(0,')==2 and new.count('pipeline_windows({0, 0},')==2,'Exact original two reference and two candidate tests required')
 new=new.replace('read_window(0,','read_window(preflight_file,').replace('pipeline_windows({0, 0},','pipeline_windows({preflight_file, preflight_file},')
 return text[:start]+new+text[end:]
