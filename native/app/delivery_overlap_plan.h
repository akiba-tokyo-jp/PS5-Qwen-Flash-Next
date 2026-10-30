// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <cstddef>
#include <stdexcept>

namespace qwen_app {
struct OverlapRange {std::uintptr_t at=0;std::size_t bytes=0;std::uintptr_t address_space=0;};
inline bool overlaps(OverlapRange a,OverlapRange b){
    if(!a.at||!b.at||!a.bytes||!b.bytes)return false;
    if(a.at>UINTPTR_MAX-a.bytes||b.at>UINTPTR_MAX-b.bytes)throw std::runtime_error("Overlap address overflows");
    if(a.address_space!=b.address_space)return false;
    return a.at<b.at+b.bytes&&b.at<a.at+a.bytes;
}
struct OverlapNode {
    OverlapRange output;std::array<int,16>inputs;std::array<OverlapRange,16>external{};
    bool pure=false,writes=true,inplace=false;
    OverlapNode(){inputs.fill(-1);}
};
class DeliveryOverlapPlan {
public:
    static constexpr unsigned capacity=1024;
    std::array<OverlapNode,capacity>nodes;
    std::array<bool,capacity>selected{};
    enum class Decision {ready,missing,dependency,side_effect,live_input_alias,live_output_alias};
    Decision inspect(unsigned count,int endpoint){
        selected.fill(false);if(!count||count>capacity||endpoint<0||unsigned(endpoint)>=count)return Decision::missing;
        selected[endpoint]=true;
        for(int i=endpoint;i>=0;--i)if(selected[i]){
            if(!nodes[i].pure)return Decision::side_effect;
            for(int source:nodes[i].inputs)if(source>=0){if(source>=i||unsigned(source)>=count)return Decision::dependency;selected[source]=true;}
        }
        unsigned last=unsigned(endpoint);
        for(unsigned i=0;i<count;++i)for(int source:nodes[i].inputs)if(source==endpoint)last=i;
        if(last==unsigned(endpoint))return Decision::dependency;
        // An imported value may appear as a NONE/view node inside this split.
        // A node index does not imply that a later GPU operation regenerates it.
        std::array<bool,capacity>imported;imported.fill(true);
        for(unsigned i=0;i<count;++i){
            if(nodes[i].writes)imported[i]=false;
            else for(int source:nodes[i].inputs)if(source>=0&&unsigned(source)<i&&!imported[source])imported[i]=false;
        }
        for(unsigned i=0;i<count;++i)if(!selected[i]){
            for(unsigned j=0;j<count;++j)if(selected[j]&&nodes[j].writes){
                for(auto external:nodes[i].external)if(overlaps(nodes[j].output,external))return Decision::live_input_alias;
                for(int source:nodes[i].inputs)if(source>=0&&unsigned(source)<count&&imported[source]&&overlaps(nodes[j].output,nodes[source].output))return Decision::live_input_alias;
            }
            bool consumes=false;for(int source:nodes[i].inputs)consumes|=source==endpoint;
            if(i<=last&&nodes[i].writes&&overlaps(nodes[endpoint].output,nodes[i].output)&&!(consumes&&nodes[i].inplace))return Decision::live_output_alias;
        }
        return Decision::ready;
    }
};
}
