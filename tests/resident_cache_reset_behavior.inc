// SPDX-License-Identifier: MIT
// Included after the actual pinned SLRU implementation in the manual host check.
struct CacheFixture {
    moe_cache_slru cache;std::array<std::array<int,512>,49> maps;
    explicit CacheFixture(unsigned slots){for(auto &row:maps)row.fill(-1);cache.init(49,512,slots,48);
        for(unsigned layer=0;layer<48;++layer)cache.slot_map[layer]=maps[layer].data();}
};
int main(){unsigned comparisons=0;
    for(bool policy:{false,true})for(unsigned slots:{53u,128u}){
        use_adaptive=policy;CacheFixture current(slots),fresh(slots);std::vector<moe_cache_slru::fill> a,b;
        for(unsigned pass=0;pass<3;++pass)for(unsigned layer=0;layer<48;++layer){std::array<int,20> ids;
            for(unsigned i=0;i<ids.size();++i)ids[i]=(layer*7+i*13+pass)%512;std::size_t hits=0;
            if(!current.cache.plan(layer,ids.data(),ids.size(),a,hits))throw std::runtime_error("Original fill refused");
            if(!current.cache.plan(layer,ids.data(),ids.size(),a,hits)||hits!=ids.size()||!a.empty())throw std::runtime_error("Original protected-hit path missing");}
        auto pointers=current.cache.slot_map;const auto occupied=qwen_app::reset_resident_cache_metadata(current.cache,48);
        if(!occupied||current.cache.slot_map!=pointers)throw std::runtime_error("Bank lookup ownership changed");
        for(unsigned pass=0;pass<4;++pass)for(unsigned layer=0;layer<48;++layer){std::array<int,40> ids;
            for(unsigned i=0;i<ids.size();++i)ids[i]=(layer*11+i*3+pass)%512;std::size_t ah=0,bh=0;
            if(!current.cache.plan(layer,ids.data(),ids.size(),a,ah)||!fresh.cache.plan(layer,ids.data(),ids.size(),b,bh)||ah!=bh||a.size()!=b.size())
                throw std::runtime_error("Reset cache differs from fresh original behavior");
            for(unsigned i=0;i<a.size();++i)if(a[i].expert!=b[i].expert||a[i].slot!=b[i].slot)throw std::runtime_error("Reset cache selected a different slot");
            if(current.cache.key_of!=fresh.cache.key_of||current.maps!=fresh.maps){throw std::runtime_error("Reset original routing differs");}
            ++comparisons;}
        current.cache.key_of[0]=49*512;bool refused=false;
        try{qwen_app::reset_resident_cache_metadata(current.cache,48);}catch(const std::runtime_error &){refused=true;}
        if(!refused)throw std::runtime_error("Invalid prior lookup was hidden by reset");
    }
    std::cout<<"{\"fresh_behavior_comparisons\":"<<comparisons<<",\"cache_shapes\":2,\"policies\":2,\"invalid_lookup_refused\":true,\"PS5_operations\":0}\n";
}
