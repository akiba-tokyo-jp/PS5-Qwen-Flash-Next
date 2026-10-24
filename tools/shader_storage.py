#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exact immutable shader storage; no shader instruction or model conversion."""
import hashlib,json,re,struct,zlib
from pathlib import Path
MAGIC=b'QWSPV001'
SHUFFLED_MAGIC=b'QWSPV002'
PREFIX=b'ps5-qwen-shader-storage-v1\0'
MAX_SHADER=1<<20
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def record(path):
    path=Path(path).resolve();return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path))
def collect(build):
    build=Path(build);recipe_path=build/'compile_commands.json';recipes=json.loads(recipe_path.read_text())
    files=sorted({Path(r['file'])for r in recipes if r['file'].endswith('.comp.cpp')})
    header=build/'ggml/src/ggml-vulkan/ggml-vulkan-shaders.hpp'
    declared=set(re.findall(r'extern const unsigned char (\w+)_data\[\];',header.read_text()))
    assets=[];seen=set();sources=[]
    for path in files:
        sources.append(record(path));text=path.read_text()
        lengths={name:int(size)for name,size in re.findall(r'const uint64_t (\w+)_len = (\d+);',text)}
        for name,size,body in re.findall(r'const unsigned char (\w+)_data\[(\d+)\] = \{(.*?)\};',text,re.S):
            if name in seen:raise ValueError('Duplicate original shader asset')
            seen.add(name);tokens=[x.strip()for x in body.split(',')if x.strip()]
            raw=bytes(int(x,16)if x.lower().startswith('0x')else int(x,10)for x in tokens)
            if len(raw)!=int(size)or len(raw)!=lengths[name]or not 20<=len(raw)<=MAX_SHADER or len(raw)%4 or raw[:4]!=b'\x03\x02\x23\x07':
                raise ValueError('Original compiled SPIR-V identity/word bounds changed')
            assets.append((name,raw))
    if not assets or seen!=declared:raise ValueError('The complete original generated shader declaration set is required')
    return sorted(assets),sources,record(header),record(recipe_path)
def pack(raw):
    compressed=zlib.compress(raw,9)
    framed=MAGIC+struct.pack('<II',len(raw),len(compressed))+hashlib.sha256(raw).digest()+compressed
    framed+=b'\0'*((-len(framed))%4)
    ordered=b''.join(raw[i::4]for i in range(4));compressed=zlib.compress(ordered,9)
    shuffled=SHUFFLED_MAGIC+struct.pack('<II',len(raw),len(compressed))+hashlib.sha256(raw).digest()+compressed
    shuffled+=b'\0'*((-len(shuffled))%4)
    return min((raw,framed,shuffled),key=len)
def unpack(blob):
    if blob[:4]==b'\x03\x02\x23\x07':return blob
    if len(blob)<48 or blob[:8]not in (MAGIC,SHUFFLED_MAGIC):raise ValueError('Invalid shader storage header')
    size,count=struct.unpack_from('<II',blob,8)
    if not 20<=size<=MAX_SHADER or size%4 or not count or count>len(blob)-48 or len(blob)!=((48+count+3)&~3):
        raise ValueError('Invalid shader storage lengths')
    if any(blob[48+count:]):raise ValueError('Shader padding changed')
    state=zlib.decompressobj();raw=state.decompress(blob[48:48+count],MAX_SHADER+1)
    if blob[:8]==SHUFFLED_MAGIC and len(raw)==size:
        restored=bytearray(size);words=size//4
        for i in range(4):restored[i::4]=raw[i*words:(i+1)*words]
        raw=bytes(restored)
    if not state.eof or state.unused_data or state.unconsumed_tail or len(raw)!=size or hashlib.sha256(raw).digest()!=blob[16:48]:
        raise ValueError('Shader storage did not restore exact original bytes')
    return raw
