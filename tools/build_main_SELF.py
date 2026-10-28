#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read the current SELF at main entry using a separately priced CPU scope."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    original=(ROOT/'tools/build_early_SELF.py').read_text()
    source=(ROOT/'native/app/resident_early_SELF.c').read_text()
    source=source.replace('WINDOW=65536','WINDOW=1048576')
    source=source.replace('qwen_resident_hash_SELF_before_CXX','qwen_resident_hash_SELF_at_main_entry')
    source=source.replace('before_CXX','at_main_entry_after_CXX').replace('before C++ initializers','at main entry after C++ initializers')
    source=source.replace('window_bytes=65536','window_bytes=1048576')
    diagnostic='''static void memory_stage(void){
    char line[240]="main_SELF_CPU_observation";size_t used=strlen(line);
    const char *keys[5]={" free_before="," free_last="," minimum_sampled="," selected_CPU_floor="," completed_reads="};
    const uint64_t values[5]={result.free_before,result.free_after,result.minimum_free,result.selected_floor,result.read_calls};
    for(unsigned i=0;i<5;++i){const size_t n=strlen(keys[i]);memcpy(line+used,keys[i],n);used+=n;
        char reverse[24];unsigned count=0;uint64_t value=values[i];
        do{reverse[count++]=(char)('0'+value%10);value/=10;}while(value);
        while(count)line[used++]=reverse[--count];}
    line[used]=0;qwen_native_stage(line);
}
'''
    start=source.index('int qwen_resident_hash_SELF_at_main_entry(void)')
    source=source[:start]+diagnostic+source[start:]
    start=source.index('int qwen_resident_hash_SELF_at_main_entry(void)')
    source=source[:start]+source[start:].replace('return 0;','{memory_stage();return 0;}')
    source=source.replace('result.elapsed_ns=now()-start;result.completed=1;',
        'result.elapsed_ns=now()-start;result.completed=1;memory_stage();')
    needle="a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];replacements={};inputs="
    replacement="a.out.mkdir(parents=True);(a.out/'tmp').mkdir();main_C=a.out/'main-entry-SELF.private.c';main_C.write_text("+repr(source)+",newline='\\n');commands=[];replacements={};inputs="
    assert original.count(needle)==1;original=original.replace(needle,replacement)
    original=original.replace("record(Path(__file__)),record(a.parent)","record(Path(__file__)),record(ROOT/'tools/build_early_SELF.py'),record(main_C),record(a.parent)")
    begin=original.index(" boot=prior['resident_bootstrap_namespace'];")
    end=original.index(' candidates=[',begin)
    original=original[:begin]+original[end:]
    original=original.replace('ps5-qwen-early-SELF-v1','ps5-qwen-main-SELF-v1').replace('native_resident_early_SELF','native_resident_main_SELF')
    original=original.replace('bind_resident_early_SELF','bind_resident_main_SELF')
    original=original.replace('{"window_bytes",65536}','{"window_bytes",1048576}')
    original=original.replace('(r->bytes+65535)/65536+1','(r->bytes+1048575)/1048576+1')
    original=original.replace('{"maximum_read_window_bytes",65536}','{"maximum_read_window_bytes",1048576}')
    original=original.replace('before_CXX_initializers','after_CXX_before_policy')
    original=original.replace("str(ROOT/'native/app/resident_early_SELF.c');cobj=","str(main_C);cobj=")
    original=original.replace("pure_C_source=record(ROOT/'native/app/resident_early_SELF.c'),bootstrap=record(boot_source)",
        "pure_C_template=record(ROOT/'native/app/resident_early_SELF.c'),pure_C_source=record(main_C),phase='after_CXX_before_policy'")
    original=original.replace('read_window_bytes=65536','read_window_bytes=1048576')
    original=original.replace(" receipt['resident_bootstrap_namespace'].update(object=record(boot_obj),generated=record(boot_source))",'')
    needle=" main_source,main_obj=derive(recipe,original,text,'resident-comparison-early-SELF')"
    replacement=''' # Repair the combined cohort join: the last request reset already
 # completed its producer epoch. The standalone prefix entry still needs
 # its initial completion after context construction.
 if 'retained_prefix_routes'in text:
  begin=text.index('        std::array<CompletedRouteEvidence,9> retained_prefix_routes;')
  end=text.index('        retained_prefix_routes=std::move(routes);',begin)
  prefix=text[begin:end]
  from resident_combined_comparison import qualify_prefix_entry
  prefix=qualify_prefix_entry(prefix)
  text=text[:begin]+prefix+text[end:]
 needle='    qwen_native_stage("main_entered GPU_not_started=1 model_loaded=0");'
 if text.count(needle)!=1:raise ValueError('Unique original main entry required')
 text='extern "C" int qwen_resident_hash_SELF_at_main_entry();\\nextern "C" [[noreturn]] void qwen_native_halt(const char *);\\n'+text.replace(needle,
  '    if(!qwen_resident_hash_SELF_at_main_entry())qwen_native_halt("main_SELF_Direct_integrity_returned_refusal");\\n'+needle)
 main_source,main_obj=derive(recipe,original,text,'resident-comparison-main-SELF')
'''
    assert original.count(needle)==1;original=original.replace(needle,replacement)
    original=original.replace('resident_early_SELF=dict','resident_main_SELF=dict')
    original=original.replace('early_SELF_native_link_passed=True','main_SELF_native_link_passed=True')
    exec(compile(original,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})
if __name__=='__main__':main()
