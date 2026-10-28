#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One MiB early Direct SELF read with the original ordinary memory floor."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    original=(ROOT/'tools/build_early_SELF.py').read_text()
    # Generate the same pure-C algorithm, changing only the requested window
    # and the CPU admission rule. The 19-page allocation margin is paid once.
    source=(ROOT/'native/app/resident_early_SELF.c').read_text()
    source=source.replace('WINDOW=65536','WINDOW=1048576').replace('static int sample(void)','static int sample(unsigned allocation_pages)')
    begin=source.index('    /* This narrow CPU recovery scope');end=source.index('    if(!result.free_before)',begin)
    source=source[:begin]+'''    result.minimum=minimum;result.reserved=reserved;
    result.selected_floor=minimum+(reserved>256?reserved:256);
    const uint64_t required=(uint64_t)result.selected_floor+allocation_pages;
'''+source[end:]
    source=source.replace('free>=result.selected_floor','free>=required').replace('!sample()','!sample(0)')
    source=source.replace('if(!start||!sample(0))','if(!start||!sample(19))')
    source=source.replace('window_bytes=65536','window_bytes=1048576')
    source=source.replace('    result.minimum=minimum;result.reserved=reserved;',
        '    if(minimum>UINT32_MAX-(reserved>256?reserved:256))return 0;\n    result.minimum=minimum;result.reserved=reserved;')
    # Preserve all physical/virtual alignment arguments at the qualified 64 KiB.
    generated_code=repr(source)
    needle="a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];replacements={};inputs="
    replacement="a.out.mkdir(parents=True);(a.out/'tmp').mkdir();early_C=a.out/'early-SELF-ordinary.private.c';early_C.write_text("+generated_code+",newline='\\n');commands=[];replacements={};inputs="
    assert original.count(needle)==1;original=original.replace(needle,replacement)
    original=original.replace("record(Path(__file__)),record(a.parent)","record(Path(__file__)),record(ROOT/'tools/build_early_SELF.py'),record(early_C),record(a.parent)")
    original=original.replace("str(ROOT/'native/app/resident_early_SELF.c');cobj=","str(early_C);cobj=")
    original=original.replace('ps5-qwen-early-SELF-v1','ps5-qwen-early-SELF-v2')
    original=original.replace('{"window_bytes",65536}','{"window_bytes",1048576}').replace('{"selected_extra_pages",2}','{"selected_extra_pages",0}')
    original=original.replace('kernel_minimum_plus_21','ordinary_minimum_plus_max_reserved_256')
    original=original.replace('(r->bytes+65535)/65536+1','(r->bytes+1048575)/1048576+1')
    original=original.replace('r->selected_floor!=r->minimum+21','r->selected_floor!=r->minimum+std::max<std::uint32_t>(r->reserved,256)')
    original=original.replace('{"maximum_read_window_bytes",65536}','{"maximum_read_window_bytes",1048576}')
    original=original.replace('read_window_bytes=65536,selected_CPU_minimum_extra_pages=21','read_window_bytes=1048576,ordinary_CPU_admission=True,new_allocation_extra_pages=19')
    original=original.replace("pure_C_source=record(ROOT/'native/app/resident_early_SELF.c')",
        "pure_C_template=record(ROOT/'native/app/resident_early_SELF.c'),pure_C_source=record(early_C)")
    needle=" main_source,main_obj=derive(recipe,original,text,'resident-comparison-early-SELF')"
    replacement=''' if 'qwen_app::require_resident_load_window(policy);'in text:
  text=text.replace('qwen_app::require_resident_load_window(policy);',
    'if(policy.contains("native_resident_model_load_window"))throw std::runtime_error("Original eight MiB model reads require no narrower window scope");')
 main_source,main_obj=derive(recipe,original,text,'resident-comparison-early-SELF')
 phase=prior['resident_phase_source']
 if phase['model_load_maximum_read_bytes']==1048576:
  phase_recipe=phase['command'].copy();phase_source=Path(phase['generated_source']['path']);phase_text=phase_source.read_text()
  needle='required().set_resident_load_limit(1u<<20);'
  if phase_text.count(needle)!=1:raise ValueError('Unique narrow load activation required')
  phase_text=phase_text.replace(needle,'required().set_resident_load_limit(model_read_window);')
  phase_generated,phase_object=derive(phase_recipe,phase_source,phase_text,'mapped-source-original-window')
 else:
  if phase['model_load_maximum_read_bytes']!=8388608:raise ValueError('Qualified original model read window required')
  phase_generated=phase_object=None
'''
    assert original.count(needle)==1;original=original.replace(needle,replacement)
    needle=" receipt['resident_bootstrap_namespace'].update("
    replacement=''' if phase_object is not None:
  receipt['resident_phase_source'].update(object=record(phase_object),generated_source=record(phase_generated),command=phase_recipe,
    model_load_maximum_read_bytes=8388608,postload_maximum_read_bytes=8388608)
'''+needle
    assert original.count(needle)==1;original=original.replace(needle,replacement)
    exec(compile(original,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})
if __name__=='__main__':main()