def archive_members(path):
    data=Path(path).read_bytes()
    if data[:8]!=b'!<arch>\n':raise ValueError('An immutable regular archive is required')
    offset=8;names=b''
    while offset<len(data):
        header=data[offset:offset+60]
        if len(header)!=60 or header[58:]!=b'`\n':raise ValueError('Invalid archive member header')
        size=int(header[48:58]);body=data[offset+60:offset+60+size]
        if len(body)!=size:raise ValueError('Truncated archive member')
        name=header[:16].strip().decode('ascii')
        if name=='//':names=body
        elif name not in ('/','/SYM64/'):
            if name.startswith('#1/'):
                count=int(name[3:]);name=body[:count].rstrip(b'\0').decode('ascii');body=body[count:]
            elif name.startswith('/')and name[1:].isdigit():
                begin=int(name[1:]);end=names.find(b'/\n',begin)
                if end<0:raise ValueError('Invalid archive long filename')
                name=names[begin:end].decode('ascii')
            else:name=name.rstrip('/')
            yield name,body
        offset+=60+size+(size%2)
    if offset!=len(data):raise ValueError('Archive member alignment changed')
def elf_details(data):
    if data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,16)[0]!=1:
        raise ValueError('A native ELF64 little-endian shader object is required')
    begin=struct.unpack_from('<Q',data,40)[0];stride,count=struct.unpack_from('<HH',data,58)
    if stride!=64 or not count or begin+count*stride>len(data):raise ValueError('Invalid ELF section table')
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,begin+i*stride)for i in range(count)]
    result={};symbol_tables={}
    for table_index,section in enumerate(sections):
        if section[1]!=2:continue
        strings=sections[section[6]];strings=data[strings[4]:strings[4]+strings[5]]
        if section[9]!=24 or section[4]+section[5]>len(data):raise ValueError('Invalid ELF symbol table')
        symbols=[]
        for at in range(section[4],section[4]+section[5],24):
            name,info,unused,index,value,size=struct.unpack_from('<IBBHQQ',data,at)
            end=strings.find(b'\0',name)
            if end<0:raise ValueError('Invalid ELF symbol name')
            name=strings[name:end].decode('ascii')
            item=dict(name=name,kind=info&15,binding=info>>4,section=index,value=value,size=size,
                section_type=sections[index][1]if index<len(sections)else None)
            symbols.append(item)
            if info&15!=1 or index==0 or index>=len(sections)or not name.endswith(('_data','_len')):continue
            target=sections[index]
            if target[1]not in (1,8)or value+size>target[5]or(target[1]==1 and target[4]+value+size>len(data)):
                raise ValueError('Invalid compiled shader symbol span')
            item['data']=b'\0'*size if target[1]==8 else data[target[4]+value:target[4]+value+size];result[name]=item
        symbol_tables[table_index]=symbols
    relocations={}
    for section in sections:
        if section[1]!=4:continue
        if section[9]!=24 or section[6]not in symbol_tables:raise ValueError('Invalid shader relocation table')
        symbols=symbol_tables[section[6]]
        for at in range(section[4],section[4]+section[5],24):
            offset,info,addend=struct.unpack_from('<QQq',data,at)
            relocations[(section[7],offset)]=(symbols[info>>32],info&0xffffffff,addend)
    return result,relocations
