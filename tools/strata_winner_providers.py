# SPDX-License-Identifier: MIT
"""Compose qualified providers with the unchanged3072 normal application."""
import copy
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require
def merge(normal,checkpoint,gpu,use_gpu):
 selected=gpu if use_gpu else checkpoint;seed=copy.deepcopy(normal)
 before=seed['lossless_shader_storage']['vulkan_object'];after=selected['lossless_shader_storage']['vulkan_object']
 require(seed['link_command'].count(before['path'])==1,'One actual GPU provider required')
 seed['link_command'][seed['link_command'].index(before['path'])]=after['path']
 for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=selected[k]
 archive=next(x for x in seed['link_command']if Path(x).name=='libllama.a');context=checkpoint['checkpoint_model_comparison']
 seed['link_command'].insert(seed['link_command'].index(archive),context['context_object']['path'])
 if use_gpu:
  model=gpu['GDN_model_graph_order'];seed['link_command'].insert(seed['link_command'].index(archive),model['object']['path'])
  asset=gpu['GDN_model_comparison'];found=[]
  for row in seed['CPU_metadata_scope']['changed_sources']:
   if row['object_path']in seed['link_command']and 'extern "C" const void *qwen_app_prepare_shader_code('in Path(row['source']['path']).read_text():found.append(row)
  require(len(found)==1,'One shader asset provider required');row=found[0];seed['link_command'][seed['link_command'].index(row['object_path'])]=asset['asset_object']['path']
  row.update(source=asset['asset_source'],object_path=asset['asset_object']['path'],command=asset['asset_command'])
  seed['GDN_model_graph_order']=model;seed['GDN_model_planner']=gpu['GDN_model_planner']
 seed['io_gpu_comparison']=selected['io_gpu_comparison'];seed['inputs_before']+=active_link_inputs(checkpoint)+active_link_inputs(gpu)
 return seed
