# IQ2 output-scale refinements

Host64934 tests two additional implementations on the18 previously authenticated
BF16 Expert matrices: nine Up and nine paired640-column Down matrices at
layers0/23/47. Both start from the unchanged prefill-only IQ2 encodings64772.
The64 code bytes in each66-byte block remain exact. Only its existing FP16
scale changes; storage size, shader arithmetic and format remain unchanged.
This does not requantize current Q2 weights as a new original reference.

The first candidate performs one residual least-squares coordinate sweep over
block scales. The second performs two sweeps, with a0.5 ridge term toward the
original scales and a12.5% cap on their changes. Shared scales of paired-row
blocks are fitted jointly against both actual output rows. Each candidate is
fully encoded before heldout target values are used. The original training
prefill operands and evaluation2–23 decode operands remain separate.

| Candidate | Role | Improved over original IQ2 | Improved over current Q2 |
| --- | --- | ---: | ---: |
| One unconstrained sweep | Up |0/9|0/9|
| One unconstrained sweep | Down |0/9|1/9|
| Two bounded ridge sweeps | Up |9/9|0/9|
| Two bounded ridge sweeps | Down |6/9|2/9|

Unconstrained fitting substantially overfits these prefill operands. Bounded
regularization improves the IQ2 baseline, but does not establish a general
quality advantage over the currently selected Q2 formats. The previous IQ2
baseline also improves heldout error for0/9 Up and2/9 Down matrices.
These are component output errors from one prompt, not model answer quality.
The same previously observed heldout cohort is exploratory evidence, not a new
independent prompt set.

All36 NEW encodings pass complete byte-for-byte C/Python F32 decoding checks.
Their independently recomputed fit outputs match the residual updates; all
heldout outputs remain finite, with original references unchanged. None of
the old quantization or GPU scopes is replayed. No PS5 call, model inference,
decode tok/s improvement or production adoption is claimed by this experiment.
The36 unselected trial binaries/15,206,400 bytes are retired after complete
numeric results, exact hashes and reproducible source are saved. Original
BF16, fit/test operands and the pinned decoder are preserved.
