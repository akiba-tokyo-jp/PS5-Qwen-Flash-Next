# SPDX-License-Identifier: MIT
"""Bind changed cache code to both existing shader-storage controls."""
import copy,json
from pathlib import Path
from expert_q4 import record,require,write_json
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
def rebind_cache(result,out,command,source):
 resource=json.loads(Path(result['shader_resource_manifest']['path']).read_text());embedded_path=Path(resource['embedded_control']['path']);embedded=json.loads(embedded_path.read_text())
 replaced={};rows=[]
 for key,label in(('parent_model_io','parent'),('extended_model_io','extended')):
  old=embedded[key];m=json.loads(Path(old['path']).read_text());item=next(x for x in m['objects']if x['source']=='src/llama-moe-cache.cpp')
  item.update(object=record(command[command.index('-o')+1]),command=command,actual_source=source);m['sources'][item['source']]['patched_sha256']=source['sha256']
  path=out/label/'model-io.private.json';path.parent.mkdir(parents=True)
  key='ggml/src/ggml-vulkan/ggml-vulkan.cpp';original=Path(old['path']).parent/'source'/key;alias=path.parent/'source'/key
  alias.parent.mkdir(parents=True);alias.write_bytes(original.read_bytes())
  write_json(path,m);validate_overrides(path,Path(result['engine_receipt']['path']));rows.append(record(path));replaced[old['path']]=rows[-1]
  result['inputs_before'] +=[record(original),record(alias)]
 def replace(values):return[replaced.get(x['path'],x)for x in values]
 embedded=copy.deepcopy(embedded);embedded.update(parent_model_io=rows[0],extended_model_io=rows[1],inputs=replace(embedded['inputs'])+[source,record(Path(__file__))])
 ep=out/'embedded-shader.private.json';write_json(ep,embedded);replaced[str(embedded_path)]=record(ep)
 resource=copy.deepcopy(resource);resource.update(parent_model_io=rows[0],extended_model_io=rows[1],embedded_control=record(ep),inputs=replace(resource['inputs'])+[source])
 rp=out/'external-shader.private.json';write_json(rp,resource);qualified=validate_shader_resources(rp,rows[1]['path'],result['engine_receipt']['path'])
 result.update(bounded_model_source_manifest=rows[1],bounded_model_source_overrides=json.loads(Path(rows[1]['path']).read_text()),shader_resource_manifest=record(rp),lossless_shader_storage=qualified)
 result['inputs_before'] +=[record(Path(__file__)),*rows,record(ep),record(rp)]
