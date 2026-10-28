#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind changed MoE/delivery objects while retaining original shader checks."""
from pathlib import Path


def main():
    original=Path(__file__).with_name('rebind_model_io_provenance.py').read_text()
    begin=original.index("    selected=next(x for x in linked['bounded_model_source_overrides']['objects']")
    end=original.index('    replacements={}',begin)
    replacement='''    originals={row['source']:row for row in extended['objects']}
    selected_rows=[row for row in linked['bounded_model_source_overrides']['objects']if row['object']!=originals[row['source']]['object']]
    if not selected_rows:raise ValueError('Distinct actual compiled delivery objects required')
    for selected in selected_rows:
        recipe=selected['command'];actual=Path(recipe[recipe.index('-c')+1])
        if record(selected['object']['path'])!=selected['object']or record(actual)!=selected['actual_source']:
            raise ValueError('Changed object or actual compile source differs')
'''
    original=original[:begin]+replacement+original[end:]
    begin=original.index("        data=copy.deepcopy(data);row=next(x for x in data['objects']")
    end=original.index('        for key,file in path_fields.items()',begin)
    replacement='''        data=copy.deepcopy(data)
        for selected in selected_rows:
            row=next(x for x in data['objects']if x['source']==selected['source']);row.clear();row.update(selected)
            data['sources'][selected['source']]['patched_sha256']=selected['actual_source']['sha256']
'''
    original=original[:begin]+replacement+original[end:]
    original=original.replace("record(actual)]","*[row['actual_source']for row in selected_rows]]")
    original=original.replace("result['inputs_before'] += [","result['inputs_before'] += [record(ROOT/'tools/rebind_model_io_provenance.py'),")
    original=original.replace("data['actual_MoE_overlay']=dict(","data['actual_delivery_overlay']=dict(")
    # Each row already contains its actual command/source/object. Keep an
    # immutable aggregate receipt without assigning the final row to them all.
    begin=original.index("        data['actual_delivery_overlay']=dict(")
    end=original.index("        directory=a.out/name;",begin)
    original=original[:begin]+'''        data['actual_delivery_overlay']=dict(parent=record(origin),actual_objects=selected_rows,
            link_receipt=record(a.linked),immutable_original_sources_preserved=True)
'''+original[end:]
    namespace={'__file__':__file__,'__name__':'__main__'}
    exec(compile(original,__file__,'exec'),namespace)
if __name__=='__main__':main()
