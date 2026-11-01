#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fetch only pinned GPL codec files and prepare an isolated host-only harness."""
import argparse,hashlib,json,shutil,urllib.request
from pathlib import Path
from build_preservation_integrity import record
REV='748eabf1b7d17819528cabf367d8e27109d8fce3'
BASE='src/LibProsperoPkg/PFS/Compression/Oodle/'
FILES={
 'KrakenBitReader.cs':'b1eb8ecaf991860beddfe7d4bc178877ce75ce58',
 'KrakenBitWriter.cs':'635ea82cfb1287879d5bd769e42009f6d883abe6',
 'KrakenDecoder.cs':'3b658a3a3c95dfb0a3f83f40c05e2eab2692d6c2',
 'KrakenHuffmanArrayEncoder.cs':'66421c828a05de3b20715458a3eff2773025f7ba',
 'KrakenOptimalCost.cs':'190409d2dbb58682cb144ef52fd20657bfa1765d',
 'KrakenSuffixTrieMatcher.cs':'2bcec3297edba6c71de9df636fa3120c9c430ea4',
 'OodleKrakenEncoder.cs':'3edca430384397b636421a2dee54e43047176167',
}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'upstream').mkdir();rows=[]
    sources={**{BASE+k:('upstream/'+k,v)for k,v in FILES.items()},
        'LICENSE':('LICENSE','f288702d2fa16d3cdf0035b15a9fcbc552cd88e7'),
        'NOTICE':('NOTICE','036b8890ad043b9953e2137ee7e1788251bb2b44')}
    for remote,(local,expected)in sources.items():
        url=f'https://raw.githubusercontent.com/SvenGDK/LibProsperoPKG/{REV}/{remote}'
        with urllib.request.urlopen(url,timeout=30)as response:payload=response.read(200000)
        actual=hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
        if actual!=expected:raise ValueError('Pinned Git blob mismatch: '+remote)
        path=a.out/local;path.write_bytes(payload);rows.append(dict(record(path),upstream_path=remote,git_blob=actual,url=url))
    own=Path(__file__).with_name('KrakenChunkBench.cs');shutil.copyfile(own,a.out/'Program.cs')
    (a.out/'Bench.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
        '<TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable>'
        '<EnableNETAnalyzers>false</EnableNETAnalyzers><GenerateAssemblyInfo>false</GenerateAssemblyInfo>'
        '</PropertyGroup></Project>\n',encoding='utf-8')
    (a.out/'source.private.json').write_text(json.dumps(dict(upstream_revision=REV,files=rows,harness=record(own),
        builder=record(__file__),host_only=True,proprietary_keys_or_resources_fetched=False,
        binary_distribution=False),indent=2),encoding='utf-8')
    print(json.dumps(dict(prepared=True,codec_files=len(FILES),legal_files=2,host_only=True)))
if __name__=='__main__':main()
