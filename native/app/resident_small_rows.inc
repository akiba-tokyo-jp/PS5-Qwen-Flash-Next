// SPDX-License-Identifier: MIT
// Included in ResidentMappedSourceReader's public section. Reuse the original
// scratch leases and workers; all callbacks consume immutable, completed input.
bool upload_small_rows(const std::array<std::uintptr_t,8>&addresses,
        unsigned count,std::size_t bytes,
        const std::function<void(const std::array<SourceReadRequest,12>&,unsigned,
            const std::array<void*,4>&,const std::function<void(unsigned)>&,
            const std::function<void(unsigned,const void*,std::int64_t)>&)>&execute,
        const std::function<void(unsigned,const void*)>&consume,
        std::array<std::uint64_t,5>&counters){
    require_completed_window();
    if(!execute||!consume||!count||count>8||!bytes||bytes>5120)return false;
    std::array<std::size_t,8>files{},order{},group{};
    std::array<std::uint64_t,8>offset{},begin{},end{};
    for(unsigned i=0;i<count;++i){
        const auto at=addresses[i];
        const auto range=candidate_range([&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
        if(range==ranges_.end()||bytes>range->bytes-(at-range->at))return false;
        files[i]=range->file;offset[i]=range->offset+at-range->at;
        begin[i]=offset[i]-(offset[i]%model_read_alignment);
        end[i]=begin[i]+rounded(offset[i]-begin[i]+bytes);order[i]=i;
        if(end[i]>files_[files[i]].bytes)return false;
    }
    std::sort(order.begin(),order.begin()+count,[&](auto a,auto b){
        return files[a]<files[b]||(files[a]==files[b]&&begin[a]<begin[b]);});
    std::array<SourceReadRequest,12>requests{};
    std::array<std::size_t,8>group_file{};
    unsigned groups=0;
    for(unsigned sorted=0;sorted<count;++sorted){
        const unsigned i=unsigned(order[sorted]);
        if(groups&&group_file[groups-1]==files[i]&&
           begin[i]<=requests[groups-1].offset+requests[groups-1].bytes&&
           end[i]-requests[groups-1].offset<=model_read_window/4){
            auto&r=requests[groups-1];r.bytes=std::max<std::uint64_t>(r.offset+r.bytes,end[i])-r.offset;
        }else{
            group_file[groups]=files[i];requests[groups]={-1,nullptr,std::size_t(end[i]-begin[i]),begin[i]};++groups;
        }
        group[i]=groups-1;
    }
    for(unsigned i=0;i<groups;++i)for(unsigned j=0;j<i;++j)
        if(!source_schedule_parallel(files_[group_file[i]].identity,requests[i].offset,requests[i].bytes,
            files_[group_file[j]].identity,requests[j].offset,requests[j].bytes))return false;
    // At most eight original files: acquiring all descriptors cannot evict a
    // request's handle from the original bounded eight-entry descriptor cache.
    for(unsigned i=0;i<groups;++i){ProfileScope timing(stats_.handle_ns);requests[i].fd=handle(group_file[i]);}
    std::array<void*,4>leases{};
    for(unsigned i=0;i<4;++i)leases[i]=static_cast<unsigned char*>(scratch_)+i*(model_read_window/4);
    busy_=true;pending_windows_=count;
    std::uint64_t consumer_ns=0,metadata_ns=0;unsigned used=0,returned=0;
    try{
        const auto before=[&](unsigned g){ProfileScope timing(metadata_ns);
            if(g>=groups||ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin||
               ops_.identity(requests[g].fd)!=files_[group_file[g]].identity)
                fail("Small-row batch cannot preserve original source identity and reserves");};
        const auto use=[&](unsigned g,const void*target,std::int64_t got){
            {ProfileScope timing(metadata_ns);
             if(g>=groups||got!=std::int64_t(requests[g].bytes)||
                ops_.identity(requests[g].fd)!=files_[group_file[g]].identity)
                fail("Small-row batch returned incomplete or changed input");}
            {ProfileScope timing(consumer_ns);
             for(unsigned i=0;i<count;++i)if(group[i]==g){
                 consume(i,static_cast<const unsigned char*>(target)+(offset[i]-requests[g].offset));++used;}}
            ++returned;++stats_.physical_read_calls;stats_.physical_read_bytes+=requests[g].bytes;
            stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,requests[g].bytes);
            counters[4]+=requests[g].bytes;
        };
        const auto started=ProfileClock::now();execute(requests,groups,leases,before,use);
        const auto elapsed=profile_elapsed_ns(started);
        if(used!=count||returned!=groups||consumer_ns>elapsed||metadata_ns>elapsed-consumer_ns)
            fail("Small-row batch completion counters differ");
        stats_.read_ns+=elapsed-consumer_ns-metadata_ns;stats_.consumer_ns+=consumer_ns;
        stats_.bytes+=count*bytes;stats_.chunks+=count;++stats_.parallel_batches;
        ++counters[0];counters[1]+=count;counters[2]+=groups;counters[3]+=count*bytes;
        consumer_started_=ProfileClock::now();completed();return true;
    }catch(...){failed_=true;throw;}
}
