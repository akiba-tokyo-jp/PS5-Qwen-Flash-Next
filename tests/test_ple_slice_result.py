# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ple_slice_result import validate

def good():
    result=dict(schema='ps5-qwen-PLE-slice-fixture-v1',pid=7,GPU_graphs=208,device_ledger_live_bytes=0,
        device_ledger_peak_bytes=512<<20,source_preflight_read_calls=2,source_preflight_read_bytes=40000,
        existing_source_scratch_bytes=8<<20,source_worker_read_ns=0,maximum_absolute_error=1e-9,
        shader_CPU_verified_assets=1527,shader_module_inputs_after_CPU_verification=3,model_loaded=False,
        numerical_data='deterministic_original_shapes_not_model_weights',
        timed_scope='graph_compute_synchronization_driver_checkpoints_and_output_readback',widths=[])
    for key in('F64_reference_passed','all_F32_outputs_bit_exact','input_and_output_canaries_intact','original_BF16_to_F32_casts_preserved',
        'graph_construction_measured_separately','common_final_output_copy_in_all_arms','driver_final_epoch_retirement_requires_caller',
        'positive_device_idle_and_epoch_retirement','all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned'):result[key]=True
    for width in range(1,5):
        row=dict(tokens=width,CONT_nodes=[8,4,4,0],graph_construction_ns=[20,18,18,16],raw_device_buffer_cap_bytes=16<<20,
            all_operations_on_single_Vulkan_backend=True,warmups=[],batches=[])
        for mode in range(4):row['warmups'].append(dict(mode=mode,ordinal=mode+1,graph_completion_and_readback_ns=100))
        ordinal=4
        for candidate in(1,2,3):
            for round_ in range(8):
                for arm in range(2):
                    ordinal+=1;mode=candidate if(round_+arm)%2 else 0
                    row['batches'].append(dict(candidate=candidate,round=round_,mode=mode,ordinal=ordinal,
                        graph_completion_and_readback_ns=100 if mode else 120))
        result['widths'].append(row)
    return result

def stages(result):
    lines=['PLE_slice_shared_shader_CPU_admission_completed GPU_not_started=1']
    for width in result['widths']:
        for event in width['warmups']+width['batches']:
            binding=f" width={width['tokens']} mode={event['mode']} ordinal={event['ordinal']}"
            lines.extend(['PLE_fixture_graph_before'+binding+' GPU_backing_pinned=1',
                'PLE_fixture_graph_and_readback_returned'+binding+f" elapsed_ns={event['graph_completion_and_readback_ns']} GPU_completion_checked=1"])
    return '\n'.join(lines+['PLE_slice_validation_completed_waiting_for_ordinary_close model_loaded=0'])

class Controls(unittest.TestCase):
    def test_complete_is_not_model_or_production_adoption(self):
        r=good();review=validate(r,7,stages(r));self.assertEqual(review['GPU_graphs'],208)
        self.assertFalse(review['model_quality_or_speed_qualified']);self.assertFalse(review['production_adopted'])
        self.assertEqual(review['width_summaries'][0]['candidates']['1']['median_paired_ratio'],1.2)
    def test_completion_and_precision(self):
        for key in('F64_reference_passed','all_F32_outputs_bit_exact','input_and_output_canaries_intact',
            'positive_device_idle_and_epoch_retirement','all_shader_input_leases_returned','original_BF16_to_F32_casts_preserved'):
            r=good();r[key]=False
            with self.assertRaises(ValueError):validate(r,7,stages(r))
    def test_identity_and_finite_counters(self):
        for key,value in [('pid',True),('pid',8),('GPU_graphs',207),('device_ledger_live_bytes',1),('source_preflight_read_calls',3),
            ('source_worker_read_ns',1),('maximum_absolute_error',float('nan')),('device_ledger_peak_bytes',2<<30),('model_loaded',True)]:
            r=good();r[key]=value
            with self.assertRaises(ValueError):validate(r,7,stages(r))
    def test_placement_and_dtype(self):
        for key,value in [('CONT_nodes',[8,4,4,1]),('all_operations_on_single_Vulkan_backend',False),('tokens',True),('graph_construction_ns',[0,-1,0,0])]:
            r=good();r['widths'][0][key]=value
            with self.assertRaises(ValueError):validate(r,7,stages(r))
    def test_incomplete_cohort(self):
        for name in('widths','warmups','batches'):
            r=good();target=r[name]if name=='widths'else r['widths'][0][name];target.pop()
            with self.assertRaises(ValueError):validate(r,7,'')
    def test_order_and_strict_time_types(self):
        for key,value in [('candidate',2),('mode',True),('round',1),('ordinal',4),('graph_completion_and_readback_ns',0),('graph_completion_and_readback_ns',100.0)]:
            r=good();r['widths'][0]['batches'][0][key]=value
            with self.assertRaises(ValueError):validate(r,7,stages(r))
    def test_durable_binding(self):
        r=good();text=stages(r)
        for changed in(text.replace('elapsed_ns=120','elapsed_ns=121',1),text.replace('GPU_completion_checked=1','GPU_completion_checked=0',1),
            '\n'.join(text.splitlines()[1:]),'\n'.join(text.splitlines()[:-1]),text+'\n'+text.splitlines()[1]):
            with self.assertRaises(ValueError):validate(r,7,changed)
    def test_slow_round_remains_visible(self):
        r=good()
        for e in r['widths'][0]['batches']:
            if e['candidate']==1 and e['round']==0 and e['mode']==1:e['graph_completion_and_readback_ns']=200
        review=validate(r,7,stages(r));row=review['width_summaries'][0]['candidates']['1']
        self.assertEqual(row['faster_rounds'],7);self.assertFalse(row['all_rounds_faster'])
if __name__=='__main__':unittest.main()
