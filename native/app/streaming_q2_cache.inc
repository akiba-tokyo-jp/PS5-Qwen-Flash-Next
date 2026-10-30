        if(qwen_app_Q2_quad_enabled()&&!six_refill){
            if(g.banks.size()!=3||l.experts.size()!=3||fills.size()>delivered.size())
                throw std::runtime_error("Streaming requires the exact original Q2 cache geometry");
            const auto joined_stream=[&](size_t a,size_t b){return !delivered[a]&&!delivered[b]&&fills[b].expert==fills[a].expert+1&&fills[b].slot==fills[a].slot+1;};
            std::array<size_t,320>available{};unsigned remaining=0;
            for(size_t i=0;i<fills.size();++i){if(delivered[i])continue;
                // Preserve already qualified adjacency/coalescing groups.
                if((i&&joined_stream(i-1,i))||(i+1<fills.size()&&joined_stream(i,i+1)))continue;
                available[remaining++]=i;
            }
            for(unsigned first=0;first<remaining;first+=4){
                const unsigned experts=std::min(4u,remaining-first),count=experts*3;
                struct StreamUpload{std::array<ggml_tensor*,12>banks{};std::array<std::size_t,12>bytes{};std::array<int32_t,12>slots{};}job;
                const void*addresses[12]{};std::size_t sizes[12]{};
                for(unsigned e=0;e<experts;++e)for(unsigned role=0;role<3;++role){const unsigned id=e*3+role;const auto&w=l.experts[role];const auto&fill=fills[available[first+e]];
                    const auto size=w->nb[2];if((size!=537600&&size!=460800)||g.banks[role]->nb[2]!=size||w->ne[2]!=512||(w->type!=GGML_TYPE_Q2_K&&w->type!=GGML_TYPE_Q2_0))
                        throw std::runtime_error("Streaming projection type or shape differs");
                    addresses[id]=static_cast<const std::uint8_t*>(w->data)+fill.expert*size;sizes[id]=size;
                    job.banks[id]=g.banks[role];job.bytes[id]=size;job.slots[id]=fill.slot;
                }
                ggml_backend_synchronize(backend);
                if(qwen_app_try_Q2_stream(addresses,sizes,count,&job,[](void*opaque,unsigned id,const void*data){
                    if(id>=12)throw std::runtime_error("Streaming callback index differs");auto&u=*static_cast<StreamUpload*>(opaque);
                    if(u.slots[id]<0||u.slots[id]>=int(output_Q8_selected_slots))throw std::runtime_error("Streaming destination slot is unowned");
                    const auto offset=std::size_t(u.slots[id])*u.bytes[id];if(offset>ggml_nbytes(u.banks[id])||u.bytes[id]>ggml_nbytes(u.banks[id])-offset)
                        throw std::runtime_error("Streaming scatter exceeds its owned cache bank");
                    ggml_backend_tensor_set(u.banks[id],data,offset,u.bytes[id]);
                })){for(unsigned e=0;e<experts;++e)delivered[available[first+e]]=true;for(unsigned id=0;id<count;++id)bytes+=sizes[id];}
            }
        }
