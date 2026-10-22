# Required Qwen operations and remaining coverage

The pinned original Qwen4Exp graph has 48 trunk layers, 512 experts with top-10
routing, four hyper-connection streams, 128-wide recurrent key/value heads,
128-wide QSA indexer heads, and the required PLE module at layer 2. These are
source/configuration facts. They do not establish operation support or quality
on the physical console.

The completed 32x16 BF16 matvec admission covers one small arithmetic path.
The separate [original-weight 2560x16 matvec and F32 RMS/SiLU diagnostic](native-original-operations-20261022.md)
subsequently passed all 5,136 outputs on the physical PS5. Neither stage covers
all operations of the complete model.

| Operation family | Inspected pinned source contract | Remaining physical coverage |
| --- | --- | --- |
| Expert routing and projections | Shared graph helpers use indexed expert projections, selection and nonlinear mixing; every original expert remains present | Routing, indexed BF16 matmul, top-10 ordering, cache/staging correctness and final quality |
| Hyper-connections | `ggml_dsv4_hc_pre_gated` maps to `GGML_OP_DSV4_HC_PRE`; Vulkan PRE/POST require F32 inputs/output and exactly four streams | Small numerical/lifetime admission, then full-model shapes |
| Recurrent attention | Vulkan gated delta net accepts value width 16/32/64/128 and six F32 sources; this model uses width 128 | State update/readback, sequence boundaries and complete-model behavior |
| SSM convolution | Vulkan support checks F32 input | Shape-specific convolution and state history |
| QSA indexer | The inspected Vulkan path requires FP16 feature availability, supported key storage, head width 128, valid element strides and storage offsets | Actual device support, alignment and numerical admission |
| Prefix sums | Vulkan CUMSUM requires subgroup arithmetic and full-subgroup support | Device feature/shape admission; a source case is insufficient |
| PLE | Original 64-bit hash constants, 128 source parts and BF16 row storage are retained; row gather feeds normalization, projections, gating and convolution history | Bounded lazy row access, original precision and all downstream operations |
| Standard attention and output | Shared graph helpers add RoPE, attention, reduction and output projection paths | Actual selected pipelines, context/batch shapes and model-quality admission |

`tools/inventory_qwen_operations.py` records source/configuration hashes, direct
GGML API names, referenced graph helpers and selected backend case names. It
removes comments before collecting names, so a comment about an unused API is
not counted as a call. This is explicitly a lexical inventory. It does not
resolve conditional helper closure, allocate a graph, query a device, evaluate
weights or prove transitive operation coverage. Runtime shape/type/stride
checks and native numerical evidence remain required.

No capability flag, precision, expert count or quality threshold is changed by
this inspection. Full inference remains rejected until its separate gates pass.
All learned computation must run on the PS5; source inspection and offline
format/reference verification on the host do not substitute for that result.
