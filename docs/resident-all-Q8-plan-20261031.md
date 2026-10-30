# Remaining resident BF16 to Q8

The owner authorizes Q8 conversion of the remaining resident BF16 weights while
retaining routed Expert Q2. The installed control is SELF57043cbe, model receipt
7ba7bbf9. Use the same872cc126 cumulative-idle driver, archiveb57fe26e, disabled
persistent caches, F32 inputs/KV, four demand-read lanes and1381 cache slots.

The owner's subsequent clarification explicitly retains the small PLE
convolution in BF16 and converts the other resident BF16 weights to Q8.
The exact ModelFootprint placement selects544 tensors /6,749,552,640 BF16 bytes.
Q8_0 payload is3,585,699,840 bytes, saving3,163,852,800 bytes before allocation
alignment. Mapped input embeddings, the lazy PLE lookup table, MTP and all F32
tensors are outside the conversion. Existing routed Q2 and output/shared Q8
payloads must remain bit-identical. Keep cache capacity fixed for this comparison.

1. Convert bounded original BF16 payloads using the pinned reference Q8_0
   quantizer. Verify each parent payload hash and serialize contiguous GGUF
   headers. Keep parts at most512 MiB and native metadata at most1 MiB.
2. Validate the exact selection and unchanged tensors independently. Preserve
   the single80 KiB PLE convolution's BF16 payload and[4,10240] shape exactly.
   Keep the original model engine, graph and convolution compute path unchanged.
3. Bind complete immutable publication identities and source ranges, integrate
   strict receipt/type/footprint admission and compile a separately linked app.
4. Run bounded native numerical and fixed-task comparisons after fresh ownership
   and memory observations. Quantized logits need not equal BF16 logits; require
   finite outputs, deterministic same-profile repeats and correct fixed tasks.
   Report cross-precision logit differences, raw output differences, TTFT, decode,
   memory and I/O separately. Preserve ordinary close and exact control restore.
5. Place the qualified Q8 program/settings with current/immediate-control full
   readback. Update production records only after actual qualification. If a
   native result fails, fix the demonstrated issue rather than weakening checks.

No CI, agents, reboot, force-kill, GPU reset or removal of original model assets.
Host conversion/build success does not establish PS5 qualification or adoption.
