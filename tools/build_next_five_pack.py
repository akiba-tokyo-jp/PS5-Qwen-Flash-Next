#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove the348-triplet software cap for a finite1024-triplet native pack."""
from pathlib import Path
def main():
 source=Path(__file__).with_name('build_expert_q2_bundle_pack.py');text=source.read_text();assert text.count("selection['bundles']<=348")==1;text=text.replace("selection['bundles']<=348","selection['bundles']<=1024")
 marker="commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_bundle_pack.cpp');"
 replacement="native=ROOT/'native/qwen_flash_next/expert_q2_bundle_pack.cpp';actual=a.out/'expanded-pack.private.cpp';body=native.read_text();require(body.count('bundle_probe_file_bytes+65536')==1,'Exact disk price required');body=body.replace('bundle_probe_file_bytes+65536','bundle_probe_file_bytes+(256ull<<20)');old='need(pwrite(output,bundle,L::stride,uint64_t(i)*L::stride)==ssize_t(L::stride),\"Dense bundle write was short\");';require(body.count(old)==1,'Exact owned output write required');body=body.replace(old,'{errno=0;const auto written=pwrite(output,bundle,L::stride,uint64_t(i)*L::stride);const int saved=errno;need(written==ssize_t(L::stride),(std::string(\"Dense bundle write was short errno=\")+std::to_string(saved)+\" returned=\"+std::to_string(written)+\" index=\"+std::to_string(i)).c_str());}');actual.write_text(body,newline='\\n');commands[1][commands[1].index('-c')+1]=str(actual);"
 assert text.count(marker)==1;text=text.replace(marker,replacement)
 old="header,a.out/'CPU-only-headroom.private.c'";assert text.count(old)==1;text=text.replace(old,"header,actual,Path(__file__).with_name('build_expert_q2_bundle_pack.py'),a.out/'CPU-only-headroom.private.c'")
 text=text.replace("'(k.ki_stat==SSLEEP||k.ki_stat==SRUN||k.ki_stat==SLOCK)'","'(k.ki_stat==SSLEEP||k.ki_stat==SRUN||(k.ki_stat==SLOCK&&!strcmp(e->name,\"SceShellCore\")))'")
 exec(compile(text,str(source)+'#finite1024','exec'),{'__file__':__file__,'__name__':'__main__'})
if __name__=='__main__':main()
