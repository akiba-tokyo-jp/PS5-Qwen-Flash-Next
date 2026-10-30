    bool upload_delivery_bundles(const std::array<SourceReadRequest,4>&input,
            const std::array<SourceIdentity,4>&identity,unsigned count,
            const std::function<void(const std::array<SourceReadRequest,4>&,unsigned,const std::array<void*,4>&,
                const std::function<void(unsigned)>&,const std::function<void(unsigned,const void*,std::int64_t)>&)>&execute,
            const std::function<void(unsigned,unsigned,const void*,std::size_t)>&consume){
        require_completed_window();if(!count||count>4||!execute||!consume)return false;
        for(unsigned i=0;i<count;++i){const auto&r=input[i];const auto&id=identity[i];
            if(r.fd<0||r.bytes!=1540096||r.offset%model_read_alignment||!id[0]||!id[1]||id[5]>(512ull<<20)||r.offset>id[5]||r.bytes>id[5]-r.offset)return false;
            for(unsigned j=0;j<i;++j)if(!source_schedule_parallel(id,r.offset,r.bytes,identity[j],input[j].offset,input[j].bytes))return false;
        }
        std::array<void*,4>leases{};for(unsigned i=0;i<4;++i)leases[i]=static_cast<unsigned char*>(scratch_)+i*(model_read_window/4);
        busy_=true;pending_windows_=count;std::uint64_t consumer_ns=0,metadata_ns=0;unsigned consumed=0;
        try{
            const auto before=[&](unsigned i){ProfileScope metadata(metadata_ns);ProfileScope timing(stats_.headroom_ns);
                if(ops_.identity(input[i].fd)!=identity[i]||ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin)
                    fail("Delivery bundle source identity or reserve differs");};
            const auto use=[&](unsigned i,const void*target,std::int64_t got){
                {ProfileScope metadata(metadata_ns);if(i>=count||got!=1540096||ops_.identity(input[i].fd)!=identity[i])fail("Delivery bundle did not positively return unchanged");}
                {ProfileScope timer(consumer_ns);const auto*p=static_cast<const unsigned char*>(target);
                    consume(i,0,p,537600);consume(i,1,p+537600,537600);consume(i,2,p+1075200,460800);}
                ++consumed;++stats_.physical_read_calls;stats_.physical_read_bytes+=1540096;stats_.bytes+=1536000;++stats_.chunks;stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,1540096);
            };
            const auto begun=ProfileClock::now();execute(input,count,leases,before,use);const auto total=profile_elapsed_ns(begun);
            if(consumed!=count||consumer_ns>total||metadata_ns>total-consumer_ns)fail("Bundle queue accounting differs");
            stats_.read_ns+=total-consumer_ns-metadata_ns;stats_.consumer_ns+=consumer_ns;++stats_.parallel_batches;
            consumer_started_=ProfileClock::now();completed();return true;
        }catch(...){failed_=true;throw;}
    }
