// SPDX-License-Identifier: MIT
// Split the packed index before expanding it into logical weight elements.
// A 3713-plane cache has 6083379200 logical elements but fewer than 2 GiB
// of carrier bytes. Its packed vec4/block indices still fit in uint32.
layout(set=0,binding=0,std430) readonly buffer IQ2DownCarrier {uint words[];} iq2_down_carrier;
const uint IQ2_DOWN_CARRIER_BYTES=460800u;
const uint IQ2_DOWN_VALUES=1638400u;
const uint IQ2_DOWN_PAYLOAD_OFFSET=64u;
const uint IQ2_DOWN_TABLE_OFFSET=422464u;
uint iq2_down_byte(uint at){return (iq2_down_carrier.words[at>>2u]>>((at&3u)*8u))&255u;}
uint iq2_down_u16(uint at){return iq2_down_byte(at)|(iq2_down_byte(at+1u)<<8u);}
uint iq2_down_u32(uint at){return iq2_down_u16(at)|(iq2_down_u16(at+2u)<<16u);}
bool iq2_down_header(uint plane){
    const uint at=plane*IQ2_DOWN_CARRIER_BYTES;
    return iq2_down_u16(at)==0x7e00u&&iq2_down_u32(at+2u)==0x32495751u&&
        iq2_down_u32(at+6u)==0x4e574f44u&&iq2_down_u32(at+10u)==0x31524950u&&
        iq2_down_u32(at+14u)==0x53585832u&&iq2_down_u32(at+18u)==1u&&
        iq2_down_u32(at+22u)==422400u;
}
uvec2 iq2_down_plane_value(uint packed_index,uint values_per_index,uint lane){
    const uint packed_per_plane=IQ2_DOWN_VALUES/values_per_index;
    return uvec2(packed_index/packed_per_plane,(packed_index%packed_per_plane)*values_per_index+lane);
}
float iq2_down_decode_index(uint packed_index,uint values_per_index,uint lane){
    const uvec2 location=iq2_down_plane_value(packed_index,values_per_index,lane);
    const uint plane=location.x,logical=location.y;
    const uint base=plane*IQ2_DOWN_CARRIER_BYTES;
    const uint block=base+IQ2_DOWN_PAYLOAD_OFFSET+(logical>>8u)*66u,within=logical&255u;
    const uint group=block+2u+(within>>5u)*8u;
    const uint codes=iq2_down_u32(group+4u),sub=(within&31u)>>3u,bit=within&7u;
    const uint grid=base+IQ2_DOWN_TABLE_OFFSET+iq2_down_byte(group+sub)*8u;
    const uint magnitude=(iq2_down_u32(grid+(bit>>2u)*4u)>>((bit&3u)*8u))&255u;
    const uint signs=iq2_down_u32(base+IQ2_DOWN_TABLE_OFFSET+2048u+((codes>>(7u*sub))&127u)*4u);
    precise float scale=unpackHalf2x16(iq2_down_u16(block)).x;
    precise float delta=scale*(0.5+float(codes>>28u))*0.25;
    precise float value=(delta*float(magnitude))*((signs&(1u<<bit))!=0u?-1.0:1.0);
    return value;
}
