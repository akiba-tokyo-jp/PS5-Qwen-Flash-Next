# SPDX-License-Identifier: MIT
"""Derive a separate all-Expert Q2 candidate from the closed mixed model."""
import copy,json,re
from expert_q2_model_source import SCOPE as MIXED_SCOPE
from build_expert_q2_composite import PACKED_SCOPE as MIXED_PACKED
from build_speculative_batch_probe import once

SCOPE=copy.deepcopy(MIXED_SCOPE)
SCOPE.update(schema='ps5-qwen-expert-all-q2-model-comparison-v1',Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',
 expected_active_Q2_slots=867,Down_encoding='signed_FP16_scale_MSE_fit')
PACKED_SCOPE=copy.deepcopy(MIXED_PACKED)
PACKED_SCOPE.update(schema='ps5-qwen-expert-all-q2-composite-source-v1',new_payloads='Down_Q2_0_MSE',retained_payloads='sealed_mixed_Q2_K_Gate_Up_and_non_Expert')

def literal(value):return json.dumps(json.dumps(value,separators=(',',':')))

def entry_source(text):
 text=once(text,'#include "expert_q2_composite_source.h"','#include "expert_all_q2_source_integrity.h"')
 text=once(text,'std::optional<qwen_app::ExpertQ2Receipt>','std::optional<qwen_app::ExpertAllQ2Receipt>')
 text=once(text,'qwen_app::expert_q2_composite_source_integrity(','qwen_app::expert_all_q2_source_integrity(')
 text=once(text,'qwen_app::validate_expert_q2_footprint(','qwen_app::validate_expert_all_q2_footprint(')
 text=once(text,literal(MIXED_SCOPE),literal(SCOPE));text=once(text,literal(MIXED_PACKED),literal(PACKED_SCOPE))
 text=once(text,'type != GGML_TYPE_Q4_0','type != GGML_TYPE_Q2_0')
 text=once(text,'type==GGML_TYPE_Q4_0?"Q4_0"','type==GGML_TYPE_Q2_0?"Q2_0"')
 text=once(text,'misses*1996800ull','misses*1536000ull')
 text=text.replace('Gate_Up_Q2_K_Down_Q4_0','Gate_Up_Q2_K_Down_Q2_0_MSE')
 text=re.sub(r'\b581\b','867',text)
 text=text.replace('ps5-qwen-expert-q2-model-result-v1','ps5-qwen-expert-all-q2-model-result-v1')
 return text

def cache_source(text):
 text=once(text,'#include "expert_q2_cache_reset.h"','#include "expert_all_q2_cache_reset.h"')
 text=once(text,'qwen_app::reset_expert_q2_cache_metadata(','qwen_app::reset_expert_all_q2_cache_metadata(')
 return re.sub(r'\b581\b','867',text)

def provider_source(text):
 return once(text,'if(src0_type==GGML_TYPE_Q2_K||src0_type==GGML_TYPE_Q4_0)return false;',
  'if(src0_type==GGML_TYPE_Q2_K||src0_type==GGML_TYPE_Q4_0||src0_type==GGML_TYPE_Q2_0)return false;')
