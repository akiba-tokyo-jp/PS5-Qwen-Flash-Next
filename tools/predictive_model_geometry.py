#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Match the original 48-trunk plus one retained MTP block geometry."""


def generate(source):
    old='model.layers.size()!=48||n_expert_used!=10)'
    new='!qwen_app::original_predictive_model_geometry(model.hparams.n_layer(),model.layers.size(),model.hparams.n_layer_nextn,model.hparams.n_expert,n_expert_used))'
    if source.count(old)!=1:raise ValueError('Unique original predictive model geometry required')
    return '#include "predictive_model_geometry.h"\n'+source.replace(old,new)
