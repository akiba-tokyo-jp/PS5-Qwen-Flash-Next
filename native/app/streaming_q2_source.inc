    // Known demands only. Reuse four existing 2 MiB scratch leases after each
    // producer callback; source maps and descriptors remain owned throughout.
    bool upload_Q2_stream(const std::array<std::uintptr_t,12>&addresses,const std::array<std::size_t,12>&sizes,unsigned count,
            const std::function<void(const std::array<SourceReadRequest,12>&,unsigned,const std::array<void*,4>&,
                const std::function<void(unsigned)>&,const std::function<void(unsigned,const void*,std::int64_t)>&)>&execute,
            const std::function<void(unsigned,const void*)>&consume){
        require_completed_window();if(!execute||!consume||!count||count>12)return false;
        std::array<SourceReadRequest,12>requests{};std::array<std::size_t,12>files{},skips{};
        std::array<void*,4>leases{};for(unsigned i=0;i<4;++i)leases[i]=static_cast<unsigned char*>(scratch_)+i*(model_read_window/4);
        for(unsigned i=0;i<count;++i){const auto at=addresses[i];const auto bytes=sizes[i];if(bytes!=537600&&bytes!=460800)return false;
            const auto range=candidate_range([&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
            if(range==ranges_.end()||bytes>range->bytes-(at-range->at))return false;
            files[i]=range->file;const auto offset=range->offset+at-range->at;
            if(offset>=files_[files[i]].bytes||bytes>files_[files[i]].bytes-offset)return false;
            skips[i]=offset%model_read_alignment;const auto requested=std::size_t(rounded(skips[i]+bytes));
            if(requested>model_read_window/4||offset-skips[i]+requested>files_[files[i]].bytes)return false;
            requests[i]={-1,nullptr,requested,offset-skips[i]};
        }
        for(unsigned i=0;i<count;++i)for(unsigned j=0;j<i;++j)
            if(!source_schedule_parallel(files_[files[i]].identity,requests[i].offset,requests[i].bytes,
                files_[files[j]].identity,requests[j].offset,requests[j].bytes))return false;
        for(unsigned i=0;i<count;++i){ProfileScope timing(stats_.handle_ns);requests[i].fd=handle(files[i]);}
        busy_=true;pending_windows_=count;std::uint64_t consumer_ns=0;unsigned consumed=0;
        try{
            const auto before=[&](unsigned i){ProfileScope timing(stats_.headroom_ns);
                if(ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin||ops_.identity(requests[i].fd)!=files_[files[i]].identity)
                    fail("Streaming demand cannot preserve source identity and original reserves");};
            const auto use=[&](unsigned i,const void*target,std::int64_t got){
                if(i>=count||got!=std::int64_t(requests[i].bytes)||ops_.identity(requests[i].fd)!=files_[files[i]].identity)
                    fail("Streaming demand was short or changed source identity");
                {ProfileScope timing(consumer_ns);consume(i,static_cast<const unsigned char*>(target)+skips[i]);}
                ++consumed;++stats_.physical_read_calls;stats_.physical_read_bytes+=requests[i].bytes;
                stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,requests[i].bytes);
            };
            const auto started=ProfileClock::now();execute(requests,count,leases,before,use);const auto total=profile_elapsed_ns(started);
            if(consumed!=count||consumer_ns>total)fail("Streaming demand completion counters differ");
            stats_.read_ns+=total-consumer_ns;stats_.consumer_ns+=consumer_ns;
            for(unsigned i=0;i<count;++i)stats_.bytes+=sizes[i];stats_.chunks+=count;++stats_.parallel_batches;
            consumer_started_=ProfileClock::now();completed();return true;
        }catch(...){failed_=true;throw;}
    }