def elf_objects(data):return {name:row['data']for name,row in elf_details(data)[0].items()}
def compiled_assets(archive,generated,header):
    expected=dict(generated);found={};members=[]
    declarations={}
    for line in Path(header).read_text().splitlines():
        match=re.fullmatch(r'extern const (?:void|unsigned char)\s*\*\s*(?:const\s+)?(\w+)_data((?:\[\d+\])+);',line)
        if match:declarations[match[1]]=(line.removeprefix('extern ').removesuffix(';'),[int(x)for x in re.findall(r'\d+',match[2])])
    if not declarations:raise ValueError('Original shader lookup declarations were not recognized')
    tables={}
    for name,body in archive_members(archive):
        if not name.endswith('.comp.cpp.o'):continue
        members.append(dict(name=name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
        symbols,relocations=elf_details(body)
        source=Path(header).parent/name.removesuffix('.o')
        initializers={}
        for table_name,kind,expression in re.findall(r'const (?:void\s*\*\s*|uint64_t\s+)(\w+)_(data|len)(?:\[\d+\])+\s*=\s*(\{.*?\});',source.read_text(),re.S):
            tokens=[v.strip()for v in expression.replace('{','').replace('}','').split(',')if v.strip()]
            initializers[(table_name,kind)]=tokens
        for key,recorded in symbols.items():
            if not key.endswith('_data')or key[:-5]not in expected:continue
            raw=recorded['data']
            key=key[:-5]
            if key in found or len(raw)!=struct.unpack('<Q',symbols[key+'_len']['data'])[0]or raw!=expected[key]:
                raise ValueError('Generated source and immutable compiled shader bytes differ')
            found[key]=raw
        for key,(declaration,dimensions)in declarations.items():
            if key+'_data'not in symbols:continue
            if key in tables:raise ValueError('Duplicate shader lookup table')
            pointer=symbols[key+'_data'];length=symbols[key+'_len']['data'];count=len(pointer['data'])//8
            product=1
            for d in dimensions:product*=d
            if count!=product or len(length)!=8*count:raise ValueError('Shader lookup dimensions changed')
            pointer_expressions=initializers.get((key,'data'));length_expressions=initializers.get((key,'len'))
            if pointer_expressions is None or length_expressions is None or len(pointer_expressions)!=count or len(length_expressions)!=count:
                raise ValueError('Complete original shader lookup initializers are required')
            targets=[]
            for i in range(count):
                relocation=relocations.get((pointer['section'],pointer['value']+8*i))
                if relocation is None:
                    if pointer['data'][8*i:8*i+8]!=b'\0'*8 or struct.unpack_from('<Q',length,8*i)[0]:raise ValueError('Unknown shader lookup entry')
                    if pointer_expressions[i]not in ('nullptr','NULL','0')or length_expressions[i]!='0':raise ValueError('Original null shader lookup initializer changed')
                    targets.append(None);continue
                target,kind,addend=relocation
                if kind!=1:raise ValueError('Unsupported shader pointer relocation')
                if target['name'].endswith('_data')and target['name'][:-5]in expected and addend==0:
                    asset=target['name'][:-5]
                else:
                    candidates=[n[:-5]for n,r in symbols.items()if n.endswith('_data')and n[:-5]in expected and r['section']==target['section']and r['value']==target['value']+addend]
                    if len(candidates)!=1:raise ValueError('Shader lookup target is ambiguous')
                    asset=candidates[0]
                actual_length=struct.unpack_from('<Q',length,8*i)[0]
                if pointer_expressions[i]!=asset+'_data'or length_expressions[i]not in (asset+'_len',str(len(expected[asset]))):
                    raise ValueError('Original source and compiled shader lookup targets differ')
                # Clang emits some extern-length initializers into NOBITS and
                # fills them in a static constructor. Accept only that exact
                # zero representation and the original named length expression.
                dynamic_zero=(actual_length==0 and symbols[key+'_len']['section_type']==8 and length_expressions[i]==asset+'_len')
                if actual_length!=len(expected[asset])and not dynamic_zero:
                    raise ValueError(f'Original shader lookup length changed: {name}:{key}[{i}] -> {asset}, {actual_length} != {len(expected[asset])}')
                targets.append(asset)
            tables[key]=dict(name=key,declaration=declaration,dimensions=dimensions,targets=targets)
    if found.keys()!=expected.keys():raise ValueError('The complete original compiled shader set is required')
    if tables.keys()!=declarations.keys():raise ValueError('The complete original shader lookup set is required')
    return sorted(found.items()),members,sorted(tables.values(),key=lambda x:x['name'])
def patch_vulkan(text):
    include='#include "mapped_source_bridge.h"'
    if text.count(include)!=1:raise ValueError('Original shader declaration include changed')
    text=text.replace(include,include+'\n#include "shader_assets_bridge.h"')
    before='    vk::ShaderModuleCreateInfo shader_module_create_info({}, spv_size, reinterpret_cast<const uint32_t *>(spv_data));'
    if text.count(before)!=1:raise ValueError('The original shader module input point changed')
    text=text.replace(before,'''    // Restore the exact immutable original before any existing float-control
    // patch. The single CPU lease stays live until positive module creation.
    void *shader_storage_lease=nullptr;size_t restored_shader_size=0;
    spv_data=qwen_app_prepare_shader_code(spv_data,spv_size,&restored_shader_size,&shader_storage_lease);
    spv_size=restored_shader_size;
'''+before)
    before='''    } catch (const vk::SystemError& e) {
        std::cerr << "ggml_vulkan: shader module creation failed for " << pipeline->name << ": " << e.what() << std::endl;
        throw;
    }

    vk::PushConstantRange pcr('''
    if text.count(before)!=1:raise ValueError('The checked positive module completion point changed')
    text=text.replace(before,before.replace('\n\n    vk::PushConstantRange','\n    qwen_app_complete_shader_code(shader_storage_lease);\n\n    vk::PushConstantRange'))
    return text
def registry_digest(assets):
    digest=hashlib.sha256(PREFIX)
    for name,raw in assets:digest.update(name.encode('ascii')+b'\0'+struct.pack('<Q',len(raw))+hashlib.sha256(raw).digest())
    return digest.hexdigest()
def write_storage(assets,out,tables):
    out=Path(out);pool=out/'shader-storage.private.bin';assembly=out/'shader-storage.private.S';metadata=out/'shader-registry.private.cpp'
    rows=[];offset=0;unique={}
    with pool.open('xb')as target:
        for name,raw in assets:
            stored=pack(raw)
            if unpack(stored)!=raw:raise ValueError('Lossless shader byte roundtrip failed')
            raw_hash=hashlib.sha256(raw).hexdigest();canonical=unique.get(raw_hash)
            if canonical is None:
                canonical=dict(name=name,offset=offset,raw=raw);unique[raw_hash]=canonical
                target.write(stored);offset+=len(stored)
            elif canonical['raw']!=raw:raise ValueError('Original shader SHA256 collision')
            rows.append(dict(name=name,offset=canonical['offset'],alias_of=canonical['name']if canonical['name']!=name else None,
                storage_bytes=len(stored),original_bytes=len(raw),
                original_sha256=hashlib.sha256(raw).hexdigest(),storage_sha256=hashlib.sha256(stored).hexdigest()))
    quoted=json.dumps(pool.as_posix())
    lines=['#ifdef _WIN32','.section .rdata,"dr"','#else','.section .rodata.qwen_shader_assets,"a",@progbits','#endif']
    cpp=['// Generated from immutable original compiled SPIR-V. Do not edit.','#include "shader_assets_bridge.h"',
         '#include "ggml-vulkan-shaders.hpp"']
    lookup_rows=[];sizes={r['name']:r['storage_bytes']for r in rows}
    def nested(values,dimensions):
        if len(dimensions)==1:return '{'+','.join(values)+'}'
        stride=1
        for d in dimensions[1:]:stride*=d
        return '{'+','.join(nested(values[i*stride:(i+1)*stride],dimensions[1:])for i in range(dimensions[0]))+'}'
    for table in tables:
        key=table['name'];dims=table['dimensions'];targets=table['targets']
        cpp.append(table['declaration']+' = '+nested([name+'_data'if name else'nullptr'for name in targets],dims)+';')
        cpp.append('const uint64_t '+key+'_len'+''.join('['+str(d)+']'for d in dims)+' = '+nested([str(sizes[name])if name else'0'for name in targets],dims)+';')
        for i,name in enumerate(targets):
            indices=[];remaining=i
            for j,d in enumerate(dims):
                stride=1
                for following in dims[j+1:]:stride*=following
                indices.append(remaining//stride);remaining%=stride
            suffix=''.join('['+str(v)+']'for v in indices)
            lookup_rows.append('{&'+key+'_data'+suffix+',&'+key+'_len'+suffix+','+(name+'_data'if name else'nullptr')+','+(str(sizes[name])if name else'0')+'},')
    cpp.append('static const qwen_shader_asset assets[] = {')
    for row in rows:
        name=row['name'];size=row['storage_bytes'];symbol=name+'_data'
        lines+=['.globl '+symbol,'#ifndef _WIN32','.type '+symbol+',@object','#endif']
        if row['alias_of']:lines+=['.set '+symbol+','+row['alias_of']+'_data']
        else:lines+=['.balign 16',symbol+':',f'.incbin {quoted},{row["offset"]},{size}']
        lines+=['#ifndef _WIN32',f'.size {symbol},{size}','#endif',
            '.balign 8','.globl '+name+'_len','#ifndef _WIN32','.type '+name+'_len,@object','#endif',name+'_len:',f'.quad {size}',
            '#ifndef _WIN32',f'.size {name}_len,8','#endif']
        digest=','.join('0x'+row['original_sha256'][i:i+2]for i in range(0,64,2))
        cpp.append('{'+json.dumps(name)+f',{symbol},{size},{row["original_bytes"]},'+'{'+digest+'}},')
    lines+=['#ifndef _WIN32','.section .note.GNU-stack,"",@progbits','#endif']
    cpp+=['};','static const qwen_shader_lookup lookups[] = {',*lookup_rows,'};',
          '__attribute__((constructor)) static void register_original_shader_storage() {',
          '    qwen_app_register_shader_assets(assets,sizeof(assets)/sizeof(assets[0]));',
          '    qwen_app_register_shader_lookups(lookups,sizeof(lookups)/sizeof(lookups[0]));','}']
    assembly.write_text('\n'.join(lines)+'\n',encoding='utf-8');metadata.write_text('\n'.join(cpp)+'\n',encoding='utf-8')
    return dict(shader_count=len(rows),original_bytes=sum(r['original_bytes']for r in rows),stored_bytes=offset,
        logical_stored_bytes=sum(r['storage_bytes']for r in rows),unique_originals=len(unique),
        maximum_shader_bytes=max(r['original_bytes']for r in rows),registry_sha256=registry_digest(assets),
        pool=record(pool),assembly=record(assembly),registry=record(metadata),shaders=rows,
        lookup_tables=tables,lookup_entries=len(lookup_rows))

def validate_storage(path,model_io_path,base_receipt):
    from build_model_io import validate_overrides
    path=Path(path);data=json.loads(path.read_text());model_io_path=Path(model_io_path)
    if data['schema']!='ps5-qwen-shader-storage-v1'or data['state']!='compiled_not_console_admitted':raise ValueError('Complete shader storage compilation is required')
    if record(model_io_path)!=data['extended_model_io']:raise ValueError('Shader storage and model I/O extension differ')
    parent_path=Path(data['parent_model_io']['path'])
    if record(parent_path)!=data['parent_model_io']:raise ValueError('Original model-I/O control changed')
    parent=validate_overrides(parent_path,base_receipt);current=validate_overrides(model_io_path,base_receipt)
    key='ggml/src/ggml-vulkan/ggml-vulkan.cpp';original=(parent_path.parent/'source'/key).read_text()
    if (model_io_path.parent/'source'/key).read_text()!=patch_vulkan(original):raise ValueError('Shader extension changed more than input restoration and positive completion')
    before={r['source']:r for r in parent['objects']};after={r['source']:r for r in current['objects']}
    for name in before:
        if name!=key and before[name]!=after[name]:raise ValueError('An unrelated model-I/O object changed')
    if after[key]['object']!=data['vulkan_object']:raise ValueError('The packed shader provider was not selected')
    for row in data['inputs']+[data['pool'],data['assembly'],data['registry'],*data['asset_objects'],data['vulkan_object']]:
        if record(row['path'])!=row:raise ValueError('An immutable shader storage input changed')
    if not current.get('shader_storage_extension')or data['shader_count']!=len(data['shaders']):raise ValueError('Explicit shader storage provenance is required')
    return data
